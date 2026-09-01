# NIST SP 800-53 and SOC 2 Support Matrix

This is an engineering crosswalk, not a certification, attestation, or claim of
complete implementation. NIST describes SP 800-53 as a flexible organizational
control catalog, and SP 800-53A supplies customizable assessment procedures.
SOC 2 evaluates the controls of an in-scope service organization; software can
produce evidence but cannot replace governance, people, policy, or an auditor.

References: [NIST SP 800-53 Release 5.2.0](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final),
[NIST SP 800-53A Release 5.2.0](https://csrc.nist.gov/pubs/sp/800/53/a/r5/final),
[NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final), and the
[AICPA Trust Services Criteria](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022).

| Capability/evidence | NIST control support | SOC 2 criteria support | State and remaining work |
|---|---|---|---|
| Owner/admin authorization, least privilege, token/session actions | AC-2, AC-3, AC-5, AC-6, IA-2, IA-5 | CC6.1-CC6.3 | Implemented; org must review access and MFA evidence periodically |
| Hash-chained audit with actor/category/time, retention and local-first flush | AU-2-AU-6, AU-8, AU-9, AU-11, AU-12 | CC2.2, CC4.1, CC7.2-CC7.4 | Implemented; protect backups and test restoration/chain verification |
| Selectable RFC 5424 JSON, RFC 5424 CEF 0, or bare JSON SIEM export over TLS/TCP/UDP; queue/drop/format status | AU-3-AU-6, AU-9, AU-12; SC-8, SC-23 | CC6.6, CC7.2-CC7.4 | Implemented, disabled by default; configure receiver/connector alerts, validate normalized fields, and prefer verified TLS |
| Integration/device/security health, CVE and detection views | CA-7, RA-3, RA-5, SI-2, SI-4 | CC3.2, CC4.1, CC7.1 | Partial; define owners, SLAs, triage and closure evidence |
| Config change audit, safe defaults, versioned store | CM-2, CM-3, CM-5, CM-6, CM-8 | CC8.1 | Protected main branch has strict checks and checks-only auto-merge; monthly repository evidence captures observable policy and CI state; deployment records remain operational evidence |
| API limits, redirect refusal, validation, secret redaction | SC-7, SC-8, SC-23, SI-10, SI-11 | CC6.6, CC6.7, CC7.1 | Implemented at app boundary; verified TLS migration remains |
| Tests, CodeQL, dependency/static scans, pinned CI actions, disclosure policy | SA-11, SI-2, SI-7, SR-3, SR-4, SR-5, SR-6 | CC8.1, CC9.1, CC9.2 | Automated; strict merge gates, immutable future releases, SHA-256 assets, SPDX SBOM, build provenance, and monthly attested repository evidence are implemented; human risk acceptance remains organizational |
| Threat model and incident-oriented detections | RA-3, IR-4-IR-6, IR-8 | CC3.2, CC7.3-CC7.5 | Documented; org must exercise and retain incident evidence |
| Backup/recovery and operational availability findings | CP-2, CP-4, CP-9, CP-10, SI-13 | A1.1-A1.3, CC7.4 | Advisory/partial; perform restore and failover tests |

## Priority path to meet and exceed the targets

1. Finish verified TLS for HA, every controller, and Syslog; segment management
   networks and deny cleartext after validation.
2. Maintain the protected checks-only merge gate, pinned workflow actions,
   immutable releases, SHA-256 assets, SPDX SBOM, provenance, and monthly
   evidence collection; investigate any partial-pack workflow failure.
3. Define control owners, system boundary/data classification, risk register,
   access-review cadence, vulnerability/patch SLAs, incident response, backup
   recovery objectives, vendor review, and exception expiry.
4. Extend the automated repository evidence with a signed runtime pack:
   user/MFA/access state, audit-chain
   verification, detections/findings and disposition, retention/export status,
   backup/restore test, CI/release attestations, and exception register.
5. Run quarterly control tests using SP 800-53A examine/interview/test methods;
   track samples, deviations, remediation, retest, approver, and expiry.
6. Commission an independent penetration test after deploying a staging copy
   and again after material trust-boundary changes. A clean scan never proves
   that no security issue exists.
