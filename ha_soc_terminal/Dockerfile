# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
# Same base and digest as ha_soc_probe; bump tag and digest together (docker buildx imagetools inspect).
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.24@sha256:93ef607824e3f27e868f11b10938283a98bf880ed57bcf8eaa81c6c2d521f6f5
FROM ${BUILD_FROM}

# The terminal server, the shell, the transcript recorder, and the readers.
# Nothing that opens a connection to another host is installed; CI asserts
# the absent binaries (docs/TERMINAL-DESIGN.md, "Client tools").
RUN apk upgrade --no-cache \
    && apk add --no-cache \
        bash \
        bash-completion \
        coreutils \
        less \
        nano \
        nano-syntax \
        ncurses \
        ttyd \
        util-linux-misc \
    && rm -f /usr/bin/tempio \
    # BusyBox applet names that open connections; the applets stay inside the
    # busybox binary (docs/TERMINAL-DESIGN.md, "Client tools").
    && rm -f /usr/bin/nc /usr/bin/wget /usr/bin/telnet /usr/bin/ftpget /usr/bin/ftpput /usr/bin/tftp

COPY rootfs /

RUN chmod a+x \
    /etc/services.d/ha_soc_terminal/run \
    /etc/services.d/ha_soc_terminal/finish \
    /usr/local/bin/ha_soc_term_open

LABEL \
    org.opencontainers.image.title="HA SOC Terminal" \
    org.opencontainers.image.description="Recorded, local-only bash terminal for the HA SOC integration." \
    org.opencontainers.image.source="https://github.com/trooperthorn/ha_int_soc" \
    org.opencontainers.image.licenses="Apache-2.0"
