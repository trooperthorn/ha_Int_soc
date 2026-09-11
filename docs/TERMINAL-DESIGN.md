# HA SOC Terminal: design

Status: phase 1 shipped as the `ha_soc_terminal` app (2026-09-10); phases 2
and 3 are design only. This document owns the terminal surface: what it is,
where it executes, who may open it, what it records, and what it can never do.
The dated decisions behind it are in `decisions.md` under "Terminal".

## Why a terminal at all, and why not app-ssh

Every HA SOC surface is a structured read or a confirmed, audited write. A
terminal is neither: it is a free shell, and the 2026-09-09 decision rejected
exactly that for Device SSH. The reason to build one anyway is that the owner
already runs one, the community "Advanced SSH & Web Terminal" app, and it has
four properties HA SOC cannot accept on a host it is supposed to be watching.
Each was read from that app's source at its current head (see
`decisions.md`, 2026-09-10):

1. Any Home Assistant administrator gets a root shell through ingress, and
   every web session attaches to the same tmux session (`tmux new -A -s
   homeassistant`), so the second admin lands inside the first admin's live
   screen.
2. Nothing records a session. sshd logs logins to journald; ttyd and tmux
   record nothing; shell history is per user and editable.
3. The Supervisor token is exported into every shell and written to
   `/data/.ssh/environment`, and a non-root login profile runs `exec sudo -i`,
   so every session is root with a manager-role token in its environment.
4. The container carries a pivot toolkit (`openssh` client, `mosh`, `nmap`,
   `ncat`, `tcpdump`, `wget`, `rsync`, `python3`) under `apparmor: false`,
   `SYS_ADMIN`, `SYS_RAWIO`, `/dev/mem`, `host_dbus`, `docker_api`,
   `host_network` and every directory mapped read-write.

The complaints that started this (no scrollback, paste that inserts
characters, no history) are all the tmux wrapper: the browser's scrollback is
a tmux pane, and paste goes through tmux's mouse mode.

## Goals and non-goals

Goals: an interactive bash terminal in the HA SOC panel that executes only on
the local Home Assistant server, is opened only by the owner (or admins, by
setting), records every session tamper-evidently, follows the panel's theme,
and reads YAML and shell comfortably. Later, SFTP to the config directory
under the same gate.

Non-goals: SSH to any other host from inside the terminal; a host (HAOS)
root shell; a shell inside the Core container's Python process; session
sharing; a package installer or init-command hook.

## Architecture

```
browser panel (xterm.js, HA theme)            phase 2
   |  ha_soc/terminal/{open,input,resize,close}
   v
HA SOC integration (terminal.py)              phase 2
   tier gate, target allowlist, session limits, audit + transcript hash
   |  WebSocket proxy over the Supervisor internal network
   v
ha_soc_terminal app                           phase 1
   ttyd  ->  ha_soc_term_open (session wrapper)
              -> script (transcript + timing under /data/sessions)
                 -> bash -l   [self]              phase 1
                 -> docker exec homeassistant     [core]   phase 2, docker_api
                 -> docker exec addon_<slug>      [addon]  phase 2, docker_api
```

Phase 1 exposes the app through ingress so the shell, theme, paste and
scrollback can be exercised before the integration side exists. Ingress is
removed in phase 2; from then on the only door is the integration's proxy.

## The app (phase 1, shipped)

Forked in spirit from app-ssh, not in code: the s6 layout, the base image
and the run-script conventions are the Probe's. What was taken from app-ssh
is its sshd hardening (for phase 3) and the history-persistence idea.

| Item | Choice | Reason |
| --- | --- | --- |
| Shell | bash, login shell | One binary, no plugin ecosystem, `PROMPT_COMMAND` gives a per-command history line with `HISTTIMEFORMAT` stamps. zsh's editing was judged not worth oh-my-zsh and its plugins. |
| Terminal server | `ttyd` without tmux | One PTY per connection, so browser scrollback and bracketed paste work and no session is shared. |
| Recording | util-linux `script` with `--log-out` and `--log-timing`, per session, under `/data/sessions` | Full transcript with timing (replayable, keeps color), written by the wrapper before the shell starts, hashed at exit into `/data/sessions/index.jsonl`. |
| Readability | `nano` with its syntax files (plus a `view` alias for `nano -v`), `dircolors`, colored `PS1` with the last exit status | Covers reading commands, reading YAML, editing YAML. No `ble.sh`. `bat` and `yq` were in the first build and dropped on 2026-09-10: `bat` links libgit2 and so libssh2, an SSH client library with open high-severity CVEs; `yq`'s Go build carried two open high-severity module findings. The image scan refuses both, and a reader is not worth a CVE. |
| Idle timeout | bash `TMOUT` from the `idle_timeout_minutes` option | Built in, nothing to add. |
| Client tools | None: no `openssh`, `mosh`, `nmap`, `ncat`, `tcpdump`, `rsync`, `git`, `python3`, `sudo`, `tmux`; the BusyBox `nc`, `wget`, `telnet`, `tftp` and ftp applet names are removed | "Cannot proxy to another host" holds for what the image ships. `curl` stays because bashio needs it, and `busybox nc` remains reachable by that spelling since the applets live inside the one binary. CI asserts the absent command names on every build. |
| Privileges | No `host_network`, no `docker_api`, no `privileged`, custom AppArmor, `homeassistant_config:rw` only | Rating 6 with ingress and the profile; the app can reach `/homeassistant` and its own `/data` and nothing else. |
| Token | Not exported. `SUPERVISOR_TOKEN` is read by bashio in the run script and never written to a profile or file. | app-ssh's item 3. |
| Ingress | On, `panel_admin: true`, phase 1 only | Testing surface; the tier gate does not exist until phase 2. |
| Boot | `boot: manual` | A terminal should not come up with the host. |

