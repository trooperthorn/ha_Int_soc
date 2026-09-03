#!/usr/bin/env bash
# Read-only verification of the Probe add-on's platform facts on a real Supervisor install; nothing here changes state.
# Run from the SSH add-on: bash ha_soc_verify_supervisor.sh | tee ha_soc_verify_$(date +%Y%m%d).txt; see docs/operations.md.
set -uo pipefail

PROBE_NAME="HA SOC Probe"
CONFIG_DIR=""
for candidate in /homeassistant /config; do
    if [ -d "$candidate/.storage" ]; then CONFIG_DIR="$candidate"; break; fi
done

have() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n==== %s ====\n' "$1"; }
fact() { printf 'FACT %s\n' "$*"; }
note() { printf 'NOTE %s\n' "$*"; }

if ! have ha; then
    echo "The 'ha' CLI is not available here. Run this from the SSH add-on terminal." >&2
    exit 1
fi
JQ=""
if have jq; then JQ="jq"; else note "jq not found; raw JSON is printed instead of extracted fields."; fi

section "Platform versions"
# The ha CLI wraps every payload in {"result", "data"}; unwrap .data first or every field prints null.
ha info --raw-json 2>/dev/null | { [ -n "$JQ" ] && jq '(.data // .) | {supervisor, homeassistant, hassos, operating_system, machine, arch, supported, healthy}' || cat; }
ha supervisor info --raw-json 2>/dev/null | { [ -n "$JQ" ] && jq '(.data // .) | {version, version_latest, supported, healthy, addons_repositories}' || cat; }
ha os info --raw-json 2>/dev/null | { [ -n "$JQ" ] && jq '(.data // .) | {version, version_latest, board, boot, data_disk, update_available}' || cat; }
if [ -n "$JQ" ]; then
    SUP_VER=$(ha supervisor info --raw-json 2>/dev/null | jq -r '.data.version // .version // empty')
    fact "supervisor_version=${SUP_VER:-unknown}  (GHSA-gh5m-4m97-c95h is fixed in 2026.03.2 and later)"
fi

section "Boot slots (the RAUC / 18.2 question)"
ha os info --raw-json 2>/dev/null | { [ -n "$JQ" ] && jq '(.data // .) | {boot, version, version_latest, update_available}' || cat; }
ha host info --raw-json 2>/dev/null | { [ -n "$JQ" ] && jq '(.data // .) | {operating_system, kernel, boot_timestamp, startup_time, disk_total, disk_used, disk_free}' || cat; }

section "Locate the Probe add-on by its name"
SLUG=""
if [ -n "$JQ" ]; then
    SLUG=$(ha addons --raw-json 2>/dev/null | jq -r --arg n "$PROBE_NAME" '.data.addons[]? | select(.name==$n) | .slug' | head -1)
fi
if [ -z "$SLUG" ]; then
    note "Could not find an installed add-on named '$PROBE_NAME'. Installed add-ons:"
    ha addons 2>/dev/null
    note "If the add-on is installed under a different name, set PROBE_NAME at the top of this script."
else
    fact "probe_slug=$SLUG   (container name addon_$SLUG)"
fi

if [ -n "$SLUG" ]; then
    section "Supervisor's view of the Probe (privileges, rating, protection)"
    INFO=$(ha addons info "$SLUG" --raw-json 2>/dev/null)
    if [ -n "$JQ" ]; then
        echo "$INFO" | jq '.data | {name, version, state, rating, protected, host_network, host_pid, host_uts, host_dbus, privileged, docker_api, full_access, apparmor, auth_api, homeassistant_api, hassio_api, hassio_role, ingress, network, signed, repository, auto_update, watchdog, boot, ip_address}'
        for k in rating protected host_network docker_api apparmor signed; do
            fact "addon.$k=$(echo "$INFO" | jq -r ".data.$k")"
        done
        fact "addon.privileged=$(echo "$INFO" | jq -c '.data.privileged')"
        fact "addon.network=$(echo "$INFO" | jq -c '.data.network')"
        note "Keys present in the Supervisor payload (these are what Core's get_addons_info() caches):"
        echo "$INFO" | jq -r '.data | keys | join(", ")'
    else
        echo "$INFO"
    fi

    section "Probe add-on log (last 120 lines)"
    ha addons logs "$SLUG" 2>/dev/null | tail -n 120
fi

section "HA SOC services registered in Core (through the Supervisor proxy)"
if [ -n "${SUPERVISOR_TOKEN:-}" ] && have curl; then
    curl -s -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" http://supervisor/core/api/services \
      | { [ -n "$JQ" ] && jq '.[] | select(.domain=="ha_soc") | .services | keys' || cat; }
else
    note "SUPERVISOR_TOKEN or curl not available in this shell; skipping service listing."
fi

