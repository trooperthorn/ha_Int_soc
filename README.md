# HA SOC

<img src="icon.png" width="72" height="72" align="left" alt="HA SOC shield icon">

A Home Assistant custom integration that centralizes user account security,
audit logging, dashboard permissions, device/integration vulnerability
tracking, and a SOC-style risk dashboard — built on the same architectural
pattern as [Alarmo](https://github.com/nielsfaber/alarmo) and
[Browser Mod](https://github.com/thomasloven/hass-browser_mod): a custom
sidebar panel driven by its own WebSocket API, with its own versioned
storage.

This repository accompanies a full design walkthrough of the goals,
architecture, and honesty tradeoffs behind every feature. The short version:
Home Assistant has exactly two authorization tiers (admin / non-admin); a lot
of what looks like finer-grained control (view visibility, per-user sidebar
hiding) is cosmetic. HA SOC is built to say so, everywhere, rather than
imply otherwise.

## What it does

- **Users & Access** — every user, their real last-login (from refresh-token
  activity, since Home Assistant fires no login event), MFA status, and
  session/token management including revocation.
- **Audit Log** — a tamper-evident (hash-chained), rotating record of
  service calls, user/dashboard changes, and best-effort login signals.
  Failed logins are IP-only: Home Assistant never logs an attempted
  username anywhere.
- **Permissions Matrix** — one grid for per-user dashboard/view visibility
  across every dashboard, labeled `enforced` or `cosmetic` on every toggle —
  because `lovelace/config` has no permission check at all; visibility
  changes what a user's UI renders, never what their account can fetch.
- **Integration Security Scanner** — static AST/regex analysis of every
  installed integration's source (core and custom) for security
  anti-patterns (disabled TLS verification, `shell=True` injection risk,
  `eval`/`exec`, insecure deserialization, hardcoded credentials, sensitive
  logging) — the exact gap `hassfest` structurally can't fill, since it only
  validates manifests/docs and never touches `custom_components` at all.
  Every finding is advisory, for the local instance owner only.
- **Device Vulnerabilities** — device-registry inventory, firmware-currency
  via `update` entities, and best-effort CVE correlation (curated CPE table
  + NVD API 2.0 keyword fallback), with a confirm/dismiss workflow.
- **Integration Health & Misconfiguration** — config-entry error/retry/
  availability tracking, plus concrete hardening checks (cleartext HTTP,
  `trusted_networks` permissiveness, disabled IP-ban, cleartext device admin
  URLs, cloud-egress inventory), mirrored into HA's own Repairs UI.
- **Risk Scoring & Security Posture** — an explainable, additive per-user
  risk score (0–100) and an install-wide posture score/grade, both shown
  with their contributing factors, never as an opaque number.
- **SOC Dashboard** — the NOC/SOC end state: posture score, open detections,
  device status, issues-by-integration, risk/detection breakdowns, and a
  live suspicious-activity feed — every tile and row links straight to the
  relevant tab or, where Home Assistant's own frontend supports a real
  preset filter, to its native Devices page.
- **Settings** — every configurable behavior (access control, MFA policy,
  audit retention/size, scanner toggles, NVD API key, risk-scoring window)
  as one panel-native form, backed by the exact same store as the native
  "Configure" dialog — change it from either place and the other reflects
  it immediately.
- **Access control** — the panel and every `ha_soc/*` command default to
  **account owner only**; a setting (Settings tab or the native Configure
  dialog) can open it to every administrator. Enforced server-side on each
  command, not just on sidebar visibility.
- **Network (UniFi Network / Protect)** — a Dashboard-style tab that talks
  directly to a UniFi console over the LAN with a local API key (read-only):
  network/internet status, WAN-port bandwidth, wireless-client and per-SSID
  counts, and Clients / Network Devices tables. Every client and device IP
  is correlated against Home Assistant's own config-entry hosts, so an
  integration whose device is a live client but whose config entry is
  failing to load is flagged **⚠ failing** — the "an integration IP is
  failing" signal. See below.
- **Host Probe (optional add-on)** — real listening-port visibility on the
  Home Assistant host itself, via the optional companion
  [HA SOC Probe](ha_soc_probe/) add-on. See below.
- **Entity ReMap** — finds and fixes broken/stale entity_id references
  across automations, scripts, scenes, Lovelace dashboards, and
  config-entry-backed helpers. Neither Home Assistant core nor
  [Spook](https://github.com/frenck/spook) (researched directly against
  both projects' source before building this — see below) actually solves
  this: renaming or replacing an entity only ever touches the entity
  registry, and everything that referenced the old entity_id keeps that
  exact string and silently breaks. Every reference found is labeled
  honestly editable or not — a reference living only inside a Jinja
  template is detected but never auto-rewritten, since a text edit there
  risks corrupting the template or missing a dynamic reference. A
  Spook-inspired proactive sweep also surfaces broken references as a
  dashboard donut and a Repairs issue without anyone needing to search
  for a specific entity first — see below for the full sweep, which now
  covers every reference kind in Spook's catalog (service/device/area/
  floor/label references, `alert`/notify-group/`person`/`group`/
  `proximity` unknown members, registry tidiness), each severity-scaled
  to how directly it can defeat a security-relevant automation.
- **Security Integrations Health** — an always-present Dashboard section
  covering the entities a security-focused install cares about most:
  every `lock`/`siren`/`valve` entity regardless of which integration owns
  it (state, "jammed"/unavailable problem flags, and battery level via the
  same device-registry-linked-sensor convention Home Assistant's own
  frontend uses for its battery icon), plus a Local Peripherals summary
  tile. Any tile backed by real devices links straight to those devices
  in Home Assistant's own Devices page (filtered by domain). Config-entry
  health for the curated integration allowlist (Kidde HomeSafe, Elk-M1
  Security, UniFi Protect, Keymaster, Emporia Vue) lives in Settings
  instead, alongside the per-source include/exclude toggles — each row
  reports honestly whether it's even installed (and links to its devices
  when it is) rather than being silently hidden just because a domain
  isn't present on this install.
- **Notify coverage gaps** — a config-hygiene check (HIGH severity) for a
  narrower, very concrete worry: an automation that calls `notify.*` when
  triggered by a lock/siren/valve entity or one of the named security
  integrations, where that source isn't tracked (or has been toggled off)
  in Security Integrations Health above. If that integration goes quietly
  unavailable, nothing on the dashboard reflects it and the only sign is
  the notification never arriving — this surfaces the gap instead.
- **Local Peripherals** — every USB serial device Home Assistant itself can
  see, its `/dev/tty` path, and a best-effort match against which
  integration (if any) is using it, with an Ignore action for devices
  that are intentionally unused. Reuses core's own USB discovery
  (`homeassistant.components.usb`) — the same data that already
  auto-detects a Zigbee/Z-Wave stick — rather than adding this to the
  Probe add-on: unlike host port scanning, serial-device visibility isn't
  structurally out of reach for a regular integration, so it doesn't need
  one.

## Icon / branding

`icon.png` (256×256), `icon@2x.png` (512×512), and the source `icon.svg`
live at the repo root — a shield, matching the sidebar panel's
`mdi:shield-search` icon. They're committed here for quick reference and
the GitHub repo card, but neither HACS nor Home Assistant's own "Add
Integration" search actually reads icons from a repo directly — both
source integration icons from the shared
[home-assistant/brands](https://github.com/home-assistant/brands) CDN. To
make this icon show up in either place, submit `icon.png` and
`icon@2x.png` there under `custom_integrations/ha_soc/` per that repo's
contribution guide. Until that PR merges, HA/HACS show a generic
placeholder instead — that's expected, not a bug here.

## Installation

1. Copy `custom_components/ha_soc/` into your Home Assistant `config/custom_components/` directory (or add this repo to HACS as a custom repository).
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **HA SOC**.
4. A **SOC** panel appears in the sidebar (admin accounts only).

## Versioning

Calendar versioning: `YYYY.MM.DD.V` — the release date plus a same-day
revision counter starting at 1 (e.g. the first release on August 23, 2026
is `2026.08.23.1`; a second release that same day would be `2026.08.23.2`).
Applies to both the integration (`manifest.json`) and the optional HA SOC
Probe add-on (`ha_soc_probe/config.yaml`), so a released version number is
always an unambiguous, directly comparable release identifier across the
whole project — never a pre-1.0 `0.x.y` number implying "still in
development." The current version is shown at the bottom of the panel on
every tab, and in HACS/Settings → Devices & Services → HA SOC the way any
integration's version is.

### Cutting a release (and why HACS needs one)

HACS installs an integration from a **GitHub Release**, whose tag points at
a commit whose tree must contain `custom_components/ha_soc/manifest.json`
with a matching `version`. Releasing by hand is where things drift — the
manifest version, the add-on version, and the tags fall out of sync, and
HACS then quotes a version that matches no release (surfacing as
`custom_components/None/manifest.json`, an unresolved domain).

One command keeps them in lockstep:

```bash
scripts/release.sh              # auto: today's date, next same-day revision
scripts/release.sh 2026.08.24.1 # or an explicit YYYY.MM.DD.N
```

It bumps the integration manifest, the add-on `config.yaml`, and the
add-on's `SCANNER_VERSION` together, runs the test suite, commits, and
pushes a tag **named exactly the version** (no `v`). Pushing that tag runs
[`.github/workflows/release.yml`](.github/workflows/release.yml), which
creates the GitHub Release HACS installs from — after first asserting the
tag equals the manifest version, so they can never disagree again.
[`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs the
HACS validator on every push, catching a manifest/`hacs.json` problem
before it can ship.

First install after this lands: in HACS remove and re-add the HA SOC
repository once, to clear any stale cached record. A private repo also
needs HACS authenticated with a GitHub account that can read it.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install homeassistant pytest-homeassistant-custom-component
pytest tests/

cd custom_components/ha_soc/frontend
npm install && npm run build
```

See `custom_components/ha_soc/frontend/README.md` for frontend details.

## Architecture

```
custom_components/ha_soc/
├── manifest.json / const.py / config_flow.py / store.py / __init__.py   — spine
├── users.py            — hass.auth wrapper: users, last-login, MFA, sessions
├── audit.py            — event capture, hash-chained JSONL storage, query
├── permissions.py       — dashboard/view visibility matrix, drift detection
├── health.py            — config-entry health, misconfiguration checks
├── vulns.py              — device inventory, firmware currency, NVD correlation
├── scanner.py            — static analysis of installed integrations' source
├── risk.py / detections.py — risk scoring engine, 12-rule detection catalog
├── mfa_policy.py         — audit-only/auto-deactivate enforcement for admins without MFA
├── probe.py              — optional HA SOC Probe add-on detection + result ingestion
├── peripherals.py        — USB/serial device visibility (Local Peripherals tab)
├── entity_remap.py       — find/fix broken entity_id references (Entity ReMap tab)
├── config_hygiene.py     — Spook-inspired broken-reference sweep (service/device/area/
│                           floor/label/alert/notify-group/person/group/proximity/registry)
├── security_health.py    — lock/siren/valve entities + curated integration health (Dashboard)
├── websocket_api.py      — the ha_soc/* command surface the panel calls
├── sensor.py / binary_sensor.py / repairs.py — entities + Repairs integration
├── panel.py              — sidebar panel registration
└── frontend/             — Lit + TypeScript panel (dist/ committed)

ha_soc_probe/              — optional companion add-on (see below)
repository.yaml             — marks this repo as a Supervisor add-on repository too
```

Every backend module is independently documented with what it captures,
what's enforced vs. cosmetic vs. best-effort, and its known coverage gaps —
read the module docstrings, they're written for exactly that.

## Honesty, briefly

- MFA can be **audited** always, and **enforced** only in the one way Home
  Assistant core actually allows: deactivating an admin account that stays
  out of compliance past a configurable grace period (`auto_deactivate`
  policy, off by default). There is still no hook to require a second
  factor at login itself.
- Dashboard/view visibility is **cosmetic** — the real access-control
  boundary is a user's admin/non-admin group, nothing finer exists.
- Failed-login telemetry is **IP-only** — Home Assistant never logs an
  attempted username on a failed login, anywhere.
- Every vulnerability/scanner finding is **advisory** — a starting point for
  a human to confirm or dismiss, never an automatic verdict.
- The audit log is **tamper-evident, not tamper-proof** — anyone with the
  filesystem access that reaches `.storage/` can rewrite the hash chain too.

## Optional: HA SOC Probe add-on

Real listening-port visibility on the Home Assistant **host** is
structurally out of reach for a Python integration — even on Home
Assistant OS, the integration only ever sees its own container's network
namespace. The two other things once considered for a companion add-on
(whether an SSH-capable add-on is exposed on the host network, and Home
Assistant's own config-check status) turned out to be reachable from
inside the integration itself instead, and now live in `health.py`'s
misconfig checks (`ssh_addon_exposed`, `ssh_addon_inventory`,
`addon_unprotected`, `ha_config_invalid`) — no add-on needed for those.

**HA SOC Probe** (source at [`ha_soc_probe/`](ha_soc_probe/)) is the
small, optional, Home-Assistant-OS/Supervised-only add-on for the one
thing that does need a separate container: it runs with `host_network:
true`, reads the host's real `/proc/net/tcp[6]` connection table, and
reports every listening TCP port back to the integration via a
`ha_soc.ingest_probe_result` service call over Supervisor's Core API
proxy — the standard mechanism any add-on uses to call back into Home
Assistant, no new communication channel invented here. Deliberately
port + protocol only, never a process name (that would need `host_pid:
true`, a second elevated privilege this add-on doesn't ask for) and never
active scanning (it only reads the kernel's own connection table, so it
never generates outbound traffic).

To install: Settings → Add-ons → Add-on Store → ⋮ → Repositories → add
this repository's URL, then install **HA SOC Probe** from the list. The
integration's Scanner tab shows a "not available" (Core/Container) or
"not installed" (Supervisor, add-on absent) state honestly whenever the
add-on isn't there to provide this data — never silent, empty results
that could be misread as "scanned, nothing found."

If the add-on is installed and running but the integration keeps
rejecting its reports (typically a brief window right after Home
Assistant Core itself restarts, while this integration is still
loading), the add-on holds in a short, capped retry loop instead of
waiting out its full `scan_interval_hours` — and if that stuck state
lasts more than 30 minutes, `health.py` raises a Repairs issue
(`probe_addon_not_reporting`) so a half-set-up pairing is visible in
Home Assistant itself, not just the add-on's own log.

The add-on's config.yaml/Dockerfile/run-script were written and reviewed
against Home Assistant's official add-on documentation and real, current
official add-ons, and its port-extraction logic was tested against a
realistic `/proc/net/tcp` fixture — but unlike the integration itself
(validated against a real `pytest-homeassistant-custom-component` harness),
it has not yet been built and run against a real Supervisor. See
[`ha_soc_probe/DOCS.md`](ha_soc_probe/DOCS.md) for the same note.

## Integration Security (provenance)

The Integration Security tab scores where each installed integration's code
*came from* — it is a **provenance** signal, not a safety verdict. Home
Assistant runs integrations in-process with no sandbox, so nothing here
proves any integration is safe to run; a high-provenance integration can do
anything a low-provenance one can. Every surface says so, and the tab never
renders "Safe"/"Verified"/"Trusted" or a bare shield.

Each installed integration is classified into a **tier** — Core (ships in
HA, hassfest-validated), HACS-managed, or unmanaged Custom — and shown with
signals gathered two ways:

- **Local, always available** (no network, no privilege): tier, the
  manifest's `quality_scale`/`integration_type`, whether a license file is
  present, and any findings from this project's own integration scanner.
  Where HACS is installed and its per-repo source is introspectable, the
  two lowest-provenance HACS origins — a custom repository or a custom
  source-list — are flagged (default-store HACS content is not).
- **GitHub-derived, optional**: release-vs-branch, commit-signing/identity
  assurance, maintenance recency, popularity, and archived status. These
  need an outbound GitHub call and an optional token (set in the owner-only
  Settings tab, which also raises GitHub's rate limit from 60 to 5,000
  requests/hour). Without a token every GitHub signal is honestly shown as
  "not collected" — never guessed.

All HA SOC settings, including that token, live in the **Settings tab,
which is available to the account owner only** — a non-owner admin sees it
disabled. The native "Configure" dialog edits nothing (it can't identify
the requesting user, so it can't enforce owner-only), pointing to the panel
instead.

See [`custom_components/ha_soc/integration_security.py`](custom_components/ha_soc/integration_security.py)
and [`github_provenance.py`](custom_components/ha_soc/github_provenance.py).

### Container Resource Usage

The same tab also shows **live per-container CPU and memory** — every add-on
plus Home Assistant Core and the Supervisor — for spotting the container
that's crashing or starving the host. Each row shows CPU %, memory % with
used/limit, network, and disk IO; a container near its **memory limit** (the
OOM-kill precursor) or pinning CPU is flagged and sorted to the top, and a
stopped add-on is flagged `not running`. Stats are fetched on demand from
the Supervisor (`get_supervisor_client`), not the hassio integration's cache
(which is empty unless the per-add-on stats sensors are enabled). This needs
a Supervisor-based install (HA OS / Supervised); on a Container/Core install
the section says so rather than erroring. See
[`custom_components/ha_soc/containers.py`](custom_components/ha_soc/containers.py).

### Resource Watchdog & hard caps

Supervisor exposes **no API to cap an add-on's CPU or memory** (verified
against the full `aiohasupervisor` client surface), so a runaway add-on can
eat the host until the kernel OOM-kills something — often not the guilty
container. HA SOC covers this two ways, matching what the platform allows:

- **Watchdog (supported APIs only, opt-in).** Samples per-container stats
  on an interval and acts only on a *sustained* breach (N consecutive
  samples over the per-container or default threshold — a one-sample media
  scan spike trips nothing). On a trip it records a detection +
  notification + audit entry and takes the configured action: alert,
  **restart**, or stop the add-on via the real Supervisor API. Two rules are
  hard-coded: Core and the Supervisor are never auto-restarted (alert-only,
  whatever the config), and after 3 enforcement actions on one container in
  an hour the watchdog downgrades it to alert-only — an add-on that
  re-breaches after every restart is a restart *loop*, and looping it
  forever is worse than saying so.
- **Hard caps (explicit escape hatch, owner-only).** Real Docker limits
  (`--memory`/`--cpus` equivalents) per add-on, delivered to the HA SOC
  Probe over its existing poll channel and applied against the Docker
  socket. This requires the Probe add-on's **Protection Mode to be
  disabled** — a root-equivalent grant the panel spells out before anything
  applies; with protection on, every application honestly reports
  *denied*. Because Supervisor recreates containers on add-on
  updates/restarts (silently dropping any Docker-level limit), the Probe
  re-applies the caps every ~60 s. A capped add-on that exceeds its memory
  limit is OOM-killed by the kernel; Supervisor's own add-on watchdog then
  restarts it if enabled.

Both live on the Integration Security tab's Container Resource Usage card;
all configuration is owner-only and audit-logged. See
[`custom_components/ha_soc/resource_watchdog.py`](custom_components/ha_soc/resource_watchdog.py).

## Firewall Rules (read and write)

Everything else in this project observes and reports; it never mutates a
host security control. The Firewall Rules card, on the Scanner tab, is
the one deliberate exception — reading, and optionally writing, the host's
iptables rules through the HA SOC Probe add-on. It needs the add-on to
declare a real `CAP_NET_ADMIN` (`privileged: [NET_ADMIN]` in its
`config.yaml`), which lowers the add-on's Supervisor security rating by
one point — a documented, deliberate trade-off, not an accident.

The design exists to answer one question safely: change which ports are
reachable from where without risking a lockout.

- Every rule this project ever applies lives in one dedicated iptables
  chain (`HA_SOC_RULES`) the add-on owns outright — never the host's raw
  `INPUT` chain, never anything Docker itself manages.
- A proposed ruleset is never permanent on arrival. Proposing one requires
  acknowledging that the current ruleset will be backed up first; the
  button that starts this reads **Test**, and relabels itself **Apply**
  once the change is live, alongside a running countdown (30–60s).
- The countdown is enforced by a **local, self-contained timer inside the
  add-on process** — a plain backgrounded `sleep`, not a scheduled
  callback from Home Assistant. If the new rules break the very network
  path Core would need to tell the add-on to revert, the revert still has
  to happen without that path working, so nothing about it depends on
  that path. If you don't click Apply in time (or the add-on itself
  crashes mid-test), the pre-change ruleset is restored automatically —
  an interrupted test is always treated as failed, never as "probably
  still fine."
- Core only ever proposes and displays; the add-on is the only thing that
  actually touches iptables, and its own report is always the final word
  on what's really active.

See [`custom_components/ha_soc/firewall.py`](custom_components/ha_soc/firewall.py)'s
module docstring for the full state machine and
[`ha_soc_probe/DOCS.md`](ha_soc_probe/DOCS.md)'s "Firewall rules" section
for the add-on side of the same design.

## Network tab (UniFi Network / Protect)

The **Network** tab talks directly to a UniFi console over your LAN with a
**local API key** (UniFi OS → Settings → Control Plane → Integrations),
using an `X-API-KEY` header — no cloud round-trip, no second add-on, and
nothing ever leaves your network. It is entirely **read-only**: it lists
clients and network devices and derives a WAN/internet status; it never
changes controller state.

Configure it in **Settings** (owner-only), where UniFi Network and UniFi
Protect each get a host, a local API key (stored as a secret — masked in
the API, redacted in the audit log), and a TLS-verify toggle (off by
default, since consoles ship a self-signed certificate).

The tab shows, close to the Dashboard's layout: network status, WAN-port
bandwidth, internet-connected, wireless-client count, per-SSID totals, and
two tables:

- **Clients** — Client, IPv4, IPv6, MAC, VLAN, SSID, Uptime, Bandwidth, Last
  Seen, Integration. Uptime is derived from the client's association
  timestamp; SSID is joined from the `/wifi/broadcasts` collection. Filters
  by **VLAN** and **SSID**, and clicking an SSID in the "Clients per SSID"
  card filters the table to it.
- **Network Devices** — Device, IPv4, MAC, VLAN, Model, **Firmware
  Updatable**, Bandwidth, Last Seen, Integration (no IPv6/Uptime — not
  applicable to infrastructure). Each device is enriched from its
  `/devices/{id}` detail endpoint for bandwidth / last-seen / firmware
  status.

There is also an **ACL Rules — Security Audit** report: every ACL / firewall
rule the controller exposes, **in evaluation order**, with the action, the
networks each rule applies to, direction, protocol, and enabled state — for
auditing that a later "deny" isn't shadowed by an earlier "allow". The
controller's Integration API is probed for the rules at several candidate
paths; if none respond, the report says so honestly (and lists what it
tried) rather than showing a fabricated ruleset.

**UniFi Protect** gets two tables of its own:

- **Devices** — name, IP, MAC, recording state, last ring, and channels.
  Each device name deep-links to that camera on the Protect console
  (`https://<host>/protect/dashboard/devices/<id>`), built from the device
  `id` the API returns.
- **Events & AI Smart Detections** (last 24h) — event type, smart-detection
  types, score, start, duration, thumbnail, and license plate. A thumbnail
  that's a direct URL links out; one that needs an authenticated fetch is
  marked "available" and links to the camera page instead of showing a
  broken image.

The **Integration column** is the point of the whole tab: every client/
device IP is matched against every Home Assistant config entry's host, and
when a matched integration's config entry is in a setup-error/retry state
the row is flagged **⚠ failing**. A device that's a live client on the
network but whose integration won't load is exactly the "an integration IP
is failing" case — the device is reachable, so the fault is the
integration, not the network — and it's surfaced with a banner at the top.

> **Field-mapping caveat.** Ubiquiti's local API field names could not be
> verified against a live controller while building this, so
> [`unifi.py`](custom_components/ha_soc/unifi.py) resolves every field from a
> list of candidate names spanning the Integration API (camelCase) and the
> legacy controller API (snake_case), and anything a given controller
> doesn't return renders as `—` rather than being guessed. Fields most
> likely to need confirmation against your firmware (VLAN, IPv6, the
> client→SSID reference key, bandwidth, the WAN-port stats, the ACL/firewall
> endpoint path and rule fields, device `firmwareUpdatable`, and — on the
> Protect side — `isRecording`, `channels`, the events path, and the
> license-plate location) are marked `# VERIFY` in that module. If a column
> reads `—` for you, that field name is the thing to confirm against your
> console's API response. Protect events in particular are delivered over a
> websocket subscription on current firmware rather than a REST list, so the
> Events table degrades to an explanatory note there.

## Entity ReMap, config hygiene, and what's borrowed from Spook

Before building this, both [Spook](https://github.com/frenck/spook) (a
well-known, actively developed, MIT-licensed HACS add-on) and Home
Assistant core itself were checked directly against their source —
not from memory — to answer two questions honestly.

**What does Spook actually do?** Its ~114-item catalog splits into ~73
"services" (mostly exposing already-possible admin actions — area/label
CRUD, entity enable/disable — as automatable; genuinely useful, but not
something a SOC report would flag) and 41 automated "chores": 37 are
variations on "does this automation/script/scene/dashboard/helper
reference an entity/area/device/floor/label that no longer exists," the
remaining 4 are pure registry tidiness (empty areas/floors, unused
labels/blueprints), and exactly one — stale long-lived access tokens
unused for 180+ days — is a genuine credential-hygiene finding on its own
(adopted via an original implementation against `hass.auth`, not Spook's
code, mirrored into Repairs; see `repairs.py`).

That first pass under-weighted the 37 broken-reference chores: even
though a stale reference isn't a vulnerability by itself, it can silently
defeat a security-relevant automation — an `alert:` that stops paging
about a leak, a notify group that quietly drops a recipient, an
automation action calling a service that no longer exists. **Every
reference kind in Spook's chore catalog is now covered**, in
`config_hygiene.py` (verified against the installed Home Assistant
package before writing a line — service calls via a recursive walk of
each automation/script's validated config; device/area/floor/label
references via Home Assistant's own `referenced_devices`/`referenced_areas`
family, the same mechanism `entity_remap.py` already uses for entities;
`alert:`/legacy notify-group config via `homeassistant.config`'s merged-YAML
re-parse, since neither stores its live config anywhere queryable;
`person`/`group` members via their state attributes; `proximity` via its
config entry — confirmed migrated off YAML entirely in the installed
core version). Severity scales with how directly the broken reference can
defeat a security control (`alert:` references are high; pure registry
tidiness like empty areas or orphaned statistics is informational-only,
never mirrored to Repairs, matching this project's existing inventory-only
findings) — every one of the 41 chores is collected and reported, exactly
none silently dropped, but not every one gets the same loudness.

One real, dynamically-tested finding from building this: Home Assistant
already validates a device trigger/condition/action against the device
registry at automation *setup* time and disables the whole automation
with its own clear error if the device never existed — so
`unknown_device_references` can only ever catch the narrower, still-real
case of a device that existed when the automation last loaded and was
*later* removed from the registry.

**Does Spook (or core) fix broken references?** No — verified directly in
both codebases, not assumed. Renaming an entity's ID, in core's UI or via
Spook's own `homeassistant.update_entity_id` service (itself a thin
wrapper over the same core registry call), only ever updates the entity
registry entry itself; nothing listens for that change and rewrites the
automations/scripts/scenes/dashboards/helpers that still hold the old
literal string. Spook's own broken-reference chores can *detect* the
fallout after the fact, but explicitly do not fix it (`is_fixable=False`
on every one of them). This is genuine, unclaimed gap — **Entity ReMap**
is that fix, built from scratch against Home Assistant's own APIs:

- **Automations / scripts / scenes** — real, structured references (a
  trigger's `entity_id:`, a service call's `target:`) are rewritten by
  replicating the exact read/lock/atomic-write/reload sequence
  `homeassistant.components.config`'s own editor views use internally
  (there's no importable library function for this). A reference that
  only exists inside a Jinja template is *never* rewritten — only
  detected and flagged for manual review, since a text-level rewrite
  there could corrupt the template or miss a computed reference.
- **Views (Lovelace dashboards)** — storage-mode dashboards are freely
  read/writable through the same object core's own frontend uses.
  YAML-mode dashboards are a confirmed, hard dead end (core's own
  `LovelaceYAML.async_save()` raises `HomeAssistantError("Not
  supported")`) and are reported as "manual edit required," never
  silently skipped.
- **Helpers** — the 13 config-entry-backed helper domains that store a
  source entity_id as a plain option field (derivative, utility_meter,
  threshold, generic_thermostat, generic_hygrostat, integration, min_max,
  filter, switch_as_x, trend, history_stats, statistics, mold_indicator —
  every field name verified against the installed package, not guessed)
  are rewritten directly. Template helpers, and any other config entry
  that merely *mentions* the entity_id in its stored data, get the same
  detect-only treatment as templated automation fields.

Nothing here performs an entity registry rename — Entity ReMap only ever
touches the *consuming* configuration. If the old entity_id should also be
renamed in the registry, that's Home Assistant's own existing Settings >
Entities rename, unaffected by and safe to combine with what this module
does.
