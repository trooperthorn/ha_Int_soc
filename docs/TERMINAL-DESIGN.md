# HA SOC Terminal: design

Status: phase 1 shipped as the `ha_soc_terminal` app (2026-09-10); phase 2,
the panel gate and proxy, shipped and verified live 2026-09-11 with the
`self` target only; phase 3, SFTP, shipped 2026-09-11; the `core` and
`addon` targets are design only. This document owns the terminal surface: what it is,
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
and reads YAML and shell comfortably, plus SFTP to the config directory for
file transfer, off until the owner opens it.

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
| Client tools | None: no `openssh`, `mosh`, `nmap`, `ncat`, `tcpdump`, `rsync`, `git`, `python3`, `sudo`, `tmux`; the BusyBox `nc`, `wget`, `telnet`, `tftp` and ftp applet names are removed; `bind-tools` (`dig`, `nslookup`, `host`, `nsupdate`, `delv`) is uninstalled | "Cannot proxy to another host" holds for what the image ships. `curl` stays because bashio needs it, and `busybox nc` remains reachable by that spelling since the applets live inside the one binary. CI asserts the absent command names on every build. |
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
| `ha_soc/terminal/app_control` (owner only) | `{action: "start"\|"restart"}` | `{ok: true}` or `{ok: false, reason}` |
| `ha_soc/terminal/forget_pairing` (owner only) | none | `{ok: true}` |
| `ha_soc/terminal/export_event` | `{kind, session_id?, lines, bytes, sha256}` | `{ok: true}` |

`ha_soc/terminal/close` lets the owner close any user's session (the panel's
session list, from `status.sessions`, shows every open session); anyone else
may only close their own, exactly as before. `app_control` and
`forget_pairing` answer the app: boot: manual (the app does not start with
the host) and a session-limit lockout with no server-side way out of them,
which the panel could previously only describe, not fix. `export_event`
audits a copy or download the panel already performed client-side: `kind` is
one of `copy_screen`, `copy_all`, `copy_last`, `download_screen`,
`download_all`, `download_transcript`, `download_run`, and `sha256` is
computed over the exact text in the browser (`crypto.subtle.digest`) so the
audit record identifies what left the panel, not just how much. The audit
category is `terminal_export`, flushed like open and close. A failed
`export_event` call does not block the copy or download itself, only the
audit trail of it, and the panel shows a warning when that happens.

Refusal codes: `not_supervisor`, `app_not_installed`, `app_not_running`,
`app_not_paired`, `session_limit_user`, `session_limit_total`,
`unknown_target`, `unknown_session`, `connect_failed`. Close reasons:
`user_closed`, `owner_closed` (the owner closed a session that was not
theirs), `remote_closed`, `connection_lost` (the browser unsubscribed or its
WebSocket dropped), `max_duration`, `unloaded`, `error`.

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

Fonts. xterm.js measures the character cell on an OffscreenCanvas, and the
canvas font parser rejects CSS custom properties, so a `var()` in
`fontFamily` is silently dropped and every cell is measured on the canvas
default of 10px sans-serif while the glyphs are drawn in the real font: rows
overlap and the text looks compressed. The view therefore resolves a
concrete family string before creating the terminal. The header offers a
family (Home Assistant's `--ha-font-family-code` token, which is plain
`monospace` unless a theme sets it, or Cascadia Mono, Consolas, JetBrains
Mono, Fira Code, Menlo, Roboto Mono, DejaVu Sans Mono, Courier New), a size
from 11 to 20px and a line height from 1.0 to 1.4, remembered per browser in
`localStorage` under `ha_soc.terminal.font`. Nothing is bundled; a family is
offered only when the viewing machine has it, detected by measuring the
family against the generic fallbacks, because `document.fonts.check()`
reports true for any system family. Bundling a woff2 (JetBrains Mono, OFL,
about 100 KB per weight) would make the look uniform across machines at the
cost of bundle size; not done.

## App control, session list, and copy-out (phase 4)

The owner's complaint driving this phase: the app is `boot: manual`
(deliberately: it does not come up with the host), and before this the
stopped-app panel state only said "start it under Settings, Apps" with no
button; a lockout from `MAX_SESSIONS_PER_USER = 1` after a browser reload
left "close it first" with nothing to close it with; and there was no way
to get terminal output back out of the browser except manual selection.

Shipped this phase, backend and audited:

- `terminal.async_app_control(hass, action)` calls the same Supervisor
  client `ws_probe_restart` already uses (`get_supervisor_client(...)
  .addons.{start,restart}_addon(slug)`) so there remains exactly one code
  path in this integration that starts or restarts an app. Owner-only,
  audited as `terminal_app_control` with the action and the result; never
  raises, every failure comes back as `{"ok": false, "reason": ...}`.
