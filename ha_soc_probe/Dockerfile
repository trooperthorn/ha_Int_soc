# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
# `3.23` is a MOVING tag: its contents change as the base image is
# rebuilt, so a build today and a build next month can differ. The image
# is therefore pinned by its immutable digest (work item 2.5): the digest
# below is the multi-arch OCI index for tag 3.23, resolved on 2026-08-30
# from ghcr.io's registry API (anonymous token flow, Docker-Content-Digest
# of the tag's manifest index, which covers linux/amd64 and linux/arm64,
# the two architectures config.yaml declares). The tag stays in the
# reference so a human can still see which release the digest froze; the
# digest is what the build actually resolves. To bump: re-resolve with
# `docker buildx imagetools inspect ghcr.io/home-assistant/base:<tag>`
# and replace both the tag and the digest together, never the tag alone.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23@sha256:1c7a8c7321c15cdc327c264232a76e6fbfdaf7f2b1734a8d8da6fcc994f66015
FROM ${BUILD_FROM}

# iptables: the firewall read/write feature (config.yaml's `privileged:
# [NET_ADMIN]`) needs the real iptables/iptables-save/iptables-restore
# binaries, not busybox's stub. iproute2: `ip -4 -o addr show`, already
# relied on by the existing port scanner to resolve a bind address to its
# owning interface — pinning it explicitly rather than continuing to rely
# on it merely happening to be present in the base image.
# Upgrade packages inherited from the immutable base digest before adding the
# Probe runtime. The base is intentionally reproducible, but Alpine security
# fixes continue after that digest is published; without this step, rebuilding
# can retain already-fixed vulnerable libraries from the older base layer.
# Only the agent package is installed. Client utilities such as snmpset are
# intentionally absent from the runtime image; validation is run from the
# external monitoring host.
RUN apk upgrade --no-cache \
    && apk add --no-cache iptables iproute2 net-snmp

# A daemon-specific account prevents the unprivileged port scanner (nobody)
# from reading Net-SNMP's mode-0600 localized USM key database.
RUN addgroup -S ha_soc_snmp \
    && adduser -S -D -H -s /sbin/nologin -G ha_soc_snmp ha_soc_snmp

COPY rootfs /

RUN chmod a+x \
    /etc/services.d/ha_soc_probe/run \
    /etc/services.d/ha_soc_probe/finish \
    /etc/services.d/ha_soc_probe_firewall/run \
    /etc/services.d/ha_soc_probe_firewall/finish \
    /etc/services.d/ha_soc_probe_snmp/run \
    /etc/services.d/ha_soc_probe_snmp/finish

LABEL \
    org.opencontainers.image.title="HA SOC Probe" \
    org.opencontainers.image.description="Host-level open-port visibility companion for the HA SOC integration." \
    org.opencontainers.image.source="https://github.com/trooperthorn/ha_int_soc" \
    org.opencontainers.image.licenses="Apache-2.0"
