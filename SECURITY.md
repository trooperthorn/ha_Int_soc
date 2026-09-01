# Security Policy

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private
addresses, or logs. Use GitHub's private vulnerability-reporting feature for
this repository. If private reporting is unavailable, open a minimal issue
asking the maintainer to establish a private channel; omit technical details.

Include the affected version/commit, prerequisites, impact, a minimal
reproduction, and suggested remediation. Remove tokens, API keys, cookies,
camera images, usernames, and private network details.

## Response targets

These are project targets, not an SLA: acknowledge critical/high reports in
three business days, establish severity and containment in seven, and publish
a coordinated fix/advisory as soon as safely validated. Lower-severity issues
are prioritized by exploitability and impact.

## Supported version

Only the latest published release and the default branch receive security
fixes. Operators should update Home Assistant, UniFi OS applications, Pi-hole,
and HA SOC promptly and retain a tested rollback/backup.

## Security boundaries

HA SOC is a privileged Home Assistant integration, not a sandbox or an
independent compliance product. It cannot prevent a malicious integration in
the same Python process from reading shared memory or files. Its findings and
control mappings are evidence inputs; they are not a certification or a claim
that no vulnerability exists.

