# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

COPY rootfs /

RUN chmod a+x \
    /etc/services.d/ha_soc_probe/run \
    /etc/services.d/ha_soc_probe/finish

LABEL \
    org.opencontainers.image.title="HA SOC Probe" \
    org.opencontainers.image.description="Host-level open-port visibility companion for the HA SOC integration." \
    org.opencontainers.image.source="https://github.com/trooperthorn/ha_int_soc" \
    org.opencontainers.image.licenses="Apache-2.0"