- `terminal.async_forget_pairing` (existed) is now reachable from the panel
  through `ha_soc/terminal/forget_pairing`, owner-only, audited as
  `terminal_forget_pairing`.
- `TerminalSessions.async_close` takes `allow_any`: the owner can close any
  user's session (the session list is theirs to see, `status.sessions`), a
  session's own user can still close only their own. The close reason
  records which happened (`owner_closed` vs `user_closed`).
- `ha_soc/terminal/export_event` audits every copy or download the panel
  performs client-side, with a client-computed sha256 so the record names
  the actual bytes.

Also shipped, closing out this phase (frontend and the one-shot listener):

- `terminal-view.ts` renders Start / Restart (whenever the app is
  installed) and Forget pairing (owner-only, with a confirm dialog) next to
  the status line, all three calling the WS commands above.
- The session list (`status.sessions`) renders under the terminal, with a
  per-session Close button; the owner sees every session, anyone else sees
  only their own (`hass.user.id` against each row's `user_id`).
- Copy screen / Copy all / Copy last output and Download screen / Download
  all read `term.buffer.active` directly (`translateToString(true)`,
  trailing whitespace trimmed per row); "last output" uses the OSC 133
  marks below rather than guessing at prompts. Every copy or download
  hashes what it sent with `crypto.subtle.digest` and calls
  `ha_soc/terminal/export_event`; a failed audit call still leaves the
  copy or download in place, with a warning appended to the feedback line
  instead of blocking it.
- OSC 133;A (a new prompt is about to be drawn) and OSC 133;C (output is
  about to start) are now emitted by the shell itself
  (`rootfs/etc/profile.d/ha_soc_terminal.sh`: `printf` in the prompt
  function for A, `PS0` for C) and read by `term.parser.registerOscHandler`
  in `terminal-view.ts`, which records the absolute buffer row at each mark
  so "last output" is the previous command's output exactly, independent of
  scrollback position.

### Transcript download and run mode

Both shipped in this phase, on a second listener rather than the ttyd
WebSocket (which is a PTY stream, not a file server, and cannot answer a
one-shot request without a human at the other end):

- A `busybox httpd` service (`ha_soc_terminal_httpd`, port 7682) starts
  alongside ttyd, waits for the same paired secret ttyd generates, and
  writes an `httpd.conf` restricting `/cgi-bin` to `hasoc:<secret>` basic
  auth (`/path:user:pass`, `networking/httpd.c`'s `parseconf()`). Two CGI
  scripts under `/www/cgi-bin`, both bash:
  - `run`: `POST {"command", "timeout_seconds"}` (parsed with `jq`), runs
    `timeout <t> bash -lc "$command" 2>&1`, caps output at 256 KiB, writes
    the transcript to `/data/sessions/<id>.out` and appends
    `{"id","kind":"run","started","ended","command","exit","bytes","sha256"}`
    to the same `/data/sessions/index.jsonl` the interactive shell wrapper
    (`ha_soc_term_open`) writes, and answers
    `{id, stdout, exit_code, duration_seconds, truncated}`.
  - `transcript`: `GET ?id=<id>`, `id` checked against `^[A-Za-z0-9_-]+$`
    before it ever reaches a path (no `/`, no `..`, so nothing can walk out
    of the sessions directory), capped at 4 MiB, returns the raw bytes with
    an `X-Sha256` header taken from the index line.
- `TerminalSessions.async_run` (`terminal.py`) POSTs to `/cgi-bin/run` with
  the paired credential, one run at a time per user (`ERR_TERMINAL_BUSY`
  refuses a second), overall wait `timeout_seconds + 10`, and audits
  `terminal_run` with the command, exit code, output bytes and sha256, and
  duration. `TerminalSessions.async_transcript` GETs `/cgi-bin/transcript`,
  recomputes the sha256 integration-side and compares it against
  `X-Sha256` (`ERR_TRANSCRIPT_HASH_MISMATCH` on a mismatch, before anything
  reaches the browser), and audits `terminal_export` / `download_transcript`
  with the session id, bytes and sha256.
- The panel's "Run a command" card (`terminal-view.ts`) offers the input,
  a 30/60/120s timeout select, the exit code and duration, Copy output /
  Download output (audited as `copy_run` / `download_run`), and the last
  ten commands as clickable chips (in memory, not persisted). Each
  session's "Download transcript" button calls `ha_soc/terminal/transcript`
  and saves it locally, with an optional client-side ANSI strip (the
  audited hash is always of the raw bytes the app sent, before stripping).

Why a second httpd listener with the same credential, rather than PTY
sentinel scraping over the existing ttyd connection or a new Supervisor
privilege: scraping a PTY for command boundaries is exactly the kind of
fragile screen-scraping this app's design rejects elsewhere (the OSC 133
approach for copy-out marks boundaries deliberately instead of guessing at
prompts); a new privilege (`docker_api`, a Core-side exec route) would widen
the app's reach for a feature that a same-container HTTP listener answers
without it. `docs/decisions.md` has the dated entry.

## SFTP (phase 3, shipped)

A second s6 service in the app runs OpenSSH's sshd for file transfer only.
Its `sshd_config` takes app-ssh's hardening (modern ciphers, MACs and key
exchange, no TCP, agent, stream-local or X11 forwarding, no tunnels, key
authentication only, `MaxAuthTries 4`, `LoginGraceTime 60`) and removes the
shell: `Subsystem sftp internal-sftp`, `ForceCommand internal-sftp -l INFO`,
`PermitTTY no`, and `ChrootDirectory /homeassistant`, so a login sees the
configuration directory as `/` and nothing else. Verified in a container on
2026-09-11: `get` and `put` work, `ssh ... id` answers "This service allows
sftp connections only", a `-L` forward is refused, and every accepted key is
logged with its fingerprint.

