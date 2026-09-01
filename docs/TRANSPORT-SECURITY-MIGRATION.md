# Transport Security Migration

## Current accepted state

The current Home Assistant console is intentionally reachable at
`http://192.168.30.3:8123`, and local applications presently use self-signed
certificates. This change does not break that deployment: HTTP remains
supported, UniFi/Pi-hole verification defaults are unchanged, and Syslog is
disabled until an owner configures it.

This state does not satisfy a strong interpretation of NIST SC-8/SC-23 or
SOC 2 logical/communications-control expectations. Credentials, tokens, logs,
and security telemetry can be exposed to a device able to observe or alter the
local path. Network isolation is compensating risk reduction, not encryption.

Certificate deployment is deferred by owner decision as of 2026-09-01 while
the AD CS hierarchy and certificate templates are researched as security
controls rather than treated as a connectivity exercise. See
`PKI-CERTIFICATE-TEMPLATE-SECURITY-RESEARCH.md`. This deferral does not close or
suppress the HTTP, self-signed-certificate, or plaintext-Syslog findings.

## Migration sequence

1. Inventory every origin, hostname, certificate subject/SAN, trust store,
   reverse proxy, API client, and SIEM receiver. Back up HA and controllers.
2. Give each service a stable internal DNS name. Issue certificates from a
   managed internal CA or a publicly trusted ACME flow as appropriate.
3. Install the issuing CA on clients and enable certificate verification for
   UniFi Network, Protect, Pi-hole, and Syslog TLS. Test hostname validation.
4. Put Home Assistant behind a correctly scoped TLS reverse proxy or configure
   supported HA TLS. Restrict `trusted_proxies` to exact proxy addresses and
   set the external/internal URLs to HTTPS after validation.
5. Redirect/deny cleartext management access only after every client and
   recovery path has been tested. Retain an isolated break-glass procedure.
6. Capture evidence: certificates/expiry, allowed ciphers/protocols, firewall
   rules, verification settings, failed cleartext tests, and quarterly review.

## Syslog modes

- TLS: preferred; RFC 5424 messages with RFC 6587 octet-counting framing.
  Verification defaults on. Turning it off is a labeled self-signed
  compatibility mode and should be time-bounded.
- TCP: plaintext fallback with reliable stream ordering but no confidentiality,
  peer authentication, or cryptographic integrity.
- UDP: broadest compatibility and lowest assurance. Delivery is best effort;
  `sent` means accepted by the local network stack, not acknowledged by SIEM.

Payload is selected independently from transport:

- RFC 5424 + Raw audit JSON: backward-compatible default. The complete
  canonical audit record is the RFC 5424 message body.
- RFC 5424 + CEF 0: the RFC 5424 body starts with
  `CEF:0|Home Assistant|HA SOC|...`; fixed CEF fields duplicate the audit
  sequence and chain hashes for SIEM connectors that ignore RFC 5424
  structured data.
- Bare Raw JSON: compatibility mode for collectors that explicitly require a
  JSON-only payload. It has no RFC 5424 envelope; TCP/TLS still retain bounded
  RFC 6587 octet-count framing.

All formats include HA SOC audit `seq`, `prev_hash`, and `hash`. In the two RFC
5424 formats, the structured-data header also carries `seq`, `hash`, and
`category`. The receiver should alert on sequence gaps, chain failures,
exporter drops/errors, and a disabled exporter. The local tamper-evident JSONL
remains the system of record.

SolarWinds SEM receipt and normalization are separate acceptance checks. Use a
dedicated `local0`-`local7` facility, confirm raw receipt first, and then verify
that the selected SEM connector maps event ID, name, severity, source, user,
and chain fields into normalized events. A standards-valid CEF message does not
by itself establish that a product-specific SEM connector supports HA SOC.