Options: `session_recording` (default on), `history_persist` (default on),
`idle_timeout_minutes` (default 30, 0 disables). There is no `packages` and
no `init_commands`.

The wrapper `ha_soc_term_open` is the only command ttyd runs. It generates a
session id, writes the transcript and timing files with mode 0600, starts
`bash -l`, and on exit appends `{id, started, ended, bytes, sha256}` to the
index. `script -f` flushes as it writes, so a session that is killed still
leaves what happened so far; the index line is the fact HA SOC will later
ingest.

Residuals accepted for phase 1 and written down: ingress is any-admin until
phase 2; the transcript captures anything typed at a prompt, including a
password typed into a program that asked for one, and the redaction rules
that mask key names cannot mask a bare value; bash `TMOUT` is a courtesy, not
a control, since a running program does not honour it.

## The integration side (phase 2, design)

WebSocket commands, all `@require_owner` by default, admins when the
existing access setting opens the panel to them:

| Command | Payload | Answer |
| --- | --- | --- |
| `ha_soc/terminal/status` | none | `{installed, running, targets: [{id, label, available}], recording, sessions_open, max_sessions}` |
| `ha_soc/terminal/open` | `{target, cols, rows}` | `{session_id, recorded: true}` then a subscription stream of `{data}` frames |
| `ha_soc/terminal/input` | `{session_id, data}` | ack |
| `ha_soc/terminal/resize` | `{session_id, cols, rows}` | ack |
| `ha_soc/terminal/close` | `{session_id}` | `{closed: true}` |

`target` is one of `self` (the app's own bash), `core` (`docker exec -it
homeassistant /bin/bash`, the shell HAOS itself documents), or `addon:<slug>`
validated against the Supervisor's installed list the way the Logs tab
validates slugs. `core` and `addon:*` need `docker_api` on the app and
Protection Mode off, spelled out in the panel exactly as the Probe's caps
are. The host is not a target; the documented HAOS path for that is debug SSH
on port 22222 with a key on a USB `CONFIG` partition.

The integration reaches ttyd over the Supervisor internal network at the
app's hostname (`{repo}-ha-soc-terminal`, from `GET /addons/<slug>/info`
`hostname`) on port 7681, with ttyd bound to that interface only and ingress
off. The per-connection target rides as a ttyd URL argument to the wrapper,
which validates it again; the browser never talks to ttyd.

Every open writes an audit record (`terminal_session_open`, flushed) with
target, user, session id; every close writes `terminal_session_close` with
duration, byte counts, and the transcript sha256 the wrapper reported through
the external audit ingest contract (`ha_soc.ingest_audit`, per-source secret
pinned on first call). A session that ends without a close record is a
finding, not silence.

Limits: one session per user, three per install, a hard maximum duration,
and the idle timeout. Recording cannot be switched off from the panel; the
app option is the only place, and the panel shows the state in the header.

The panel bundles xterm.js (Lit component, `@xterm/xterm` and the fit,
web-links and clipboard addons), builds the terminal theme from the HA theme's
CSS variables (background, foreground, the sixteen ANSI colors mapped from the
theme's accent and state colors, with a Settings override), enables bracketed
paste, and keeps a bounded scrollback. Phase 1 approximates the theme with
ttyd's `-t theme=` client option so the palette can be judged before the
component exists.

## SFTP (phase 3, design)

sshd from app-ssh's hardened `sshd_config` (modern ciphers, no forwarding, key
auth only, root login off) with only the `internal-sftp` subsystem and a
`ChrootDirectory` of `/homeassistant`, on a port the owner opens explicitly,
off by default. No shell over SSH: the terminal is the panel's. Keys come from
the same secret store path as Device SSH, and every login is audited from
sshd's journald lines through the Logs tab's Supervisor gateway.

## Verification list

- [x] Phase 1 image builds (verified locally 2026-09-10: util-linux 2.42.3
      `script`, ttyd 1.7.7); `ttyd`, `bash`, `nano`, `script` present; `ssh`, `nmap`, `ncat`, `nc`, `wget`,
      `tcpdump`, `mosh`, `tmux`, `python3`, `sudo` absent (CI, `security.yml`).
- [ ] Ingress terminal on the live install: scrollback in the browser, paste
      of a multi-line YAML block arrives unchanged, `view` colours YAML
      correctly, theme readable in light and dark.
- [ ] A session leaves `/data/sessions/<id>.out`, `.timing`, and an index
      line whose sha256 matches the file.
- [x] AppArmor profile loads. The Supervisor does apply `apparmor.txt` to a
      locally built app: the first profile stopped the container at
      `/bin/sh: can't open '/init': Permission denied` because it granted
      `ix` without `r` on the s6 boot chain, fixed 2026-09-10. The second
      profile denied `ln -s /homeassistant /config` at the root, which is
      correct: the root stays read-only and the link moved to `~/config`.
      The third
      denied libwebsockets' scan of `/usr/lib` for its event-loop plugin:
      file rules do not grant directory listings, so `/**/ r` was added.
      Still open: a normal session with no denials in
      `journalctl _TRANSPORT="audit"`.
- [ ] Phase 2: the app's Supervisor `hostname` is reachable from Core on
      7681; ttyd `-a` URL arguments reach the wrapper (unverified against ttyd
      1.7.7).
