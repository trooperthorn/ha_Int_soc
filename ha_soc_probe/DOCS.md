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

A second background service polls the HA SOC integration every ~5
seconds for a proposed firewall change and, when one is pending, applies
it to a dedicated `HA_SOC_RULES` iptables chain (see "Firewall rules"
below). This is the one thing this add-on ever writes rather than just
reads — everything else it does is observation only.

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

## Firewall rules (read and write)

Starting with `2026.08.23.3` this add-on can also read and, if you choose
to propose a change from the HA SOC panel, write the host's firewall
rules. This is opt-in per change, not an always-on background behavior:
nothing here is modified unless you propose a ruleset from HA SOC's
Firewall Rules card, which requires acknowledging that a backup will be
taken first.

**Why this needed a new privilege.** Running `iptables` against the
host's real netfilter tables needs a real `CAP_NET_ADMIN`, which Docker
strips from every container by default — `host_network: true` alone
isn't enough. This add-on's `config.yaml` now declares
`privileged: [NET_ADMIN]`, which lowers the Supervisor security rating by
one point. See the HA SOC integration's own README for the full breakdown
of what that rating means and why every other elevated privilege this
project could ask for was deliberately avoided (no `host_pid`, no
`full_access`, no `docker_api`, no elevated `hassio_role`).

**How the safety mechanism works.** Every rule this add-on ever applies
lives in one dedicated chain, `HA_SOC_RULES`, which it owns outright —
never the host's raw `INPUT` chain, never anything Docker itself manages.
A proposed ruleset is never permanent on arrival:

1. HA SOC takes a full ruleset backup (`iptables-save`) and applies the
   proposed rules to `HA_SOC_RULES`.
2. A confirmation window opens (roughly 30–60 seconds, set by HA SOC).
   The instant the rules are applied, this add-on arms a **local** revert
   timer — a plain backgrounded `sleep` inside this same process, not a
   scheduled callback from Home Assistant. This is deliberate: if the new
   rules break the very network path HA Core would need to tell this
   add-on to revert, the revert still has to happen without that path
   working. Nothing about the revert depends on anything outside this
   container.
3. If you confirm within the window, the rules stay and the timer becomes
   a no-op. If you don't — or you cancel immediately — the pre-change
   backup is restored automatically.
4. If this add-on itself crashes or restarts while a test is still
   unconfirmed (the local timer from step 2 dies with the old process),
   the next startup finds the leftover unresolved test and restores its
   backup immediately, rather than assuming it's still safely "in
   progress." An interrupted test is always treated as failed.

## Resource hard caps (optional, off by default)

The HA SOC panel can configure real Docker limits (memory / CPUs) per
add-on — the per-container cap Supervisor itself has no API for. This
add-on receives those caps on the same poll channel as firewall work and
applies them against the Docker socket (`config.yaml`'s `docker_api`).

Two things to know before using it:

- **It only works with this add-on's Protection Mode DISABLED.** With
  protection on (the default), the Docker socket is read-only and every
  application honestly reports *denied* back to the panel. Disabling
  Protection Mode is a root-equivalent grant to this add-on — the panel
  says so before anything is applied, and users who don't use hard caps
  lose nothing by leaving protection on.
- **Caps are re-applied every ~60 s, by design.** Supervisor recreates
  add-on containers on update/restart, silently dropping any Docker-level
  limit — idempotent re-application is the only way a cap actually
  persists across the platform's own lifecycle. Removing a cap in the
  panel resets that container to unlimited on the next pass.

A capped add-on that exceeds its memory limit is OOM-killed by the kernel;
Supervisor's own add-on watchdog restarts it if enabled.

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
