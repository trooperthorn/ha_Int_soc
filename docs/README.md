# Documentation index

One line per document, stating what it is responsible for, so a reader knows where a fact belongs. Code carries only what a reader needs at the point of reading; every explanation, rationale, protocol fact, and operational note lives in one of these files.

## Core documents

- `design.md`: architecture and rationale by subsystem (audit chain, store and secrets, WebSocket API and access control, detections and risk, scanner and provenance, health and hygiene, network integrations, probe and firewall, frontend, CI and release, tests). Why a thing is built the way it is.
- `protocol.md`: wire and device facts (Supervisor endpoints, WebSocket message shapes, audit chain on-disk format, NVD and GitHub and Pi-hole response shapes, USB and serial facts, the Probe add-on protocol, the external audit ingest contract). What crosses a boundary and in what shape.
- `operations.md`: configuration keys and their consequences, thresholds and defaults, detection threshold table, health check table, the Probe's privilege and option table, runtime knobs, troubleshooting, release and CI operations.
- `security.md`: trust boundaries, enforced versus cosmetic controls, secret handling, redaction rules, audit chain integrity reasoning, detection false positives, scanner rule false positives and evasion.
- `decisions.md`: dated decisions, each with the alternative rejected and why.
- `backlog.md`: dated open items moved out of code (VERIFY markers and deferred work).

## Contracts owned by dedicated documents

- `CEF-SCHEMA.md`: the CEF 0 payload format for syslog export (header, extension mapping, severity policy, encoding bounds, SolarWinds SEM validation boundary).
- `SNMPV3.md`: the SNMPv3 telemetry export served by the Probe (security contract, exposed MIB objects, scope boundary, configuration and validation steps, agent and wire facts).
- `UNIFI-LOCAL-API-CONTRACT.md`: the verified UniFi Network and Protect Local Integration API contract (artifact hashes, bases, corrected calls, Firewall Policies versus ACL Rules, verified response shapes).
- `OPERATIONS-NOTES.md`: Supervisor transport quirks discovered during integration (the journald log gateway's missing Range header and ANSI output).
- `RESOURCE-WATCHDOG.md`: the two-layer container resource watchdog summary (soft Supervisor-native actions, hard Docker caps via the Probe).
- `THREAT-MODEL.md`: assets, trust boundaries, the principal threat table with controls and residual actions, mechanism notes, and assumptions.

## Plans, reviews, and research

- `HA-SOC-Security-Work-Plan.md`: the ordered work items (sprint 0 through 4 and beyond) and the decisions register (D-1 through D-23) that the other documents cite by number.
- `HA-SOC-Sprint-Next-Open-Items.md`: the boundary of the 2026-08-30 implementation round, what shipped, what is still open, owner actions, and hygiene carried forward.
- `FRONTEND-VISUAL-ARCHITECTURE.md`: the console's presentation model, workspace information architecture, Overview rules, Customize contract, accessibility, and delivery phases.
- `automated-calver-release-design.md`: the CalVer release automation through protected branches (invariant, GitHub App configuration, adaptation to other repositories, concurrency and recovery, security boundaries).
- `COMPLIANCE-EVIDENCE-PLAN.md`: what evidence is collected, from where, on what cadence, and who reviews it.
- `NIST-SOC2-CONTROL-MATRIX.md`: the engineering crosswalk from HA SOC capabilities to NIST SP 800-53 and SOC 2 controls, and the priority path.
- `TRANSPORT-SECURITY-MIGRATION.md`: the accepted current transport state, the migration sequence to TLS, and syslog modes.
- `PKI-CERTIFICATE-TEMPLATE-SECURITY-RESEARCH.md`: deferred PKI and certificate template research, the questions a later design must answer, and required outputs.
- `HACS-Takeover-Feasibility-Report.md`: whether HA SOC should absorb HACS's ingestion and upgrade role, with the recommendation and open questions.
- `UPSTREAM-CORE-PROPOSAL.md`: the draft proposal to Home Assistant core for observable authentication and authorization events (D-22), for owner review only.
