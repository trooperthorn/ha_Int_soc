# Container Resource Watchdog

Supervisor exposes no API to cap an add-on's CPU or memory (verified
against `aiohasupervisor`'s full `AddonsClient` surface), so "make sure no
container runs away" is built from what Supervisor does support, plus an
explicit opt-in escape hatch for hard caps.

## Soft path: sampling and Supervisor-native actions

The watchdog samples per-container stats, and on a **sustained** breach of
its threshold takes a per-container action:

- `alert` — raise a finding, take no action on the container.
- `restart` — restart the add-on via the real Supervisor API.
- `stop` — stop the add-on via the real Supervisor API.

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
