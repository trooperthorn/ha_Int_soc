# Container Resource Watchdog

Supervisor exposes no API to cap an add-on's CPU or memory (verified
against `aiohasupervisor`'s full `AddonsClient` surface), so "make sure no
container runs away" is built from what Supervisor does support, plus an
explicit opt-in escape hatch for hard caps.

## Soft path: sampling and Supervisor-native actions

The watchdog samples per-container stats, and on a **sustained** breach of
its threshold takes a per-container action:

- `alert`: raise a finding, take no action on the container.
- `restart`: restart the add-on via the real Supervisor API.
- `stop`: stop the add-on via the real Supervisor API.

`restart` and `stop` are only ever applied to add-ons, never to Core or to
the Supervisor itself.

## Hard path: real Docker limits via the Probe

Hard caps (real Docker `--memory` / `--cpus`) are delivered to the HA SOC
Probe add-on over the existing poll channel and applied directly against
the Docker socket. This requires the Probe's Protection Mode to be
**disabled**, a root-equivalent grant that the UI spells out explicitly
before anything is applied.

Docker limits don't survive a container recreate, so whenever Supervisor
recreates a container, the hard cap must be re-applied. The Probe add-on
re-applies its caps on a timer for exactly that reason; a cap silently
disappearing after a Supervisor-triggered recreate would be worse than
never applying one.

## Constants

`WATCHDOG_ACTION_ALERT`, `WATCHDOG_ACTION_RESTART`, and
`WATCHDOG_ACTION_STOP` (`custom_components/ha_soc/const.py`) enumerate the
soft-path actions above.

## History persistence

The 60-sample ring per container used to live only in
`ResourceWatchdog._history` (a `dict[slug, deque]`), which meant a Core
restart lost the last hour of usage history. It is now written to
`<config>/ha_soc/watchdog_history.json` and reloaded on startup before the
first new sample lands, so the ring survives a restart with its `maxlen`
intact.

The write happens at most every `HISTORY_SAVE_INTERVAL_SECONDS` (10
minutes), and only when the ring changed, plus once when the entry stops or
reloads (`async_flush_history`), and when Home Assistant itself stops (a listener on the stop event, because core does not unload entries on shutdown). Writing after every sample rewrote the whole
file about 60 times an hour for data that changes by one sample at a time. A
crash or power loss loses at most the last ten minutes of samples, and the
first write of a boot comes ten minutes after startup. The ring as the last
write left it is copied to the `.prev` file described below, which is what the
crash bundle reads, so after a crash it can be up to ten minutes old. A slug that is no longer in the overview of a
complete (not truncated) sample, because the add-on was uninstalled, is
removed from the ring and from the file.

## Shared container sample

The watchdog and the Observe push share one container sample
(`ResourceWatchdog.async_shared_overview`). It is taken at most every
`STATS_MIN_INTERVAL_SECONDS` (3 minutes), or at the watchdog interval when
the watchdog is on and that interval is shorter (`sample_gap()`). Callers that
arrive while a sample is in flight wait for it. A sample the push took just
before a watchdog tick is evaluated by the watchdog on that tick instead of
being fetched again, and is evaluated once. With the watchdog off nothing
evaluates thresholds; the push alone drives the sample at the three-minute
gap. `async_run_once` still always asks the Supervisor and is kept for the
tests; the panel's resource request calls the collector directly and does not use the shared sample.

The write goes through `atomic_json.sync_write_json_atomic` (temp file +
`os.replace`, mode 0600) rather than the HA SOC `Store` helper. `Store` is
right for configuration that changes occasionally and can tolerate a
debounced, versioned write; this ring changes as often as once a minute
forever and never needs a migration path, so a plain private JSON file
with no version envelope is the lighter and more honest fit. See
`atomic_json.py`'s module docstring and `docs/decisions.md` (2026-09-22).

`ResourceWatchdog.status()` reports `history_file` (the on-disk path) and
`history_last_write` (ISO timestamp of the last actual write, `None`
before the first one).

Before this boot's watchdog can overwrite `watchdog_history.json`,
`async_load_history()` copies whatever was already on disk to
`watchdog_history.prev.json`. `crash_forensics.py` reads that `.prev` file
when it collects a bundle, because a bundle about an unclean stop is
necessarily about the boot that just ended, and by the time the collector
runs, the live `watchdog_history.json` already belongs to the new boot.
