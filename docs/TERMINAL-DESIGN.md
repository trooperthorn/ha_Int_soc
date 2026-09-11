# HA SOC Terminal: design

Status: phase 1 shipped as the `ha_soc_terminal` app (2026-09-10); phase 2,
the panel gate and proxy, shipped and verified live 2026-09-11 with the
`self` target only;
phase 3 and the `core` and `addon` targets are design only. This document owns the terminal surface: what it is,
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

Phase 1 exposed the app through ingress so the shell, paste and scrollback
could be exercised before the integration side existed. Phase 2 removed
ingress; the only door is the integration's proxy, and the app declares
`homeassistant_api` for the one pairing call it makes.

## The app (phase 1, shipped)

Forked in spirit from app-ssh, not in code: the s6 layout, the base image
and the run-script conventions are the Probe's. What was taken from app-ssh
is its sshd hardening (for phase 3) and the history-persistence idea.

| Item | Choice | Reason |
| --- | --- | --- |
| Shell | bash, login shell | One binary, no plugin ecosystem, `PROMPT_COMMAND` gives a per-command history line with `HISTTIMEFORMAT` stamps. zsh's editing was judged not worth oh-my-zsh and its plugins. |
| Terminal server | `ttyd` without tmux | One PTY per connection, so browser scrollback and bracketed paste work and no session is shared. |
| Recording | util-linux `script` with `--log-out` and `--log-timing`, per session, under `/data/sessions` | Full transcript with timing (replayable, keeps color), written by the wrapper before the shell starts, hashed at exit into `/data/sessions/index.jsonl`. |
| Readability and inspection | `nano` with its syntax files (plus a `view` alias for `nano -v`), `dircolors`, colored `PS1` with the last exit status; `lscpu`, `lspci` and the Supervisor `ha` CLI (5.5.0, pinned by checksum per architecture) since 2026-09-11 | Covers reading commands, reading YAML, editing YAML. No `ble.sh`. `bat` and `yq` were in the first build and dropped on 2026-09-10: `bat` links libgit2 and so libssh2, an SSH client library with open high-severity CVEs; `yq`'s Go build carried two open high-severity module findings. The image scan refuses both, and a reader is not worth a CVE. |
| Idle timeout | bash `TMOUT` from the `idle_timeout_minutes` option | Built in, nothing to add. |
| Client tools | None: no `openssh`, `mosh`, `nmap`, `ncat`, `tcpdump`, `rsync`, `git`, `python3`, `sudo`, `tmux`; the BusyBox `nc`, `wget`, `telnet`, `tftp` and ftp applet names are removed | "Cannot proxy to another host" holds for what the image ships. `curl` stays because bashio needs it, and `busybox nc` remains reachable by that spelling since the applets live inside the one binary. CI asserts the absent command names on every build. |
| Privileges | No `host_network`, no `docker_api`, no `privileged`, custom AppArmor, `homeassistant_config:rw` only; `hassio_api` with `hassio_role: manager` since 2026-09-11 for the `ha` CLI | Rating 5 (base 5, custom profile +1, manager -1, no ingress). Manager is the role the Supervisor documents for apps that run CLIs and needs no Protection Mode change; it lets a session start, stop, install and update apps and Core, which is what a terminal owner expects and the tier gate is the control on. The app can reach `/homeassistant`, its own `/data`, and the Supervisor API, and nothing else. |
| Token | Not in the shell. The start script uses `SUPERVISOR_TOKEN` for the pairing call and then unsets it before starting ttyd, so no session, transcript or history file carries it. The `ha` wrapper re-imports the container environment for the CLI process alone (`with-contenv`). Correction 2026-09-11: phase 1 and 2 claimed the token was "not exported" but never unset it, so every shell inherited it from the s6 environment; found while adding the CLI. | app-ssh's item 3, done properly. |
| Ingress | Off since phase 2 | The panel is the only door. ttyd requires HTTP basic auth with a per-install credential the app generates once (`/data/ha_soc_terminal_secret`, mode 0600) and hands Core through `ha_soc.pair_terminal`; verified in a container that ttyd answers 401 to an anonymous HTTP or WebSocket request with the credential set. |
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

Residuals written down: the transcript captures anything typed at a prompt, including a
password typed into a program that asked for one, and the redaction rules
that mask key names cannot mask a bare value; bash `TMOUT` is a courtesy, not
a control, since a running program does not honour it.

## The integration side (phase 2, shipped)

`terminal.py` holds one aiohttp WebSocket to ttyd per session and relays
bytes both ways as base64; the browser never talks to the app. The commands
carry the panel's own tier (`require_soc_access`: owner only by default,
owner and admins when the access setting says so):