section "File modes under .storage (DATA-1)"
if [ -n "$CONFIG_DIR" ]; then
    for f in "$CONFIG_DIR/.storage/ha_soc.storage" "$CONFIG_DIR/.storage/core.config_entries" "$CONFIG_DIR/.storage/auth" "$CONFIG_DIR/secrets.yaml"; do
        [ -e "$f" ] && stat -c 'FACT mode=%a owner=%U:%G %n' "$f"
    done
    if [ -d "$CONFIG_DIR/.storage/ha_soc_audit" ]; then
        stat -c 'FACT mode=%a owner=%U:%G %n' "$CONFIG_DIR/.storage/ha_soc_audit"
        ls -la "$CONFIG_DIR/.storage/ha_soc_audit" | tail -n 8
    else
        note "no ha_soc_audit directory yet"
    fi
    if [ -e "$CONFIG_DIR/.storage/backup" ] && [ -n "$JQ" ]; then
        # Reports only whether a default backup password and per-agent protection are set, never any value.
        fact "backup_default_password_set=$(jq -r '(.data.config.create_backup.password != null)' "$CONFIG_DIR/.storage/backup" 2>/dev/null || echo unknown)"
        fact "backup_agents_protected=$(jq -c '[.data.config.agents // {} | to_entries[] | {(.key): .value.protected}]' "$CONFIG_DIR/.storage/backup" 2>/dev/null || echo unknown)"
    fi
else
    note "Config directory not found at /homeassistant or /config; skipping file-mode checks."
fi

section "Container level (needs docker; requires Protection Mode off on THIS SSH add-on)"
if ! have docker; then
    note "docker CLI not available; container-level facts skipped. Disable Protection Mode on the SSH add-on temporarily to collect them, then re-enable it."
elif [ -z "$SLUG" ]; then
    note "Probe slug unknown; container-level facts skipped."
else
    # Discover the container by name first; an auto-update can recreate addon_<slug> mid-run.
    C=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -m1 "ha_soc_probe" || true)
    if [ -z "$C" ]; then C="addon_$SLUG"; fi
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$C"; then
        note "Container $C is not running right now (an auto-update may have it mid-recreate)."
        note "Running containers matching nothing suppressed; retry in a minute. Full list:"
        docker ps --format '  {{.Names}}' 2>/dev/null
    fi
    docker inspect "$C" --format 'FACT container.NetworkMode={{.HostConfig.NetworkMode}}
FACT container.CapAdd={{json .HostConfig.CapAdd}}
FACT container.Privileged={{.HostConfig.Privileged}}
FACT container.AppArmorProfile={{.AppArmorProfile}}
FACT container.Image={{.Config.Image}}
FACT container.Mounts={{json .Mounts}}' 2>/dev/null || note "docker inspect $C failed"

    docker exec "$C" sh -c '
        echo "FACT uid_gid=$(id)"
        echo "FACT caps_eff=$(grep CapEff /proc/1/status | cut -f2)"
        echo "FACT var_run_target=$(readlink -f /var/run 2>/dev/null || echo none)"
        for s in /run/docker.sock /var/run/docker.sock; do
            if [ -S "$s" ]; then echo "FACT docker_socket_present=$s"; else echo "FACT docker_socket_absent=$s"; fi
        done
        echo "FACT iptables_version=$(iptables -V 2>&1)"
        echo "FACT ip6tables_version=$(ip6tables -V 2>&1)"
        for b in iptables-legacy iptables-nft ip6tables-legacy ip6tables-nft nft; do
            if command -v $b >/dev/null 2>&1; then echo "FACT binary_present=$b"; else echo "FACT binary_absent=$b"; fi
        done
        echo "FACT legacy_ip_tables_names=$(cat /proc/net/ip_tables_names 2>/dev/null | tr "\n" " ")"
        echo "FACT legacy_ip6_tables_names=$(cat /proc/net/ip6_tables_names 2>/dev/null | tr "\n" " ")"
        echo "---- iptables -S HA_SOC_RULES"; iptables -S HA_SOC_RULES 2>&1
        echo "---- ip6tables -S HA_SOC_RULES"; ip6tables -S HA_SOC_RULES 2>&1
        echo "---- iptables -S INPUT (first 8 rules)"; iptables -S INPUT 2>&1 | head -n 8
        echo "---- ip6tables -S INPUT (first 8 rules)"; ip6tables -S INPUT 2>&1 | head -n 8
        if command -v iptables-legacy >/dev/null 2>&1 && command -v iptables-nft >/dev/null 2>&1; then
            echo "---- backend comparison (which one Docker on this host actually uses)"
            echo "legacy INPUT rules: $(iptables-legacy -S INPUT 2>/dev/null | wc -l)   nft INPUT rules: $(iptables-nft -S INPUT 2>/dev/null | wc -l)"
        fi
        echo "---- /data"; ls -la /data 2>&1
        echo "FACT secret_file_mode=$(stat -c %a /data/ha_soc_probe_secret 2>/dev/null || echo missing)"
    ' 2>&1

    section "Host-side view (Core container is not the host; this is the Probe with host_network)"
    docker exec "$C" sh -c 'ip -4 -o addr show 2>/dev/null; ip -6 -o addr show scope global 2>/dev/null' 2>&1 | sed "s/^/HOSTNET /"
fi

section "Done"
note "Review every FACT line. The work plan's section 6.2 lists what each one settles."
