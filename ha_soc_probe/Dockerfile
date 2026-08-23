# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

# iptables: the firewall read/write feature (config.yaml's `privileged:
# [NET_ADMIN]`) needs the real iptables/iptables-save/iptables-restore
# binaries, not busybox's stub. iproute2: `ip -4 -o addr show`, already
# relied on by the existing port scanner to resolve a bind address to its
# owning interface — pinning it explicitly rather than continuing to rely
# on it merely happening to be present in the base image.
RUN apk add --no-cache iptables iproute2

COPY rootfs /

RUN chmod a+x \
    /etc/services.d/ha_soc_probe/run \
    /etc/services.d/ha_soc_probe/finish \
    /etc/services.d/ha_soc_probe_firewall/run \
    /etc/services.d/ha_soc_probe_firewall/finish

LABEL \
    org.opencontainers.image.title="HA SOC Probe" \
    org.opencontainers.image.description="Host-level open-port visibility companion for the HA SOC integration." \
    org.opencontainers.image.source="https://github.com/trooperthorn/ha_int_soc" \
    org.opencontainers.image.licenses="Apache-2.0"
