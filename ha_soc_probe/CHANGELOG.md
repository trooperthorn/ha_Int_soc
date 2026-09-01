# Changelog

## Unreleased

- SIEM export: operators can retain the default RFC 5424 JSON wire format,
  select standards-based CEF 0 inside RFC 5424 for SolarWinds SEM and other
  CEF receivers, or select raw canonical JSON. UDP remains one event per
  datagram; TCP and TLS retain RFC 6587 octet counting, bounded queueing,
  retries, delivery status, and TLS verification.
- Release integrity: the integration, Probe add-on, and Probe scanner are
  synchronized at `2026.09.01.2`; a repository test and the tag-release gate
  now reject version drift across any of those identifiers. The synthetic
  hard-coded-credential regression fixture is assembled at runtime so GitHub
  secret scanning no longer mistakes test data for a live Google API key.
- Security CI: CodeQL now analyzes Python and JavaScript/TypeScript and uploads
  results to GitHub code scanning alongside Bandit, npm audit, and ShellCheck.
- Panel redesign: the dashboard now opens with a compact security command
  overview and prioritized action counts, replaces the repeated donut charts
  with comparable bars and summary metrics, limits initial investigation
  queues to ten rows, and uses a quieter, sticky application navigation.
- CodeQL follow-up: credential migration logs now expose only a count, never
  credential key names, with a regression assertion covering both names and
  values. A synthetic YAML-reference test fixture no longer uses a
  secret-classified variable name that caused a test-only storage alert.

Everything from the 2026-08-30 security review's sprints 0, 1, and 2
(this section becomes the next version when it is cut; the sprints
landed after v2026.08.30.2 shipped, which is why they are not in that
entry):

- Security (sprint 0): Home Assistant accepts this add-on's two
  callback services only from the Supervisor's own user context; the
  shared secret becomes defense in depth behind that check, a call
  presenting no secret is always rejected, and rejected calls are
  audited and raised as HIGH detections. On Core and Container installs
  the services no longer exist at all.
- Firewall (sprint 0): only one test can exist at a time, end to end.
  The firewall service refuses to apply a new test while a previous one
  is still armed, clears a timer-resolved test's state file before
  reporting so a reverted test cannot wedge the channel, and Home
  Assistant refuses new proposals until this add-on has reported the
  previous test's fate.
- Firewall safety (sprint 2): applies take two checked backups (full
  table for manual recovery, chain-only snapshot for reverts) and
  refuse to apply if either fails; reverts flush and replay only the
  `HA_SOC_RULES` chain, never the whole table; the service's `finish`
  script reverts an unresolved test on a deliberate stop; and every cap
  slug from HA SOC is re-validated locally before it can reach a Docker
  API path.
- The pairing secret file in `/data` is created 0600 and an existing
  file is tightened at startup; the first live Supervisor verification
  run found it at 0644 (exposure bounded by the add-on's private
  volume, but 0600 matches what a credential file deserves).
- On the Home Assistant side of the same sprints: the firewall is
  owner-only in its entirety with an owner-only, audited discard for a
  test the add-on never reported; the panel countdown re-anchors to the
  moment this add-on actually applies; admin-account lifecycle actions,
  entity remap applies, and sidebar pushes are owner-only per the
  recorded D-23 decision; every HA SOC credential moved into a
  dedicated private secret store with fetch-at-use callers, extraction
  pattern detection, and expanded audit capture; and CI now gates every
  push and release on the test suite and a bundle-drift check.
- Docs: the privilege ledger in DOCS.md (the add-on's Supervisor
  security rating is 1 by deliberate choice), and the verified-facts
  section recording the two live Supervisor verification runs of
  2026-08-30, including that this add-on and the host both use the
  nf_tables backend and that the host is IPv6-capable, which unblocks
  the dual-stack firewall work.
- Dual-stack firewall (work plan 2.4, decision D-3): rules carry a
  family (4, 6, or both; a source address pins it), the HA_SOC_RULES
  chain and its INPUT jump exist in iptables and ip6tables alike,
  backups and chain snapshots are taken and checked per family, applies
  are atomic across families with both tables restored on any failure,
  and a host without ip6tables is reported honestly instead of
  succeeding IPv4-only in silence.
- Hardening (work plan 2.5): a custom AppArmor profile in enforce mode
  (pending live-load verification, stated in its header); the
  port-scanner service runs as the unprivileged nobody account; the
  base image is pinned by digest; every rule field, window bound, and
  test id from Home Assistant is re-validated locally before any
  iptables or Docker call; failure reasons now reach Home Assistant in
  the report instead of living only in this log; and a deliberate stop
  or update exits cleanly instead of logging a spurious restart
  warning. Recorded answer on image signing: Cosign via the official
  builder applies only to pre-built published images, so signed: false
  remains structurally accurate for this locally built add-on.

## v2026.08.30.2

- No functional add-on change. Version bump keeping the add-on in
  lockstep with the HA SOC integration release (audit capture
  expansion, UniFi in-memory enrichment, app/add-on log viewing,
  sortable tables).
