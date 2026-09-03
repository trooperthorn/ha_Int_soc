#!/usr/bin/env bash
# Pure validation/serialization helpers for privileged Docker resource limits, sourced by the firewall service.

validate_resource_limits() {
    jq -ce '
        if (
            type == "object"
            and length <= 128
            and all(
                to_entries[];
                (.key | test("^[a-z0-9][a-z0-9_-]{0,63}$"))
                and (.value | type == "object")
                and ((.value | keys_unsorted) - ["memory_mb", "cpus"] | length == 0)
                and (
                    .value.memory_mb == null
                    or (
                        (.value.memory_mb | type) == "number"
                        and .value.memory_mb == (.value.memory_mb | floor)
                        and .value.memory_mb >= 64
                        and .value.memory_mb <= 1048576
                    )
                )
                and (
                    .value.cpus == null
                    or (
                        (.value.cpus | type) == "number"
                        and .value.cpus >= 0.1
                        and .value.cpus <= 64
                    )
                )
                and (.value.memory_mb != null or .value.cpus != null)
            )
        ) then . else error("invalid HA SOC resource limits") end
    '
}

validate_applied_resource_slugs() {
    jq -ce '
        if (
            type == "array"
            and length <= 128
            and all(.[]; type == "string" and test("^[a-z0-9][a-z0-9_-]{0,63}$"))
        ) then unique else error("invalid HA SOC applied-resource slug list") end
    '
}

docker_body_for_resource_limit() {
    jq -ce '
        {
            Memory: (if .memory_mb == null then null else (.memory_mb * 1048576 | floor) end),
            MemorySwap: (if .memory_mb == null then null else (.memory_mb * 1048576 | floor) end),
            NanoCpus: (if .cpus == null then null else (.cpus * 1000000000 | floor) end)
        }
        | with_entries(select(.value != null))
    '
}
