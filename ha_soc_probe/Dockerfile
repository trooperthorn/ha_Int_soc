# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
# 3.24 is a moving tag, so the digest is what the build resolves; bump tag and digest together (docker buildx imagetools inspect).
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.24@sha256:93ef607824e3f27e868f11b10938283a98bf880ed57bcf8eaa81c6c2d521f6f5
FROM ${BUILD_FROM}

# apk upgrade pulls Alpine fixes published after the base digest.
# Real iptables and iproute2 binaries, not busybox stubs; snmpset and tempio are deliberately absent.
RUN apk upgrade --no-cache \
    && apk add --no-cache iptables iproute2 net-snmp \
    && rm -f /usr/bin/tempio

# A dedicated account keeps the nobody scanner from reading Net-SNMP's mode-0600 USM key database.
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
