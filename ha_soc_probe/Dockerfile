# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
# `3.23` is a MOVING tag — its contents change as the base image is
# rebuilt, so a build today and a build next month can differ. For
# reproducible builds, also pin the image by its immutable digest:
#
#     ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23@sha256:<digest>
#
# Fill <digest> in from the REAL published image at build time (e.g.
# `docker buildx imagetools inspect ghcr.io/home-assistant/base:3.23`, or
# `docker pull ... && docker inspect --format='{{index .RepoDigests 0}}' ...`).
# Left un-pinned here on purpose: the digest must come from the actual
# published image, never a guessed/placeholder value.
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
