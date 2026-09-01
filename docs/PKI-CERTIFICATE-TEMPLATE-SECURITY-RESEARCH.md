# PKI and Certificate Template Security Research

Status: **deployment deferred by the owner on 2026-09-01**.

The current self-signed certificates and the local Home Assistant HTTP access
remain documented exceptions. This file records a research boundary, not an
authorization to create templates, enroll certificates, change trust stores,
or enable TLS. The intended Microsoft AD CS namespace is
`net.secretsquirrel.club`; no private key, certificate, credential, internal
host inventory, or CA configuration belongs in this repository.

## Questions the later design must answer

1. **Trust architecture:** offline root versus current hierarchy, issuing-CA
   separation, administrative roles, CA audit logs, backup, recovery, and
   cryptographic-agility plan.
2. **Template attack surface:** enrollment and auto-enrollment ACLs, template
   ownership, subject/SAN supply rules, manager approval, authorized
   signatures, enrollment agents, issuance requirements, and known AD CS
   escalation classes (including ESC1 and later published variants).
3. **Identity and purpose:** a separate template or policy for web servers;
   least-privilege EKUs; unique DNS SANs; no wildcard, client-auth, code-signing,
   smart-card, or certificate-request-agent capability unless a documented use
   case requires it.
4. **Private-key custody:** generate the key on the destination when possible;
   prefer non-exportable keys and hardware protection where supported; define
   secure exceptions for appliances that require import; prohibit shared keys.
5. **Algorithms and compatibility:** compare RSA and ECDSA support across Home
   Assistant, UniFi Network, UniFi Protect, Pi-hole, browsers, collectors, and
   SolarWinds before selecting key sizes, curves, signature algorithms, and
   validity periods.
6. **Revocation and lifecycle:** CDP/AIA reachability, CRL/OCSP behavior during
   outages, renewal overlap, expiry alerting, emergency revocation, inventory,
   decommissioning, and evidence retention.
7. **Service deployment:** termination point, internal DNS, certificate chain,
   hostname verification, minimum protocol/cipher policy, rollback, and the
   point at which plaintext HTTP or Syslog is denied rather than merely warned.
8. **Assessment:** export and review CA/template configuration, run an AD CS
   exposure assessment from a controlled administrative host, threat-model the
   results, and test enrollment/revocation in a non-production path first.

## Required outputs before implementation

- approved architecture and data-flow diagram;
- template-by-template configuration and ACL matrix;
- certificate inventory and ownership register;
- compatibility test results for each destination;
- issuance, renewal, revocation, backup, recovery, and incident runbooks;
- documented exception and expiry for any exportable key, broad enrollment
  right, extra EKU, long validity period, wildcard, self-signed certificate, or
  plaintext fallback;
- independent review of the proposed AD CS configuration and a staged rollback
  test.

Until those outputs are reviewed, certificate setup stays deferred and the
transport findings in HA SOC must remain visible.
