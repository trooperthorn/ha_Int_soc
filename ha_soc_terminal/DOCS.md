# HA SOC Terminal

A recorded bash terminal for the [HA SOC](https://github.com/trooperthorn/ha_Int_soc)
integration. It exists because the community SSH and web terminal app gives
every Home Assistant administrator a root shell, shares one screen between
all of them, records nothing, and ships every tool needed to pivot from this
host to another. This app is the opposite on each point, and the reasoning,
the phases, and the accepted limits are in the repository's
`docs/TERMINAL-DESIGN.md`.

## What it is

- **bash**, one login shell per browser connection. No tmux, so the
  browser's own scrollback and paste work, and nobody lands in someone
  else's session.
- **Recorded.** Each session is written by util-linux `script` to
  `/data/sessions/<id>.out` with a timing file beside it, and its size and
  SHA-256 are appended to `/data/sessions/index.jsonl` when the session
  ends. The transcript keeps colour and can be replayed with
  `scriptreplay`. The header line of every session says whether it is
  being recorded.
- **Local only.** The image carries no SSH client, no `mosh`, `nmap`,
  `ncat`, `tcpdump`, `rsync`, `git`, `python`, or `sudo`. The only
  directory mapped in is the Home Assistant configuration directory, at
  `/homeassistant` (also reachable as `~/config`). There is no host network, no
  Docker socket, and no extra capability.
- **Readable.** `view` (nano read-only) reads YAML and shell in colour, `nano` edits
  with syntax highlighting and line numbers, `ls` and `grep` are coloured,
  and the prompt shows the last command's exit status in red when it was
  not zero.
- **No token in the shell.** The Supervisor token is used by the app's own
  start script and is not exported into your session.

## What it is not

- Not a host shell. Home Assistant OS documents its own root path: debug SSH
  on port 22222 with an `authorized_keys` file on a USB partition named
  `CONFIG`.
- Not an SSH server. There is no port to open. SFTP to the configuration
  directory is a planned, separately enabled feature.
- Not shared. Two people opening the terminal get two shells.

## Options

| Option | Default | Effect |
| --- | --- | --- |
| `session_recording` | `true` | Write the transcript, timing file, and index line for every session. |
| `history_persist` | `true` | Keep bash history in `/data/.bash_history` across restarts, with timestamps. |
| `idle_timeout_minutes` | `30` | Close a shell idle at its prompt for this long; `0` disables. A running program is not interrupted. |

## Access today, and what changes next

In this release the terminal opens from the sidebar through ingress, which
means any Home Assistant administrator can open it. That is the testing
surface for the shell, theme, paste and scrollback. The next release moves
the terminal into the HA SOC panel behind HA SOC's own access tier (owner
only by default), removes ingress, and writes every session open and close
into HA SOC's audit chain with the transcript hash. Until then, treat this
app like the one it replaces: start it when you need it and stop it after.

## Known limits

- A transcript captures whatever is typed at a prompt, including a password
  typed into a program that asks for one.
- The idle timeout is bash's `TMOUT`; a running program does not honour it.
- `curl` is present because the app's own start script needs it, and
  BusyBox's networking applets remain reachable as `busybox nc` even though
  their command names are removed. The design doc records both as the
  accepted residual of "local only".