- Versioning standardized: `vYYYY.MM.DD.V` is now the canonical form
  everywhere a person reads a version (git tags, GitHub Releases, HACS,
  changelog headers like the ones in this file, the panel footer). The
  machine-read `version:` field in `config.yaml` stays bare because the
  Supervisor and the release workflow compare it with the prefix
  stripped. See the repository README's Versioning section.

## v2026.08.30.1

- New optional feature: per-add-on resource hard caps. When the HA SOC
  Resource Watchdog proposes CPU/memory limits, the firewall poll cycle
  now carries them and the add-on applies real Docker `--cpus` /
  `--memory` limits through the Docker socket (`docker_api: true` is new
  in this release). With Protection Mode ON, the default, the socket is
  read-only and every application honestly reports "denied": actually
  applying caps requires deliberately disabling Protection Mode on this
  add-on, which the HA SOC panel spells out as the root-equivalent grant
  it is before anything is applied. Installs that never use hard caps
  lose nothing by leaving Protection Mode on.
- Limits are re-asserted periodically (every 12th poll) because a
  container recreated by an add-on update silently loses its caps.
- This version supersedes the deleted 2026.08.29.x tags; their changes
  (blocking-I/O fix, watchdog groundwork) ship here.

## v2026.08.23.4

- Security: both add-on services now send a per-install secret (generated
  once and stored in the add-on's own `/data`) on every call into Home
  Assistant. HA SOC pins the first secret it sees and rejects any later
  ingest/poll call that can't present it, so a forged local service call
  can no longer spoof a port report or a firewall test outcome. No key
  management for you — the secret is created and shared between the two
  services automatically.
- Firewall: a rule that fails to apply now aborts the whole apply and
  restores the pre-test ruleset immediately (rather than leaving a
  partially-applied set live), and the failure is reported back to HA SOC.
- Hardening notes added to the port-scanner service documenting the
  recommended non-root privilege drop (left un-applied pending validation
  against a real Supervisor) and a base-image digest pin.

## v2026.08.23.3

- Added: optional host firewall read/write, gated behind a new `NET_ADMIN`
  capability this add-on now requests in `config.yaml` (a documented -1 on
  the Supervisor security rating — see the HA SOC integration's README).
  A new, second background service polls HA SOC every ~5s for a proposed
  ruleset, applies it to a dedicated `HA_SOC_RULES` iptables chain this
  add-on owns outright (never the raw `INPUT` chain, never anything Docker
  itself manages), and arms a fully local, self-contained revert timer the
  moment it applies anything — a plain backgrounded `sleep` in this same
  process, not a callback that depends on the network path it just changed
  still working. A ruleset backup (`iptables-save`) is taken before every
  apply; an unconfirmed test is restored automatically once its window
  elapses, and if this add-on itself crashes or restarts mid-test, the
  next startup finds the unresolved test and restores it immediately
  rather than trusting a timer that died with the old process.
- Changed: `iptables` and `iproute2` are now installed in the add-on image
  (previously `iproute2`'s presence was merely assumed).

## v2026.08.23.2

- Added: each reported open port now includes its bind address (e.g.
  `192.168.10.5`, or `0.0.0.0` for "every interface") and, for an IPv4
  address, a best-effort match against the host's real network interfaces
  (`eth0.10`, etc.) — real, not guessed, since this add-on already shares
  the host's network namespace. Meant for installs segmenting VLANs: a
  service listening on `(all interfaces)` is reachable from every VLAN,
  not just the one it's meant for. IPv6 bind addresses are reported as
  `null` rather than risk decoding them incorrectly — see run.sh's
  comments for why.

## v2026.08.23.1

- Changed: version numbering switched from pre-1.0 semver (`0.1.x`) to
  calendar versioning, `YYYY.MM.DD.V` — the release date plus a same-day
  revision counter starting at 1 (e.g. the first release on August 23,
  2026 is `2026.08.23.1`; a second release that same day would be
  `2026.08.23.2`). Matches the HA SOC integration's own version scheme so
  the add-on and the integration it reports to always carry a directly
  comparable, unambiguous release identifier — no more guessing whether
  `0.1.1` is newer or older than whatever the integration itself is on.

## 0.1.1

- Fixed: a rejected report (commonly a few seconds/minutes of HTTP 400
  right after Home Assistant Core itself restarts, while the HA SOC
  integration is still loading) no longer waits out the full
  `scan_interval_hours` (up to 24h) before trying again. It now holds in a
  short, capped-exponential retry loop (30s up to 5min) instead, and logs
  a clear, repeating "Holding — ..." warning while it does — so a
  half-connected setup is visible in the add-on's own log rather than
  just going quiet for hours. The HA SOC integration also now raises a
  Repairs issue if the add-on stays installed and running without ever
  successfully reporting for more than 30 minutes.

## 0.1.0

- Initial release. Reports the host's real listening TCP ports to the
  HA SOC integration on a configurable interval. Port + protocol only —
  no process-name attribution (see DOCS.md for why).
