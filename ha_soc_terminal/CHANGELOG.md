# Changelog

## Unreleased

- Added the Supervisor `ha` CLI (5.5.0, checksum-pinned per architecture),
  `lscpu` and `lspci`. The app declares `hassio_api` with the `manager`
  role for the CLI; Protection Mode stays on.
- The Supervisor token is now unset before the terminal server starts. It
  was inherited by every shell from the s6 environment in earlier releases
  despite the documentation saying otherwise; the `ha` wrapper re-imports it
  for the CLI process alone.
- Ingress removed. The terminal opens only from the HA SOC panel, behind
  HA SOC's access tier, with every session's open and close audited. The
  app generates a credential once, requires it on every connection, and
  hands it to HA SOC through `ha_soc.pair_terminal` (declared
  `homeassistant_api` for that one call). ttyd's built-in page is no
  longer served to a browser; the panel's own terminal carries the theme.
- Fixed ttyd failing to start with `Scandir on '/usr/lib' failed, errno 13`:
  the AppArmor profile granted file contents but not directory listings,
  which libwebsockets needs to find its event-loop plugin and which bash
  completion needs everywhere. Directories are now readable throughout.
- Fixed the service restarting with `ln: failed to create symbolic link
  '/config': Permission denied`: the AppArmor profile keeps the filesystem
  root read-only by design, so the convenience link is now `~/config` and
  the shell starts in `/homeassistant`.
- Dropped `bat`: it links libgit2 and therefore libssh2, an SSH client
  library with open high-severity findings, in an image whose point is to
  carry no SSH. Dropped `yq` as well: its Go build carries two open
  high-severity module findings the scan refuses. `view` (nano in
  read-only mode) covers coloured reading.
- Fixed the AppArmor profile stopping the container at startup with
  `/bin/sh: can't open '/init': Permission denied`: the s6 boot chain
  paths were granted execute without read.
- First release of the HA SOC Terminal app: one bash login shell per
  connection through ttyd with no tmux, every session recorded by
  util-linux `script` with its hash in `/data/sessions/index.jsonl`,
  `nano` with syntax files (and a `view` alias for read-only colourised
  viewing) for reading and editing YAML,
  a coloured prompt showing the last exit status, timestamped persistent
  history, and a bash idle timeout. No SSH client or other network tool,
  no host network, no Docker socket, no extra capability, and the
  Supervisor token is not exported into the shell. Ingress is on for this
  release only; the HA SOC panel gate replaces it next.
