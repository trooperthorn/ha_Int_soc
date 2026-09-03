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
  service calls, user/dashboard changes, registry and config-entry
  changes, best-effort login signals, and HA SOC's own actions,
  including privileged reads (host and add-on logs, the crash log, a
  user's token list). Failed logins are IP-only: Home Assistant never
  logs an attempted username anywhere. High-value records (user
  changes, firewall actions, rejected probe calls, privileged reads)
  flush to disk immediately rather than waiting for the periodic timer,
  and deleting or rolling back the on-disk chain is detected against a
  head mirrored in the main store, raising a Repairs issue and chaining
  the discontinuity itself.
- **SIEM export** — finalized audit records can be exported as RFC 5424 with
  canonical audit JSON (the backward-compatible default), RFC 5424 with a
  genuine HA SOC CEF 0 payload, or bare canonical JSON for collectors that
  explicitly require JSON-only input. Transport is selected independently:
  verified TLS is preferred, with TCP and UDP plaintext fallbacks. TCP/TLS use
  RFC 6587 octet-counting; every format retains `seq`, `prev_hash`, and `hash`
  for receiver-side gap/chain checks. Export is disabled by default, bounded,
  retried without blocking Home Assistant, and exposes format/queue/drop/error
  status.
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
  Four rules target the cross-integration extraction patterns no design
  can prevent in Home Assistant's shared process: indiscriminate or
  foreign config-entry reads consumed wholesale, `.storage` and
  `secrets.yaml` file access, foreign `hass.data` reads, and storage
  keys outside the integration's own namespace. A matched credential
  literal is never stored or exported, only a masked placeholder with
  its length. Legitimate uses are acknowledged visibly in source with a
  reasoned `# ha-soc-allow` marker, never silently skipped, and a test
  holds HA SOC's own code to zero open findings from these rules.
  Coverage is honest: the scanner records per domain what it scanned,
  skipped, and failed to parse, a domain it never scanned reads "not
  scanned" rather than "0 findings", findings absent on a rescan of
  their file resolve themselves, and the rules are stated plainly to
  detect unobfuscated instances only.
  Every finding is advisory, for the local instance owner only.
- **Device Vulnerabilities** — device-registry inventory, firmware-currency
  via `update` entities, and best-effort CVE correlation (curated CPE table
  + NVD API 2.0 keyword fallback), with a confirm/dismiss workflow.
  Disclosure: while `nvd_lookups_enabled` is on (the default, toggle in
  Settings), device manufacturer and model strings are sent to NIST's
  NVD service over HTTPS; nothing else leaves the instance for this
  feature, and vendor-wide matches are reported as informational only.
- **Integration Health & Misconfiguration** — config-entry error/retry/
  availability tracking, plus concrete hardening checks (cleartext HTTP,
  `trusted_networks` permissiveness, reverse-proxy trust breadth,
  disabled IP-ban, cleartext device admin URLs, cloud-egress inventory,
  config-directory-mapping add-ons, backup protection), mirrored into
  HA's own Repairs UI. The sweep waits out startup so half-loaded state
  is never misread as misconfiguration, findings you confirmed survive a
  pass that could not see their evidence, and a check that could not
  evaluate says so instead of going quiet.
- **Risk Scoring & Security Posture** — an explainable, additive per-user
  risk score (0–100) and an install-wide posture score/grade, both shown
  with their contributing factors, never as an opaque number. Every
  factor carries its applied points so the list sums exactly to the
  score, the posture grade is labeled provisional (with the missing
  terms listed) until every term has computed from real data at least
  once, and every detection threshold is owner-tunable in Settings with
  the most-sensitive value as its default and a one-click reset. The
  posture sensor's attributes expose the grade only; the full breakdown
  stays behind the access-controlled API, since entity attributes are
  readable by every authenticated user.
- **Protected Security Console** — six workspaces (Overview, Assets, Findings,
  Identity, SIEM & Audit, and owner-only Settings) organize the existing
  access-gated views without changing their server-side permissions or saved
  per-user layouts. Overview presents posture, trend, open detections,
  operational availability, vulnerability severity, and investigation queues;
  every actionable tile links to the protected leaf view or, where Home
  Assistant supports a real preset filter, its native Devices page. The visual
  and data-boundary decisions are recorded in
  [`docs/FRONTEND-VISUAL-ARCHITECTURE.md`](docs/FRONTEND-VISUAL-ARCHITECTURE.md).
- **Settings** — every configurable behavior (access control, MFA policy,
  audit retention/size, scanner toggles, NVD API key, risk-scoring window)
  as one panel-native form, backed by the exact same store as the native
  "Configure" dialog — change it from either place and the other reflects
  it immediately.
- **Logs:** three log sources in one tab. Home Assistant's own captured
  WARNING/ERROR/CRITICAL records (the same buffer as Settings > System >
  Logs, deduplicated, filterable by integration and level, tracebacks
  expandable in place); the `home-assistant.log.fault` crash dump,
  surfaced read-only because a non-empty file means Core itself died at a
  fatal signal at least once; and, on Supervisor installs, the full
  container log of any app or add-on (Core, Supervisor, the host journal,
  or any installed add-on) fetched through the Supervisor's journald
  gateway, ANSI-stripped and tail-capped to the newest 128 KB. Add-on
  targets are validated against the Supervisor's own installed-add-on
  list before the slug ever reaches a URL.
- **Access control** — the panel and every `ha_soc/*` command default to
  **account owner only**; a setting (Settings tab or the native Configure
  dialog) can open it to every administrator. Enforced server-side on each
  command, not just on sidebar visibility.
- **Network (UniFi Network / Protect)** — a Dashboard-style tab that talks
  directly to a UniFi console over the LAN with a local Integration API key
  (read-only), verified against Network 10.4.57 and Protect 7.2.105:
  network/internet status, WAN-port bandwidth, wireless-client and per-SSID
  counts, and Clients / Network Devices tables. Every client and device IP
  is correlated against Home Assistant's own config-entry hosts, so an
  integration whose device is a live client but whose config entry is
  failing to load is flagged **⚠ failing** — the "an integration IP is
  failing" signal. See below.
- **Network Security** — a dedicated tab tying together **Firewall
  Policies** (UniFi's zone-based default allow/deny UI) and **ACL Rules**
  — two genuinely separate UniFi resources, both read and audited in
  evaluation order with their ports, protocols, source/destination/zones,
  and the networks each applies to — the Home Assistant server's own
  **listening ports cross-referenced against both rule sets** (via the
  optional Host Probe add-on), a **Pi-hole** DNS section (blocking status,
  query totals, whether your IoT subnet has its own scoped client group,
  top blocked domains), and an **advisory findings list** derived from all
  four — e.g. a rule/policy with no source/destination scoping at all, a
  server port nothing names, or an IoT subnet falling through to Pi-hole's
  global Default group. Entirely read-only and advisory: nothing here ever
  edits a UniFi rule or policy, toggles Pi-hole, or reassigns a Pi-hole
  client. See below.
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
  risks corrupting the template or missing a dynamic reference. Applying
  a remap backs everything up first: YAML files are copied aside and
  storage dashboards and helpers get JSON snapshots under
  `.storage/ha_soc_remap/` (kept 30 days), and a YAML file containing
  `!secret` or `!include` is refused as "manual edit required" because a
  rewrite would inline the include destructively. A
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

Every data table in the panel sorts by any column. The header cells are
real buttons (keyboard focusable, activatable with Enter or Space) and the
`th` carries `aria-sort`, so the current order is announced by assistive
technology rather than conveyed only by an arrow glyph. Unknown or empty
values always sink to the bottom of a sort in either direction: an unknown
value is not "smallest", it is unknown.

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

Calendar versioning, displayed as `vYYYY.MM.DD.V`: the release date plus a
same-day revision counter starting at 1 (e.g. the first release on
August 30, 2026 is `v2026.08.30.1`; a second release that same day is
`v2026.08.30.2`). One version number covers the integration and the
optional HA SOC Probe add-on together, so a release identifier is always
unambiguous and directly comparable across the whole project, never a
pre-1.0 `0.x.y` number implying "still in development."

The `v` prefix is the canonical form everywhere a person reads a version:
git tags, GitHub Releases, HACS (which displays and installs by the
release tag name itself), this repo's changelogs, and the version footer
at the bottom of every panel tab. Exactly three machine-read fields carry
the bare number instead - `custom_components/ha_soc/manifest.json`
`version`, `ha_soc_probe/config.yaml` `version`, and the probe's
`SCANNER_VERSION` - because Home Assistant, the Supervisor, and the
release workflow compare those values with the prefix stripped. The
mapping is enforced, not remembered: CI refuses a version mismatch, and the
Release workflow refuses to publish unless the manifest, Probe, and scanner
versions agree. `scripts/release.sh` bumps all three fields and opens an
auto-merge pull request. After its required checks pass, the merge to `main`
creates the canonical `v`-prefixed tag and Release automatically.

### Cutting a release (and why HACS needs one)

HACS installs an integration from a **GitHub Release**, whose tag points at
a commit whose tree must contain `custom_components/ha_soc/manifest.json`
with a matching `version`. Releasing by hand is where things drift — the
manifest version, the add-on version, and the tags fall out of sync, and
HACS then quotes a version that matches no release (surfacing as
`custom_components/None/manifest.json`, an unresolved domain).

One command starts the protected, automated release path:

```bash
scripts/release.sh               # auto: today's date, next same-day revision
scripts/release.sh v2026.08.30.2 # or an explicit version (bare form accepted too)
```

It bumps the integration manifest, the add-on `config.yaml`, and the
add-on's `SCANNER_VERSION` together, runs available local checks, and opens a
pull request configured to merge only after GitHub's required checks pass.
The resulting `main` push runs
[`.github/workflows/release.yml`](.github/workflows/release.yml), which creates
the tag, deterministic `ha_soc.zip`, SPDX SBOM, `SHA256SUMS`, signed build and
SBOM attestations, and GitHub Release. HACS installs that exact ZIP; unversioned
default-branch downloads are hidden.

Published artifacts can be verified independently:

```bash
gh release download vVERSION -R trooperthorn/ha_Int_soc \
  -p ha_soc.zip -p SHA256SUMS
sha256sum --check SHA256SUMS --ignore-missing
gh attestation verify ha_soc.zip -R trooperthorn/ha_Int_soc
```
[`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs the
HACS validator on every push, catching a manifest/`hacs.json` problem
before it can ship.

First install after this lands: in HACS remove and re-add the HA SOC
repository once, to clear any stale cached record. A private repo also
needs HACS authenticated with a GitHub account that can read it.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-test.txt
pip install -r requirements-core.txt
pytest tests/

cd custom_components/ha_soc/frontend
npm install && npm run build
```

See `custom_components/ha_soc/frontend/README.md` for frontend details.

Design rationale, protocol facts, operational knobs, and dated decisions live
under `docs/`; start at [`docs/README.md`](docs/README.md), which says which
document owns which topic.

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
├── logs.py               — fault-log reader + Supervisor container/add-on log access (Logs tab)
├── unifi.py              — UniFi Network/Protect data for the Network tab; ACL rules,
│                           Firewall Policies, and HA-server-port correlation for the
│                           Network Security tab
├── pihole.py             — Pi-hole v6 direct API client (Network Security tab's DNS section)
├── network_security.py   — advisory findings tying rules/policies/ports/Pi-hole together
├── firewall.py           — host firewall read/test/confirm state machine (with the add-on)
├── integration_security.py — per-integration provenance/trust signals (Integration Security tab)
├── containers.py         — per-container CPU/memory usage via Supervisor stats
├── resource_watchdog.py  — sustained-overuse watchdog + optional Docker hard caps
├── diagnostics.py        — redacted config-entry diagnostics (safe to attach to an issue)
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

## Secrets at rest

Every credential HA SOC holds (the NVD and GitHub keys, the UniFi API
keys, the Pi-hole app password, the Probe pairing secret) lives in one
dedicated private store,
`.storage/ha_soc.secrets`, written 0o600 and atomically, the same
primitive Home Assistant core uses for its own password hashes and
refresh tokens. Nothing else carries a value: settings hold only
"configured" booleans, `entry.options` is scrubbed and never reseeded,
audit records and diagnostics redact at their chokepoints, and callers
fetch a key immediately before the request that needs it and drop it
with the response. Existing installs migrate automatically on first
load, logged with key names only.

Two honest limits, stated because pretending otherwise would be the real
defect. First, Home Assistant runs every integration in one Python
process: any integration can reach this store's contents in memory, and
no arrangement inside Core changes that. What HA SOC does instead is
shrink the number of places a secret exists, read only location-shaped
keys (`INTEGRATION_LOCATOR_KEYS`) out of other integrations' entries so
it is itself the model citizen, and detect the extraction patterns it
cannot prevent (the four scanner rules above). Second, file modes
protect against other uids, not against root or anything with the
config directory mapped; the misconfiguration sweep now flags add-ons
that widen that boundary, unprotected backups, and unauthenticated
Samba shares of the config directory.

## Honesty, briefly

- MFA can be **audited** always, and **enforced** only in the one way Home
  Assistant core actually allows: deactivating an admin account that stays
  out of compliance past a configurable grace period (`auto_deactivate`
  policy, off by default). There is still no hook to require a second
  factor at login itself. The policy assesses Home Assistant's own MFA
  modules only: a user whose every credential comes from an external
  provider (an SSO proxy, trusted networks) is exempt from
  `auto_deactivate` and reported as **MFA not assessable**; an install
  authenticating externally should keep `audit_only`.
- Dashboard/view visibility is **cosmetic** — the real access-control
  boundary is a user's admin/non-admin group, nothing finer exists.
- Failed-login telemetry is **IP-only** — Home Assistant never logs an
  attempted username on a failed login, anywhere. Capturing even the IP
  depends on the `homeassistant.components.http.ban` logger staying at
  WARNING or lower; a health check flags an install that has silenced it.
- Every vulnerability/scanner finding is **advisory** — a starting point for
  a human to confirm or dismiss, never an automatic verdict.
- The audit log is **tamper-evident, not tamper-proof** — anyone with the
  filesystem access that reaches `.storage/` can rewrite the hash chain too.
  Retention does not break this: when expired day files are deleted, the
  newest expired record's sequence number and hash are kept as an anchor,
  verification restarts from it, and the panel says "verified from record
  N; records before D expired under retention" rather than pretending the
  whole history was re-checked. Records before the anchor are attested by
  the anchor's stored hash, not re-verified record by record.
- A failed load is never shown as "no data" or left as an endless spinner.
  Every panel view catches its own load failure into a distinct
  could-not-load state, with the server's message and a Retry button,
  so a WebSocket error is never mistaken for an empty result or a specific
  backend state (e.g. "USB discovery isn't available") it did not actually
  report.

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
small, optional, Home-Assistant-OS/Supervised-only add-on for host-scoped
functions that need a separate container: it runs with `host_network:
true`, reads the host's real `/proc/net/tcp[6]` connection table, and
reports every listening TCP port back to the integration via a
`ha_soc.ingest_probe_result` service call over Supervisor's Core API
proxy — the standard mechanism any add-on uses to call back into Home
Assistant, no new communication channel invented here. Deliberately
port + protocol only, never a process name (that would need `host_pid:
true`, a second elevated privilege this add-on doesn't ask for) and never
active scanning (it only reads the kernel's own connection table, so it
never generates outbound traffic). It can also host an optional,
owner-configured Net-SNMP agent for standards-based monitoring export.

**Who may call the Probe callback services.** The Supervisor's Core API
proxy forwards every add-on call with the Supervisor's own token and no
add-on identity, so Core sees each legitimate call as the Supervisor
system user. HA SOC therefore accepts `ha_soc.ingest_probe_result` and
`ha_soc.poll_firewall_command`, and `ha_soc.poll_snmp_config` only when the call carries that exact user
context; anything else, including an automation with no user context, is
rejected before the payload is read, audit-logged as
`probe_auth_rejected`, and raised as a HIGH detection (at most one per
caller per hour). The per-install shared secret remains as defense in
depth behind that check: a call with no secret is always rejected, the
comparison is constant-time, and the secret can only ever be pinned by a
call that already passed the Supervisor check. The owner-only pairing
reset in Settings still exists for reinstalling the add-on. On Home
Assistant Core and Container installs the services are not
registered at all, since no Supervisor exists to legitimately call them.

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

Since 2026-08-30 the add-on runs in production on the owner's Home
Assistant OS install: two read-only verification passes (work plan
decision D-21) confirmed it installs, scans, and reports on a real
Supervisor 2026.08.0, that the hold-and-retry path recovers from a Core
restart exactly as designed, that the Supervisor rates it 1 as the
privilege ledger states, and, at the container level, that both the
add-on and the host use the nf_tables backend, that ip6tables works,
that the container runs unprivileged with only NET_ADMIN added under
the docker-default AppArmor profile, and that the Docker socket is
genuinely unmounted under Protection Mode. The full verified-facts
list lives in [`ha_soc_probe/DOCS.md`](ha_soc_probe/DOCS.md).

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
`config.yaml`).

**The add-on's Supervisor security rating is 1, the lowest, and that is a
deliberate choice.** The Supervisor's rating algorithm sets the rating to
1 unconditionally for any add-on declaring `docker_api` (verified against
the Supervisor source, `rating_security`, commit `c5a5477`), so no
arrangement of the other grants changes the number while hard caps exist.
The project decided (work plan decision D-2) to ship one companion add-on
carrying every host-level capability the SOC needs, rather than several
partially privileged ones, and to document each grant instead of chasing
the score. The privilege ledger below states every grant, the feature
that needs it, what breaks without it, and how its use is limited; the
same ledger lives in [`ha_soc_probe/DOCS.md`](ha_soc_probe/DOCS.md).

| Grant | Needed by | What the add-on does with it | Without it | How its use is limited |
| --- | --- | --- | --- | --- |
| `host_network` | Port report and optional SNMP | Shares the host's network namespace so `/proc/net/*` and IF-MIB counters describe host interfaces; permits binding the configured host IP | Port data and interface counters would describe only the container | Read-only observation by default; when SNMP is enabled, one explicit-address UDP listener is opened—wildcard binds are rejected |
| `privileged: [NET_ADMIN]` | Firewall read/test/confirm | Runs `iptables` against the host's real netfilter tables | The firewall card cannot read or write anything; the port report still works | Writes stay in the dedicated `HA_SOC_RULES` chain plus exactly one jump rule at the top of `INPUT` into that chain; full ruleset backup before every apply; local self-contained revert timer |
| `docker_api` | Resource hard caps | Applies per-container `--cpus`/`--memory` limits through the Docker socket | Hard caps report `denied`/unavailable; the watchdog's Supervisor-API restart and stop actions still work | With Protection Mode on (the default) the Supervisor does not mount the socket at all; slugs are validated against the installed add-on list; only container update calls are issued |
| `homeassistant_api` | Everything | Delivers reports and polls firewall/SNMP configuration through the Supervisor proxy | The add-on cannot report anything | Calls only the three internal `ha_soc` services, carrying the pairing secret; Core additionally requires the call to arrive with the Supervisor's own user context |
| Protection Mode off (your toggle) | Hard caps only | Grants the Docker socket mount | Everything except hard caps works with protection on | The panel states the root-equivalent consequence before any cap is applied, and every application is audited |

### SNMPv3 monitoring export

The Probe can expose host-network, CPU, memory, and container-visible storage
telemetry to SolarWinds or another standards-compatible NMS. It is disabled by
default and supports only SNMPv3 USM AuthPriv with SHA-256 authentication,
AES-128 privacy, a read-only restricted VACM view, and an exact listener IP.
There is no SNMPv1/v2c mode, community string, write access, wildcard bind, or
trap sender. Configure it in the owner-only HA SOC Settings tab; credentials
remain masked and are stored in HA SOC's private secret store.

The exact OIDs, counter math, scope limitations, validation commands, and
authoritative standards references are in [SNMPv3 monitoring export](docs/SNMPV3.md).

The design exists to answer one question safely: change which ports are
reachable from where without risking a lockout.

**The firewall is owner-only in its entirety**, `firewall/status`
included, whatever `access_level` says: no other account can attempt a
takeover or a change that ends with the platform unreachable. A
non-owner admin sees a one-line "owner only" note where the card would
be. The same reasoning (recorded decision D-23) makes
`entity_remap/apply` and sidebar policy pushes owner-only outright, and
makes deactivating, deleting, or revoking the sessions of an
admin-group account owner-only, while admins keep routine management of
non-admin users.

- Every rule this project ever applies lives in one dedicated iptables
  chain (`HA_SOC_RULES`) the add-on owns outright, plus exactly one jump
  rule the add-on maintains at position 1 of `INPUT` into that chain; it
  sits first because a deny that lands below an accept is not a deny.
  Nothing Docker manages and no pre-existing rule is ever touched.
  Rules are **dual-stack by default**: each rule carries a family (`4`,
  `6`, or `both`), a source address pins the family to its own and a
  contradicting explicit value is rejected, and the add-on mirrors the
  chain into `ip6tables` with the same jump. Before every apply the
  add-on takes checked backups per family (a full-table save for manual
  recovery plus the chain-only snapshot it actually reverts from); if
  any backup fails, nothing is applied, and a failure in either table
  restores both. A revert flushes and replays only the `HA_SOC_RULES`
  chains, never a whole table. On a host without `ip6tables` the card
  says "IPv6 rules not applied" and marks every dual-stack rule
  partially applied, computed at read time so history is never
  rewritten; a silent IPv4-only success does not exist.
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
  still fine." The countdown the panel shows re-anchors the moment the
  add-on actually applies the rules, so it tracks the add-on's real
  local revert timer instead of running up to one poll interval ahead.
- A deliberate stop of the add-on reverts an unresolved test immediately
  (the service's `finish` script runs the same recovery). A host reboot
  with the add-on disabled leaves the pre-test ruleset only if the timer
  or `finish` ran; otherwise the next start reverts it. If the add-on
  goes silent mid-test, nothing ever unblocks automatically: the owner,
  and only the owner, can discard the unreported test once its window
  has lapsed, which archives it as `discarded_unreported` and is
  audit-logged.
- Uninstalling the add-on is best-effort cleanup: no Supervisor
  uninstall hook is verified to exist, so an empty `HA_SOC_RULES` chain
  and its one `INPUT` jump can remain. Manual removal is
  `iptables -D INPUT -j HA_SOC_RULES` followed by
  `iptables -X HA_SOC_RULES`.
- Core only ever proposes and displays; the add-on is the only thing that
  actually touches iptables, and its own report is always the final word
  on what's really active.

See [`custom_components/ha_soc/firewall.py`](custom_components/ha_soc/firewall.py)'s
module docstring for the full state machine and
[`ha_soc_probe/DOCS.md`](ha_soc_probe/DOCS.md)'s "Firewall rules" section
for the add-on side of the same design.

## Network tab (UniFi Network / Protect)

The **Network** tab talks directly to a UniFi console over your LAN with a
**local API key** (Local Site → Settings → Integrations),
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
  applicable to infrastructure). Each device is enriched from the documented
  `/devices/{id}` detail and `/devices/{id}/statistics/latest` endpoints.

**Firewall Policies**, **ACL Rules — Security Audit**, the HA server's own
port coverage, and the Pi-hole DNS section live on their own tab — see
[Network Security tab](#network-security-tab) below.

**UniFi Protect** gets two tables of its own:

- **Devices** — name, IP, MAC, recording state, last ring, and channels.
  Each device name deep-links to that camera on the Protect console
  (`https://<host>/protect/dashboard/devices/<id>`), built from the device
  `id` the API returns.
- **Events & AI Smart Detections** — recent in-memory event type, smart-detection
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

> **Contract and field caveat.** The calls and response schemas were verified
> against Ubiquiti's versioned Network 10.4.57 and Protect 7.2.105 OpenAPI and
> Postman artifacts, but not against this installation's live controller. See
> [`docs/UNIFI-LOCAL-API-CONTRACT.md`](docs/UNIFI-LOCAL-API-CONTRACT.md). Thus
> [`unifi.py`](custom_components/ha_soc/unifi.py) resolves every field from a
> list of candidate names spanning the Integration API (camelCase) and the
> legacy controller API (snake_case), and anything a given controller
> doesn't return renders as `—` rather than being guessed. Fields most
> likely to need confirmation against live data (VLAN, IPv6, the
> client→SSID reference key, bandwidth, the WAN-port stats, the ACL/firewall
> rule fields, device `firmwareUpdatable`, and — on the Protect side —
> `isRecording`, `channels`, and the
> license-plate location) are marked `# VERIFY` in that module. If a column
> reads `—` for you, that field name is the thing to confirm against your
> console's API response. Protect 7.2.105 events are delivered through
> `/subscribe/events`, not a historical REST list; HA SOC uses Home Assistant's
> loaded Protect integration for its recent event buffer or shows a limitation.

## Network Security tab

The **Network Security** tab is the security-audit surface for your UniFi
Firewall Policies and ACL rules, the Home Assistant server's own exposure,
and Pi-hole's DNS-level view of the IoT network — all read-only, all
advisory. Nothing on this tab ever edits a UniFi rule or policy, toggles
Pi-hole blocking, or reassigns a Pi-hole client to a group.

**Firewall Policies and ACL Rules are two genuinely separate UniFi
resources, not two names for the same feature.** This was confirmed against
a live controller: its ACL Rules endpoint responded with zero rules
(`{"count":0,"data":[]}`) while its actual allow/deny configuration lived
entirely under Firewall Policies — the zone-based mechanism current UniFi
Network firmware shows by default under **Settings → Security → Create
Policy**. A controller can have rules under either, both, or neither, so
this tab reads and audits both independently.

**Firewall Policies — Security Audit.** Every policy the controller
exposes, **in evaluation order**, with:

- **Action** (allow/block/reject), **Source zone → Destination zone**,
  **Protocol**, **Ports**, **Enabled** state.
- Each row's name cell shows any additional narrowing beyond the zone pair
  — networks, IP/subnet, MAC, domains, or application/category counts —
  when the controller reported one.
- A port list scoped to a saved **Traffic Matching List** is shown as such
  rather than as fabricated port numbers, since this project doesn't
  resolve that list's contents.
- The same **custom** badge and "N custom / M total" count as ACL Rules
  below, driven by the same `metadata.origin` field.

A **Matrix / Table** toggle at the top of the card switches between the
full sortable table above and a zone × zone grid — one cell per source/
destination zone pair, colored by what's actually present there (all
allow, all block/reject, a mix of both, or nothing) rather than by which
policy "wins": UniFi evaluates policies in order with an implicit-deny
fallback, and this project hasn't verified that evaluation closely enough
to claim a winner, so "mixed" only means read the filtered table to see
which policy actually governs. Clicking a cell switches back to Table
view filtered to that one zone pair; a zone whose name no longer matches
any policy (deleted after the policy list was last fetched) simply has
nothing in its row/column rather than causing an error. Matching is by
zone **name**, not id — the normalized policy rows don't carry the raw
`zoneId`, only the name UniFi's own API already resolved it to (see
`buildZoneMatrix` in
[`firewall-matrix.ts`](custom_components/ha_soc/frontend/src/firewall-matrix.ts)).

This reads the confirmed real endpoints `GET /sites/{siteId}/firewall/zones`
and `GET /sites/{siteId}/firewall/policies`, whose schema (`action` as a
typed ALLOW/BLOCK/REJECT object, `ipProtocolScope`, `source`/`destination`
each with a required `zoneId` and an optional typed `trafficFilter` —
NETWORK/IP_ADDRESS/MAC_ADDRESS/PORT modeled field-for-field; REGION/
VPN_SERVER/SITE_TO_SITE_VPN_TUNNEL/IPV6_IID shown by type only) was
extracted directly from Ubiquiti's own published OpenAPI spec for this
controller version and parsed programmatically — not summarized secondhand
— since `developer.ui.com` itself isn't reachable from every environment
this project has been built in. See the "Firewall Policies" section of
[`unifi.py`](custom_components/ha_soc/unifi.py) for the full verified shape
and what's still marked `# VERIFY`.

**ACL Rules — Security Audit.** Every ACL rule the controller exposes, **in
evaluation order**, with:

- **Action** (allow/block), **Protocols** (TCP/UDP — the only two an IPV4
  ACL rule can filter by), **Enabled** state.
- **Networks** — every network the rule touches, resolved to names. A
  MAC-type rule's network comes from its own `networkIdFilter`; an IPV4
  rule's comes from whichever of its source/destination filters is
  NETWORKS-scoped.
- **Ports** — the destination and source port lists the controller actually
  configured, combined and deduplicated for the table; each row's name cell
  also shows the raw source/destination IP-or-subnet and MAC detail when the
  controller reported it.
- A **custom** badge next to the name, plus a "N custom / M total" count in
  the card header, for every rule whose `metadata.origin` is
  `USER_DEFINED` — i.e. a rule you created yourself, distinct from one
  UniFi ships by default.

This reads the real ACL Rule schema — a `type` (`IPV4` or `MAC`)
discriminator, `action`, and (IPV4 only) a top-level `protocolFilter`, with
`sourceFilter`/`destinationFilter` each independently discriminated into
`IP_ADDRESSES_OR_SUBNETS` (+ port), `NETWORKS` (+ port), or `PORTS`-only
for IPV4 rules, and `MAC_ADDRESSES` for MAC rules — verified directly
against a live controller's own OpenAPI spec (the account owner uploaded
`network_v10.4.57`'s spec straight from their console), which superseded
and corrected an earlier build of this module based on a third-party
extraction of a different controller version that turned out to model this
resource incorrectly. It's still marked `# VERIFY` in
[`unifi.py`](custom_components/ha_soc/unifi.py) wherever a live controller
could confirm it further — the same honesty posture as the Network tab's own
field-mapping caveat above. If the controller's ACL endpoint doesn't
respond, the report says so (and lists what it tried) rather than showing a
fabricated ruleset.

**Source/Destination device tie-in.** Every IP, subnet, or MAC address a
rule or policy's name cell shows is also matched, client-side, against the
Network tab's own Clients table (the same client list `network_security.py`
already exposes as part of the overview): an IPv4 address or CIDR that
contains a known client's address, or a MAC that matches one exactly,
renders as a clickable chip carrying that client's display name instead of
a bare address. Clicking it switches to the Network tab and filters its
Clients table down to that device. This is a display convenience only — it
never changes what the rule itself actually matches, and a miss (no chip,
just the raw address) means no current client's IP/MAC falls inside that
rule's filter, not that the address is unrecognized or unsafe. IPv6 subnet
containment isn't implemented, only an exact IPv6 address can match; see
`matchClientsForEntries` in
[`device-match.ts`](custom_components/ha_soc/frontend/src/device-match.ts).

> **What this API surface does not expose.** The same uploaded spec confirms
> this controller's entire public Integration API surface — every path it
> serves — includes only `acl-rules` and `firewall/policies`+`firewall/zones`
> as rule-like resources; there is no endpoint for UniFi's older, pre-zone
> "Firewall Rules" screen (the classic WAN_IN/WAN_OUT/LAN_IN/LAN_OUT/DMZ
> ruleset some UniFi OS versions still show in the UI). A rule created
> through that legacy screen cannot be read by this integration, or by any
> integration using this API — it isn't a gap in this project's code, it's
> a gap in what Ubiquiti's public API exposes on this firmware.

**Home Assistant Server Ports.** The optional [HA SOC Probe](#optional-ha-soc-probe-add-on)
add-on already reports the server's real listening TCP/UDP ports and their
bind addresses; this table cross-references each one against **both** the
Firewall Policies and ACL rules above (`correlate_server_ports_with_rules`
in [`unifi.py`](custom_components/ha_soc/unifi.py)) and labels it, with each
covering rule prefixed `ACL:` or `Policy:` so you know which UI to go edit:

- **Covered** — an enabled rule/policy's destination names this server's
  IP/subnet and (has no port restriction, or explicitly includes this port).
- **Network-scoped** — a rule/policy covers it by network/zone rather than
  by IP; this project has no verified way to confirm the server's own
  network membership from the Integration API, so this is reported
  separately rather than folded into "covered".
- **Uncovered** — no enabled rule or policy of either kind names this
  server by IP/subnet at all for that port. This does **not** by itself
  mean the port is reachable from every network — UniFi's own default zone
  policy still applies — only that nothing enumerates who may reach it.

**Pi-hole DNS.** Configure a Pi-hole v6 host and its **app password**
(Pi-hole → Settings → API → App password) in Settings, plus the **IoT
network CIDR** — the subnet whose DNS your UniFi gateway forwards to
Pi-hole. HA SOC logs in over the LAN for one snapshot at a time (session id
on `X-FTL-SID`, logged out again immediately after — never a long-lived
credential in memory) and shows blocking on/off, the query/blocked totals,
whether that IoT subnet has its own dedicated Pi-hole client group (versus
every device on it falling through to the global Default group), and a
short sample of top blocked domains and recently blocked queries — the
"what is my IoT/TV traffic actually trying to phone home to" view. Core Home
Assistant's own `pi_hole` integration only exposes an on/off switch and a
few coarse sensors; it has no query log, group, or client-scoping surface,
so this is a real direct API client (see
[`pihole.py`](custom_components/ha_soc/pihole.py)), not an enrichment layer.
Its auth flow and endpoint shapes were verified against pi-hole/FTL's own
published OpenAPI spec (the same one served locally at
`http://pi.hole/api/docs`) rather than guessed, since that host is only
reachable on your own LAN.

**Suggestions.** A short advisory findings list combines all four sources —
today: an ACL rule with no source/destination scoping at all (allows from
anywhere to anywhere), a Firewall Policy that allows an entire zone-to-zone
path with no traffic filter narrowing it, a server port no enabled rule or
policy names, neither ACL Rules nor Firewall Policies having anything
configured (a single combined nudge — an install using only one of the two
mechanisms is not missing anything just because the other is empty),
Pi-hole blocking disabled, no IoT CIDR configured yet, and an IoT subnet
without its own Pi-hole client group. Each finding fires only when the
underlying data actually supports the specific claim — none of them guess
at which UniFi network is "the IoT network" beyond what you've told Pi-hole
explicitly. Findings are recomputed fresh on every refresh rather than
tracked through a dismiss/resolve lifecycle like the Scanner tab's findings:
this is live network/DNS configuration that can change from one refresh to
the next (a rule or policy edited in the UniFi app, blocking toggled from
Pi-hole's own UI), and a persisted status here could go stale silently.

## Customize (per-tab layout)

A **Customize** button in the panel's top-right header (hidden on the
Settings tab, whose cards are a config form rather than browsable
resources) puts every other tab into an edit mode: each card/table gets a
drag handle plus up/down buttons for reordering, and a show/hide toggle
for the ones marked hideable. A tab's one primary resource — the
Permissions Matrix, the Audit Log, Entity ReMap's own remap card, and a
few others — stays pinned and un-hideable, since hiding it would leave the
tab with nothing to look at. Leaving edit mode switches every view
straight back to full, unfiltered content; nothing about which cards
render is ever driven by edit mode itself, only by what's saved.

Layout is stored **per Home Assistant account**, scoped by the caller's
own `user_id` (`ha_soc/layout/get` and `ha_soc/layout/set` in
[`websocket_api.py`](custom_components/ha_soc/websocket_api.py), backed by
`panel_layout` in the store) — any user with SOC panel access manages
their own arrangement, gated the same as any other read/write of the
caller's own preferences (`@require_soc_access`, not owner-only), and can
never read or write another user's layout. A user's saved layout is purged
along with the rest of their data on `async_purge_user`. A failed load
falls back to each view's own declared default order with nothing hidden
— a transient WebSocket error never locks a view into a blank or
scrambled state, it just ignores the saved arrangement for that session.
Saves are fire-and-forget: a rearrangement applies immediately in the UI
regardless of whether the save behind it succeeds, so the worst case of a
failed save is that it doesn't survive a refresh, not that the click
appears to do nothing.

The framework is intentionally generic — every card-based view extends a
shared `HaSocCustomizableView` base class
([`customizable-view.ts`](custom_components/ha_soc/frontend/src/customizable-view.ts))
that declares its cards as an ordered `LayoutSection[]`
([`customize.ts`](custom_components/ha_soc/frontend/src/customize.ts)), so
adding Customize support to a future tab means wrapping its existing
render output in that array, not writing per-view reorder logic.

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