| Command | Payload | Answer |
| --- | --- | --- |
| `ha_soc/terminal/status` | none | `{supervisor, installed, running, paired, version, hostname, recording, targets: [{id, label, available}], sessions_open, max_sessions, max_session_seconds, sessions}` |
| `ha_soc/terminal/open` | `{target, cols, rows}` | result `{session_id, target, host, started, recorded, max_session_seconds}`, repeated as the first event `{kind: "opened", ...}`, then events `{kind: "output", data}` (base64), `{kind: "title", title}`, and finally `{kind: "closed", reason, duration_seconds}` |
| `ha_soc/terminal/input` | `{session_id, data}` (base64, at most 64 KiB decoded) | `{ok: true}` |
| `ha_soc/terminal/resize` | `{session_id, cols, rows}` | `{ok: true}` |
| `ha_soc/terminal/close` | `{session_id}` | `{closed: true}` |

Refusal codes: `not_supervisor`, `app_not_installed`, `app_not_running`,
`app_not_paired`, `session_limit_user`, `session_limit_total`,
`unknown_target`, `unknown_session`, `connect_failed`. Close reasons:
`user_closed`, `remote_closed`, `connection_lost` (the browser unsubscribed
or its WebSocket dropped), `max_duration`, `unloaded`, `error`.

`target` is `self` (the app's own bash) today. `core` (`docker exec -it
homeassistant /bin/bash`, the shell HAOS itself documents) and `addon:<slug>`
(validated against the Supervisor's installed list the way the Logs tab
validates slugs) remain design: both need `docker_api` on the app and
Protection Mode off, a privilege change the app has not made, to be spelled
out in the panel exactly as the Probe's caps are. The host is never a target;
the documented HAOS path for that is debug SSH on port 22222 with a key on a
USB `CONFIG` partition.

The integration finds the app in the Supervisor's cached add-on list by
slug suffix, reads `GET /addons/<slug>/info` for `hostname`, `state` and
`options`, and connects to `ws://<hostname>:7681/ws` with subprotocol `tty`
and basic auth `hasoc:<secret>`. The ttyd wire protocol is one command byte
then the payload in each direction: the first client message is JSON
`{AuthToken, columns, rows}` with `AuthToken` the base64 credential again (an empty token is closed with 1008), then `0`+bytes is input, `1`+JSON is resize,
and from ttyd `0`+bytes is output, `1`+text is a title, `2`+JSON preferences
are ignored. The per-connection target as a ttyd URL argument stays design
with the `core` and `addon` targets.

Every open writes an audit record (`terminal_session_open`, flushed) with
target, user, session id, host and size; every close writes
`terminal_session_close` with duration, bytes in and out, and the reason.
`terminal_pairing_rejected` records a pairing call that was not the
Supervisor's or carried a different secret than the pinned one. Not yet
wired: the transcript sha256 the wrapper writes to the app's index, which
would ride the external audit ingest contract; it stays in the app's
`/data/sessions/index.jsonl` (backlog).

Limits: one session per user, three per install, eight hours maximum, and
the app's idle timeout. Recording cannot be switched off from the panel; the
app option is the only place, and the panel header shows the state it read
from the app's options.

The panel bundles xterm.js (`@xterm/xterm` 6 and `@xterm/addon-fit`; the
stylesheet is copied into `src/generated/xterm-css.ts` by
`scripts/gen-xterm-css.mjs` at build time because the view renders in shadow
DOM), builds the terminal theme from the HA theme's CSS variables (code
editor background, primary text, primary and accent colors, the error,
success, warning and info state colors mapped onto the ANSI palette, with a
light-mode neutral set) and rebuilds it whenever `hass` changes, keeps a
5,000-line scrollback, and ends the session when the view is left. A
Settings override for the palette is not built.

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
- [x] ttyd 1.7.7 offers `-c/--credential`, `-a/--url-arg`, `-i/--interface`
      and `-b/--base-path` (read from `ttyd --help` in the image), and with a
      credential set answers 401 to anonymous HTTP and WebSocket requests
      (verified in a container).
- [x] Phase 2 on the live install, first pass 2026-09-11: the app paired,
      Core reached the app's hostname on 7681, and the panel received the
      `opened` event, so the gate, pairing and proxy work end to end. The
      session then closed at once: ttyd requires the credential a second
      time as `AuthToken` in the handshake and the proxy sent it empty.
      Fixed the same day.
- [x] Phase 2 on the live install, second pass (v2026.09.11.2, 2026-09-11):
      a session stays open, paste and scrollback behave in xterm.js, the
      theme follows light and dark, and closing the view leaves a
      `terminal_session_close` audit record. Phase 2 is closed.
- [ ] ttyd `-a` URL arguments reach the wrapper (needed only for the `core`
      and `addon` targets; unverified).
