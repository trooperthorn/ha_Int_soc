# Threat Model

## Scope and assets

Assets are Home Assistant accounts/tokens, HA SOC configuration and secrets,
UniFi/Pi-hole API keys and telemetry, Protect metadata, the host/probe Docker
boundary, audit-chain evidence, and availability of automations/security
monitoring. Trust boundaries are: browser to HA WebSocket; HA core/shared
integration process; HA to local controller APIs; HA to probe/Docker; HA to
NVD/GitHub; and HA to the SIEM.

## Principal threats and controls

| Threat | Impact | Implemented controls | Residual action |
|---|---|---|---|
| Non-owner admin changes an owner/admin target | privilege loss/takeover | server-side target classification; owner-only gates; owner deactivation refusal | retain regression tests and owner MFA |
| API key exfiltration by redirect/log/error | controller compromise | secret store, redaction, masked representation, redirects disabled, bounded errors | verified TLS and key rotation |
| Undocumented/private UniFi calls drift | false data or unexpected mutation | versioned read-only Local API contract tests | re-verify on controller upgrade |
| Malicious probe resource JSON reaches shell/Docker | command/option injection or host DoS | strict jq schema/slug/ranges, last-known-good state, canonical Docker JSON | isolate add-on, review Docker privilege |
| Audit deletion, rollback, queue exhaustion, or SIEM outage | evidence loss | hash chain, mirrored head, Repairs issue, local-first flush, bounded queue, retry/status/gap detection | SIEM alerts, retention, evidence export, capacity test |
| HTTP/plaintext Syslog or unverified certificates | interception/tampering | visible findings/warnings; no forced migration | complete certificate plan and segmentation |
| Malicious integration in shared HA process | secret/data theft | advisory static scanner and provenance findings | allowlist/review code; isolate high-risk workloads |
| Dependency or CI compromise | shipped vulnerable code | lockfile, pinned Actions, CodeQL, npm audit, Bandit, ShellCheck, Dependabot, owner review | enable vulnerability alerts; add signed releases/SBOM/provenance |
| Availability attack or response amplification | HA/SIEM degradation | time/body/fan-out/queue bounds, cancellation-safe lifecycle, rate-conscious polling | load/failure drills and monitoring |

## Assumptions

The HA owner account and host OS/Supervisor are trusted, local DNS/routing are
administratively controlled, controller API keys are scoped read-only where
the platform permits, and clocks are synchronized. Compromise of HA core or
the host defeats most integration-level controls.

Review this model for every new data source, write operation, network listener,
credential, or trust-boundary change and at least annually.
