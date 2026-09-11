# Changelog

## Unreleased

- Fixed the AppArmor profile stopping the container at startup with
  `/bin/sh: can't open '/init': Permission denied`: the s6 boot chain
  paths were granted execute without read.
- First release of the HA SOC Terminal app: one bash login shell per
  connection through ttyd with no tmux, every session recorded by
  util-linux `script` with its hash in `/data/sessions/index.jsonl`,
  `bat`, `yq`, and `nano` with syntax files for reading and editing YAML,
  a coloured prompt showing the last exit status, timestamped persistent
  history, and a bash idle timeout. No SSH client or other network tool,
  no host network, no Docker socket, no extra capability, and the
  Supervisor token is not exported into the shell. Ingress is on for this
  release only; the HA SOC panel gate replaces it next.