Two departures from the earlier design paragraph, each for a reason:

- The login is `root`, with `PermitRootLogin prohibit-password`, not a
  dedicated account. The configuration directory and everything in it are
  root-owned on Home Assistant OS, so a non-root SFTP user could read but
  never write; app-ssh reaches the same conclusion ("SFTP only works if the
  user is root"). What limits root here is the forced command and the
  chroot, not the account.
- The authorized public keys are an app option (`sftp_authorized_keys`),
  not a Home Assistant secret. A public key is not a secret, sshd is the
  app's process, and the integration has no channel into the app's files
  except options. The service writes them to `/data/sftp_authorized_keys`
  (0600) on every start, so a removed key stops working at the next
  restart.

Off by default twice over: `sftp_enabled` is false, and the container port
2222 is mapped to no host port until the owner sets one in the app's network
settings. With the option on and no key that parses as a public key, the
service idles and says why rather than starting an sshd nobody can log in
to. The Ed25519 host key is generated once into `/data` and its fingerprint
is logged at every start so the owner can pin it. sshd runs in the foreground
with its log on stderr, so logins, refusals and the fingerprint land in the
app log the HA SOC Logs tab reads; turning accepted-key lines into audit
records is in the backlog.

AppArmor grants sshd `setuid`, `setgid` (privilege separation to the `sshd`
account), `sys_chroot` and `fowner` (the chroot and its ownership check),
`kill`, `/var/empty/`, and execution under `/usr/lib/ssh`; no
`net_bind_service` (2222 is unprivileged) and no `dac_override`. The image
adds `openssh-server` only: `ssh`, `scp` and `sftp` clients stay absent and
CI asserts it, along with an `sshd -t` of the shipped config and a check that
it resolves to the SFTP-only settings.

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
- [x] SFTP in a container (2026-09-11): host key generated, `get` and `put`
      through the chroot, shell and port forward refused, accepted keys
      logged with fingerprints, `sshd -t` clean, config resolves to the six
      SFTP-only settings.
- [ ] SFTP on the live install: `/homeassistant` passes sshd's chroot
      ownership check (root-owned, not group or world writable; a failure
      logs "bad ownership or modes for chroot directory"), the mapped port
      answers, and a client can `get` and `put` under the configuration
      directory.
- [ ] `busybox httpd` on this image is compiled with the `httpd` applet
      (added to `terminal-image-security` in `security.yml`, unverified
      without a Docker build in this environment).
- [ ] The `run` and `transcript` CGI scripts against a live app: basic auth
      is enforced on `/cgi-bin`, a run's output and index line match, a
      transcript's `X-Sha256` matches what `async_transcript` recomputes,
      and a bad `id` (`../etc/passwd` and similar) is refused by the WS
      schema before it ever reaches the CGI script.
- [ ] OSC 133 marks on the live shell: `A` fires once per prompt, `C` once
      per command, and "Copy last output" in the panel bounds exactly the
      previous command's output after a multi-line command and after a
      command that scrolls the screen.
- [ ] The `ha` subcommand names `corelog`/`suplog`/`hostlog`/`applog` call
      (`ha core logs`, `ha supervisor logs`, `ha host logs`, `ha apps logs
      <slug>`) against a live Supervisor CLI; not exercised outside the
      image build.
