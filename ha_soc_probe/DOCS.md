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

## How Home Assistant authenticates this add-on's calls

Every call this add-on makes into Home Assistant goes through the
Supervisor's Core API proxy, which forwards with the Supervisor's own
token. HA SOC accepts the two callback services only when a call carries
the Supervisor system user's context; any other caller is rejected
before the payload is read, audit-logged, and raised as a HIGH
detection. The per-install shared secret this add-on generates in its
own `/data` is defense in depth behind that check, not the primary gate:
a call without it is always rejected, and it can only be pinned by a
call that already passed the Supervisor check. On installs without a
Supervisor the services do not exist at all.

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
isn't enough. This add-on's `config.yaml` declares
`privileged: [NET_ADMIN]` for it.

**This add-on's Supervisor security rating is 1, and that is deliberate.**
The Supervisor's rating algorithm (`rating_security`, verified against
Supervisor commit `c5a5477`) sets the rating to 1 unconditionally for any
add-on declaring `docker_api`, which this add-on does for the optional
resource hard caps. No arrangement of the other grants changes that
number while the feature exists. The project's recorded decision (work
plan D-2) is one companion add-on carrying every host-level capability
the SOC needs, each grant documented, rather than several partially
privileged add-ons chasing a higher score. What this add-on still avoids:
`host_pid`, `host_uts`, `full_access`, and any elevated `hassio_role`.

### Privilege ledger

Every grant in `config.yaml`, why it exists, and how its use is limited.
Each row is checkable against the shipped scripts.

| Grant | Needed by | What the add-on does with it | Without it | How its use is limited |
| --- | --- | --- | --- | --- |
| `host_network` | Port report | Shares the host's network namespace so `/proc/net/*` shows the host's real listeners and bind addresses | The report would show the container's own (empty) namespace | Read-only use of `/proc/net`; the add-on opens no listening socket of its own |
| `privileged: [NET_ADMIN]` | Firewall read/test/confirm | Runs `iptables` against the host's real netfilter tables | The firewall card cannot read or write anything; the port report still works | Writes stay in the dedicated `HA_SOC_RULES` chain plus exactly one jump rule at the top of `INPUT` into that chain; full ruleset backup before every apply; local self-contained revert timer |
| `docker_api` | Resource hard caps | Applies per-container `--cpus`/`--memory` limits through the Docker socket | Hard caps report `denied`/unavailable; the watchdog's Supervisor-API restart and stop actions still work | With Protection Mode on (the default) the Supervisor does not mount the socket at all; slugs are validated against the installed add-on list; only container update calls are issued |
| `homeassistant_api` | Everything | Delivers port reports and firewall/cap poll results into Core through the Supervisor proxy | The add-on cannot report anything | Calls only the two `ha_soc` services, carrying the pairing secret; Core additionally requires the call to arrive with the Supervisor's own user context |
| Protection Mode off (your toggle) | Hard caps only | Grants the Docker socket mount | Everything except hard caps works with protection on | The panel states the root-equivalent consequence before any cap is applied, and every application is audited |

**How the safety mechanism works.** Every rule this add-on ever applies
lives in one dedicated chain, `HA_SOC_RULES`, which it owns outright,
plus exactly one jump rule it maintains at position 1 of `INPUT` into
that chain (first, because a deny that lands below an accept is not a
deny). Nothing Docker manages and no pre-existing rule is ever touched.
A proposed ruleset is never permanent on arrival:

1. This add-on takes two backups and checks both succeeded: a
   full-table `iptables-save` kept for manual recovery, and a chain-only
   snapshot (`iptables -S HA_SOC_RULES`) that reverts actually replay.
   If either backup fails, nothing is applied and the test reports as
   reverted. Reverts flush and replay only the `HA_SOC_RULES` chain,
   never the whole table, so a revert can never disturb rules this
   add-on does not own.
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
   progress." An interrupted test is always treated as failed. A
   deliberate stop behaves the same way: the service's `finish` script
   runs the identical recovery before exiting, so stopping the add-on
   mid-test reverts immediately instead of waiting for the next start.
5. Every add-on slug HA SOC sends for a resource cap is re-validated
   locally against a strict character pattern before it can appear in a
   Docker API path, so a compromised Core cannot turn this add-on into
   an arbitrary Docker client.

**Uninstalling.** Cleanup is best-effort: no Supervisor-run uninstall
hook is verified to exist, so an empty `HA_SOC_RULES` chain and its one
`INPUT` jump can remain after removal. Manual cleanup from the host is
`iptables -D INPUT -j HA_SOC_RULES` followed by
`iptables -X HA_SOC_RULES`.

## Resource hard caps (optional, off by default)

The HA SOC panel can configure real Docker limits (memory / CPUs) per
add-on — the per-container cap Supervisor itself has no API for. This
add-on receives those caps on the same poll channel as firewall work and
applies them against the Docker socket (`config.yaml`'s `docker_api`).

Two things to know before using it:

- **It only works with this add-on's Protection Mode DISABLED.** With
  protection on (the default), the Supervisor does not mount the Docker
  socket into this container at all, so every
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

## Verified on a real Supervisor

On 2026-08-30 the owner ran the read-only verification script
(`scripts/ha_soc_verify_supervisor.sh` in the repository, work plan
decision D-21) on the production Home Assistant OS install. Facts
recorded from that run, each checkable against the pasted output:

- Supervisor 2026.08.0. GHSA-gh5m-4m97-c95h (fixed in 2026.03.2) is
  patched on this install.
- The add-on installs, starts, and works: version 2026.08.30.2, state
  started, 91 listening TCP ports found and reported successfully. The
  hold-and-retry path was exercised live: during a Core restart the
  report was refused with HTTP 502 and the add-on backed off 30s, 60s,
  120s, then succeeded on the next cycle.
- The Supervisor rates the add-on 1, exactly as the privilege ledger
  states, with `protected: true`, `host_network: true`,
  `docker_api: true`, `privileged: [NET_ADMIN]`, `apparmor: default`
  (no custom profile yet; that is planned work), `signed: false`,
  `hassio_role: default`.
- The cached add-on info payload carries every key the planned add-on
  privilege inventory needs (`host_pid`, `host_uts`, `full_access`,
  `hassio_role`, `ingress`, `rating`, `protected`, `signed`, and the
  rest), confirming the aiohasupervisor model against the live shape.
- Both callback services are registered and reachable through the
  Supervisor proxy.
- The install slug is Supervisor-assigned from the repository
  (`9ddefa12_ha_soc_probe` there; yours will differ), which is why the
  integration matches this add-on by its `name`, never by slug.

Still unverified, because the container-level half of that run hit the
add-on mid-recreate (auto-update) and found no container to inspect:
the iptables backend in use versus the host's, `ip6tables` and kernel
`ip6_tables` support, the effective AppArmor profile and capability
set, the Docker socket path and `/var/run` symlink question, the secret
file mode, and the absence of listening sockets. The script now
discovers the container instead of assuming its name; a re-run of just
that section settles these.

## A note on how this was built

This add-on's scripts were written and reviewed against Home Assistant's
official add-on documentation and real, current official add-ons (see the
integration repo's design notes for exactly what was checked and where),
and since 2026-08-30 it has run in production on the owner's Home
Assistant OS install (see "Verified on a real Supervisor" above). If
something here doesn't work as described, please open an issue.
