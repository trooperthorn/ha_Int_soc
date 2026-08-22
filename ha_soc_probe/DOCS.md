# HA SOC Probe

An **optional** companion add-on for the [HA SOC](https://github.com/trooperthorn/ha_int_soc)
integration. It exists to close exactly one gap: real, socket-level
visibility into what's actually listening on the Home Assistant **host**,
which a Python integration cannot see from inside its own container even
on Home Assistant OS. Everything else HA SOC's design docs once considered
bundling into an add-on (SSH-add-on exposure, HA's own config-check
status) turned out to be reachable from inside the integration itself —
see that repo's README for the full reasoning. This add-on does the one
thing that genuinely needs a separate, host-network-attached container,
and nothing else.

## What it does

Every `scan_interval_hours` (default 6), this add-on reads the host's
`/proc/net/tcp` and `/proc/net/tcp6` connection tables — visible here only
because `host_network: true` puts this container on the host's own
network namespace — and reports every port in `LISTEN` state to the HA
SOC integration via its `ha_soc.ingest_probe_result` service, over
Supervisor's Core API proxy (`SUPERVISOR_TOKEN` + `homeassistant_api`
permission — no separate credentials or setup on your end).

If a report is rejected — most commonly a brief window of HTTP 400 right
after Home Assistant Core itself restarts, while the HA SOC integration
is still loading — this add-on does not wait out the full
`scan_interval_hours` before trying again. It holds in a short, capped
retry loop (30s, backing off to a 5-minute cap) instead, logging a clear
"Holding — ..." warning on every attempt, so a half-connected setup shows
up in this add-on's own log rather than silently going quiet for hours.
If it stays in that state for more than 30 minutes, the HA SOC
integration itself also raises a Repairs issue (Settings > Repairs) —
visible even to someone who never opens the add-on's log at all.

## What it deliberately does NOT do

- **No process-name attribution.** Knowing *which port* is open is useful
  on its own; knowing *which process* opened it would need this add-on to
  also see the host's process list (`host_pid: true`), a second elevated
  privilege on top of `host_network`. That's a real security cost for a
  nice-to-have, so this add-on doesn't ask for it. The HA SOC panel shows
  port + protocol only.
- **No active scanning.** This reads the kernel's own connection table —
  the same data `netstat`/`ss` show — rather than connecting outward to
  probe ports, so it never generates outbound traffic or triggers an IDS
  on your own network.
- **No UDP.** `/proc/net/udp[6]` has no meaningful "listening" state the
  way TCP does (UDP sockets are connectionless), so this add-on doesn't
  attempt to characterize UDP as open/closed the way it does for TCP.

## Configuration

```yaml
scan_interval_hours: 6
```

`scan_interval_hours` (1–24, default 6): how often to re-scan and report.

## Requirements

- Home Assistant OS or Supervised. This add-on cannot run on Core or
  Container installs — host-level network visibility isn't something
  Supervisor can grant outside of Home Assistant OS/Supervised.
- The HA SOC integration installed and loaded, since this add-on's only
  job is calling into it.

## A note on how this was built

This add-on's scripts were written and reviewed against Home Assistant's
official add-on documentation and real, current official add-ons (see the
integration repo's design notes for exactly what was checked and where),
but — unlike the HA SOC integration itself, which is validated against a
real `pytest-homeassistant-custom-component` test harness — this add-on
has not yet been built and run against a real Home Assistant Supervisor.
If something here doesn't work as described, please open an issue.
