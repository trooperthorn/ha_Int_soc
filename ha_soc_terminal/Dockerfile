# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
# Same base and digest as ha_soc_probe; bump tag and digest together (docker buildx imagetools inspect).
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.24@sha256:93ef607824e3f27e868f11b10938283a98bf880ed57bcf8eaa81c6c2d521f6f5
FROM ${BUILD_FROM}
ARG BUILD_ARCH=amd64

# The Supervisor CLI, pinned by release and checksum per architecture. It
# is installed as ha.real; /usr/local/bin/ha is the wrapper that hands it
# the Supervisor token without exporting it into the shell.
ARG HA_CLI_VERSION=5.5.0
ARG HA_CLI_SHA256_AMD64=fb2e2177bd7bc014f029b807cd1cc7d74484ecfed1e90d5f9b2a61d65ff5393d
ARG HA_CLI_SHA256_AARCH64=af390ab7f91a8135668ace7b1425d8e53800b6a1fc3b36fc588df701d2ab3db5

# The terminal server, the shell, the transcript recorder, and the readers.
# Nothing that opens a connection to another host is installed; CI asserts
# the absent binaries (docs/TERMINAL-DESIGN.md, "Client tools").
RUN apk upgrade --no-cache \
    && apk add --no-cache \
        bash \
        bash-completion \
        coreutils \
        less \
        lscpu \
        nano \
        nano-syntax \
        ncurses \
        openssh-server \
        pciutils \
        ttyd \
        util-linux-misc \
    && rm -f /usr/bin/tempio \
    # BusyBox applet names that open connections; the applets stay inside the
    # busybox binary (docs/TERMINAL-DESIGN.md, "Client tools").
    && rm -f /usr/bin/nc /usr/bin/wget /usr/bin/telnet /usr/bin/ftpget /usr/bin/ftpput /usr/bin/tftp

RUN set -eu; \
    case "${BUILD_ARCH}" in \
        amd64) sum="${HA_CLI_SHA256_AMD64}" ;; \
        aarch64) sum="${HA_CLI_SHA256_AARCH64}" ;; \
        *) echo "no ha CLI for ${BUILD_ARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /usr/bin/ha.real \
        "https://github.com/home-assistant/cli/releases/download/${HA_CLI_VERSION}/ha_${BUILD_ARCH}"; \
    echo "${sum}  /usr/bin/ha.real" | sha256sum -c -; \
    chmod 0755 /usr/bin/ha.real

COPY rootfs /

RUN chmod a+x \
    /etc/services.d/ha_soc_terminal/run \
    /etc/services.d/ha_soc_terminal/finish \
    /etc/services.d/ha_soc_terminal_sftp/run \
    /etc/services.d/ha_soc_terminal_sftp/finish \
    /usr/local/bin/ha_soc_term_open \
    /usr/local/bin/ha \
    && chmod 0600 /etc/ssh/sshd_config

LABEL \
    org.opencontainers.image.title="HA SOC Terminal" \
    org.opencontainers.image.description="Recorded, local-only bash terminal for the HA SOC integration." \
    org.opencontainers.image.source="https://github.com/trooperthorn/ha_int_soc" \
    org.opencontainers.image.licenses="Apache-2.0"
