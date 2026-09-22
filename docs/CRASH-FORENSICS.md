# Crash forensics

Implements section 3(b) of the 2026-09-22 crash-forensics report
(`~/workspace/ha-crash-2026-09-22/REPORT-crash-forensics.md` on the
authoring machine; not part of this repository). See `docs/decisions.md`
("Crash forensics") for why this is a heartbeat file rather than a
Supervisor-reported flag, and `docs/RESOURCE-WATCHDOG.md` for the sibling
persistence change this module depends on.

## What it records

- A heartbeat file, `<config>/ha_soc/heartbeat.json`, rewritten every
  `heartbeat_interval_seconds` (default 30, 10-300) with the current
  timestamp, a per-boot id, and when this boot's Core started.
- A clean-stop marker, `<config>/ha_soc/last_stop.json`, written once on
  `EVENT_HOMEASSISTANT_STOP`.
- On the next start, after `EVENT_HOMEASSISTANT_STARTED` (so the `hassio`
  component the Supervisor calls need is loaded): if the heartbeat file is
  newer than the clean-stop marker (or there is no marker at all), the
  previous run did not stop cleanly, and a forensics bundle is collected.
- The bundle lands in `<config>/ha_soc/crash-<heartbeat timestamp>/`:

  | File | Source |
  | --- | --- |
  | `host-journal-prev-boot.txt` | `GET /host/logs/boots/-1?lines=5000` |
  | `kernel.txt` / `supervisor.txt` / `core.txt` | `GET /host/logs/boots/-1/identifiers/<id>?lines=3000` |
  | `host-info.json` | `GET /host/info` |
  | `resolution-info.json` | `GET /resolution/info` |
  | `supervisor-info.json` | `GET /supervisor/info` |
  | `os-info.json` | `GET /os/info` |
  | `containers.json` | this integration's own container-resource snapshot (`containers.py`), or `"unavailable"` |
  | `fault-log.txt` | `home-assistant.log.fault` if non-empty, else a note that an empty file is expected unless Core itself crashed on a fatal signal |
  | `watchdog-history.json` | the resource watchdog's ring **as it stood before this boot started overwriting it** (`watchdog_history.prev.json`; see RESOURCE-WATCHDOG.md) |
  | `summary.json` | classification, gap, suspects, and which Supervisor calls failed |

  Every Supervisor call is best-effort with a 30-second timeout; a failure
  is recorded in `summary.json`'s `errors` map and never raises. The
  bundle is capped at 25 MiB total (files are truncated, `summary.json`
  never is) and at most 10 bundles are kept, oldest deleted first.

## Classification

`classify_journal_tail()` reads the previous boot's journal tail and
returns one of:

- `clean_reboot`: a shutdown sequence is present (`Stopping`, `Reached
  target Reboot`, `Power-Off`).
- `kernel_fault`: a panic/hardware-error line is present (`Kernel panic`,
  `BUG:`, `Hardware Error`, `mce:`).
- `silent_stop`: neither — the journal simply stops. This is the failure
  mode the 2026-09-22 report calls case 7: the host went down under
  Supervisor with no shutdown sequence and no panic recorded anywhere on
  the box.

## Suspect ranking

`summary.json`'s `suspects` list, ranked in the order produced (not a
severity score — each entry names its own kind and evidence):

1. The unclean-stop window itself (heartbeat timestamp, `/host/info`'s
   `boot_timestamp`, the gap between them).
2. The journal classification above.
3. Any container the snapshot shows OOM-killed or exited 137/139/134/132.
4. Any container whose watchdog history shows CPU or memory rising, or
   above 85%, across its last 15 samples before the heartbeat (peak value
   included).
5. The last five distinct loggers to log in `core.txt` before the
   silence, parsed from the standard `[homeassistant.components.x]` /
   `[custom_components.x...]` log line format.
6. Any `systemd-coredump`/`traps:` line naming a process other than
   `chromium`.
7. A noise count of `traps: chromium` and `Bluetooth: hci0` lines, both
   recorded elsewhere as non-causal (kiosk Chromium's own known bug; see
   `docs/backlog.md`) — reported so a real reviewer does not chase them.

