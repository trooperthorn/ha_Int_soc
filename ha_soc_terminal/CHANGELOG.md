# Changelog

## Unreleased

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
