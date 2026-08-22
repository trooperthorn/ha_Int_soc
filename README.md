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
├── websocket_api.py      — the ha_soc/* command surface the panel calls
├── sensor.py / binary_sensor.py / repairs.py — entities + Repairs integration
├── panel.py              — sidebar panel registration
└── frontend/             — Lit + TypeScript panel (dist/ committed)
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

## Planned: optional HA SOC Probe add-on

Action item to pick back up later — not started.

An optional, HAOS-only companion add-on for the one class of check that
genuinely needs a separate container: real socket-level **port scanning**
of the host (what's actually listening, not just what's configured).
Everything else originally floated alongside this idea turned out to
already be reachable from inside the integration itself and does **not**
need an add-on:

- Whether an SSH-capable add-on is installed/exposed, and HA config-check /
  Repairs issues — both readable today via the Supervisor `supervisor/api`
  websocket proxy and `issue_registry`, already available to `health.py`.
  This should just become an extension of `health.py`'s misconfig checks,
  no add-on required.
- Only the add-on itself (working name: `ha_soc_probe`) needs building —
  a small container that periodically probes its own host's open ports and
  calls back into HA over the REST API (`POST /api/services/ha_soc.ingest_probe_result`),
  the same pattern other monitoring add-ons use, so no new communication
  channel is needed on the integration side.
- The integration should detect the add-on's presence via the Supervisor
  add-on list and only show that panel section when it's actually
  installed — Container/Core installs must never look like they silently
  lack data; they should show the section is unavailable, honestly.