A Repairs issue (`unclean_stop_<bundle timestamp>`, severity warning,
non-fixable) is raised with the bundle path, classification, gap, and the
top three suspects.

## What it cannot see

A kernel panic that corrupts or prevents the journal write leaves nothing
behind for this module, or for anything else running inside the boot that
just failed, to read afterward. The only capture that survives that case
is shipping the journal continuously to a box that is not the one that
might go down — see `docs/backlog.md`'s "Off-box journal shipping" item,
which this feature does not attempt and does not replace.

An empty `home-assistant.log.fault` is not evidence of anything by
itself: Core removes it on every clean return and it only gets content on
a fatal *signal* (SIGSEGV/SIGFPE/SIGABRT/SIGBUS/SIGILL) in the Core
process, never for a Python exception, an OOM kill, a host hang, or a
power cut.

## Surfaces

- WS `ha_soc/crash_forensics/status` (soc-access gated): heartbeat state
  plus the bundle list (id, classification, gap, top-3 suspects, size,
  path).
- WS `ha_soc/crash_forensics/bundle` (soc-access gated): one file's text
  from one bundle; both the bundle id and file name are validated against
  a fixed allow-list before any path is built.
- WS `ha_soc/crash_forensics/collect_now` (owner-only, audited): runs the
  same collector against the CURRENT boot (`boots/0`) as a dry run, for
  testing that the pipeline reaches the Supervisor correctly before a real
  event needs it.
- Config: `crash_forensics_enabled` (default on) and
  `heartbeat_interval_seconds` (default 30, 10-300) in the HA SOC settings
  store, following the same pattern as the resource watchdog's settings.

## Panel

The Integration Security tab (where the resource watchdog's status card
also lives) carries a Crash Forensics card, backed by the three WS
commands above:

- Heartbeat state: enabled/disabled, the configured interval, and the
  last recorded heartbeat timestamp.
- A bundle table: timestamp, classification badge (`silent_stop` /
  `kernel_fault` / `clean_reboot`), gap in seconds, the top three
  suspects (`kind: subject`), and total size. Expanding a row lists
  every file the bundle can hold (`crash_forensics.py`'s `BUNDLE_FILES`)
  with View (renders the text in a capped monospace `<pre>`), Copy and
  Download buttons. Each copy/download is fetched from
  `ha_soc/crash_forensics/bundle` and then audited through
  `ha_soc/terminal/export_event` with kind `copy_forensics` or
  `download_forensics`, the line count, byte count, and a client-computed
  sha256 of the exact text that left the panel — the same pattern the
  Terminal view uses for its own exports (`export-helpers.ts`).
- Empty state: "No unclean stops recorded since crash forensics was
  enabled."
- A "Collect now (dry run)" button, confirm-gated, visible but disabled
  for non-owners (server-side this is `require_owner`; the button just
  reflects that instead of round-tripping to find out). On success it
  shows the resulting bundle id and classification and reloads the
  bundle list.
- If the status call itself fails (no connection, or this install has no
  Supervisor to page bundle files from), the card shows an error message
  in place of the table rather than a blank card.

## Unverified

- The Core container's exact `SYSLOG_IDENTIFIER` on HAOS 18.1+ (assumed
  `homeassistant`; the collector confirms it against
  `GET /host/logs/identifiers` at collection time and records what it
  actually used in `summary.json`, falling back to the guess on any
  failure).
- The exact line-count cap behaviour of `GET /host/logs/boots/-1` (whether
  `lines` is honored server-side or the response is filtered client-side).
- Whether `hass.data[DATA_COMPONENT].send_command` (the same transport
  `logs.py` already uses for the Logs tab) is the only supported way to
  reach `/host/logs/...` as text, or whether a raw aiohttp session against
  the Supervisor is ever necessary; this module uses `send_command`
  throughout, matching `logs.py`.
- Whether `home-assistant.log.fault` reliably has its final content
  flushed before a SIGKILL/host-stop reaches the same generation this
  collector reads it in (a fast enough power cut could still leave the
  file only partially written).
