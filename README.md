# HA SOC

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
  users-at-risk, vulnerability/detection breakdowns, and a live suspicious-
  activity feed.

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

- MFA can be **audited**, never **enforced** — no such hook exists in Home
  Assistant core.
- Dashboard/view visibility is **cosmetic** — the real access-control
  boundary is a user's admin/non-admin group, nothing finer exists.
- Failed-login telemetry is **IP-only** — Home Assistant never logs an
  attempted username on a failed login, anywhere.
- Every vulnerability/scanner finding is **advisory** — a starting point for
  a human to confirm or dismiss, never an automatic verdict.
- The audit log is **tamper-evident, not tamper-proof** — anyone with the
  filesystem access that reaches `.storage/` can rewrite the hash chain too.
