# Compliance Evidence Plan

| Evidence | Source | Cadence | Required review |
|---|---|---|---|
| User/admin/owner inventory, MFA, active tokens | HA SOC Users export/screenshot | monthly and termination | owner signs exceptions |
| Audit-chain verification, head, first/last seq, gaps | local JSONL plus SIEM | daily automated; monthly sample | alert on any reset/gap/drop |
| Syslog mode, TLS verification, receiver health, sent/dropped/error | HA SOC Settings and SIEM | continuous/monthly | plaintext exception has owner and expiry |
| Open findings/detections, age, disposition | HA SOC dashboards | weekly | severity-based remediation SLA |
| UniFi/Pi-hole/HA versions and API contract | inventory and versioned specs | each upgrade/monthly | re-run contract/regression suite |
| CI test/validation/security results and reviewed diff | GitHub Actions/PR | every change | required owner approval |
| Dependency inventory, audit, SBOM/provenance | lockfile and release workflow | every release | block known exploitable findings |
| Backup encryption, age and restore result | backup platform/test record | daily backup; quarterly restore | meet approved RPO/RTO |
| Incident exercise and lessons learned | incident plan/tabletop record | at least annually | actions assigned and retested |
| Certificates, expiry, protocols, verification | PKI/TLS scan | continuous/quarterly | alert before expiry and on trust failure |

Evidence should be written to an access-controlled, append-only or immutable
repository with time synchronization, retention, legal/privacy review, named
control owner, collection method, sampling period, result, exception, approval,
and hash/signature. Do not export raw API keys, tokens, cookies, camera images,
or unnecessary personal data.

Required future product work is a signed evidence-pack generator and receiver-
side chain verifier. Until then, retain HA SOC exports, SIEM records, GitHub
workflow artifacts, configuration snapshots, and reviewer attestations as
separate evidence sources.

