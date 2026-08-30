# HA SOC: open items for the next sprint

Companion to docs/HA-SOC-Security-Work-Plan.md (revision 3, every decision
recorded). This file is the boundary of the 2026-08-30 implementation
round: everything above the line in section 1 shipped on this branch;
everything below is deferred, each item with the reason and what unblocks
it. The next sprint starts from section 2 in order.

## 1. Shipped this round (for orientation, not re-work)

- Sprint 0 in full: Probe Supervisor-context authentication (0.1), audit
  chain retention anchor (0.2), one firewall test at a time (0.3), Entity
  ReMap apply plus the panel-wide WS contract test (0.4), the rating truth
  and privilege ledger (0.5), CI test and bundle-drift gates (0.6).
- Sprint 1 in full: the dedicated private secret store with migrations and
  fetch-at-use callers (SEC-1, SEC-2, SEC-3), locator-key allowlist for
  cross-integration reads (SEC-4), the four extraction-pattern scanner
  rules with the self-scan test (SEC-5), the boundary-widening
  misconfiguration checks (SEC-7), audit file modes and private stores
  (1.1), scanner snippet masking (1.3), audit coverage of HA SOC's own
  actions including privileged reads (1.4, D-14), wiped-chain detection
  (1.5), deep service-data redaction (1.6), immediate flush for high-value
  records plus the ban-logger check (1.7), bounded add-on state (1.8),
  remap backups with the !secret/!include refusal (1.9, D-13).
- Sprint 2, the parts not blocked on the D-21 verification run: the
  firewall owner-only in full with the owner discard (2.1, D-4/D-5), cap
  slug validation end to end (2.2), chain-scoped revert with a checked
  backup (2.3), stop-honesty in the add-on finish script (2.6), the D-23
  owner-only gates on admin-targeting and config-rewriting commands, and
  the firewall countdown re-anchored at apply confirmation.
- Decision consequences shipped immediately: hacs.json minimum raised to
  the tested core version (D-16), the upstream proposal drafted for owner
  review (D-22, docs/UPSTREAM-CORE-PROPOSAL.md).

## 2. Blocked on the owner's verification run (D-21)

The read-only script is committed at scripts/ha_soc_verify_supervisor.sh.
Until its FACT lines are pasted back and recorded in ha_soc_probe/DOCS.md,
these stay parked; every one of them consumes a fact only that run settles:

- 2.4 IPv6 firewall parity (D-3 requires it). Needs: which iptables
  backend (legacy or nft) the Probe's binaries and the host's Docker use,
  and whether ip6tables plus the ip6_tables kernel module are present. If
  the backends differ, the add-on must switch to the host's backend before
  2.4 ships.
- 2.5 Hardening the single add-on: the AppArmor profile (needs the live
  profile state), the unprivileged scanner service (needs the container's
  readable-paths facts), the base-image digest pin, and the image-signing
  investigation.
- 2.7 The verification write-up itself: record every FACT line in
  ha_soc_probe/DOCS.md and clear the plan's section 6.2.
- SEC-6 envelope encryption with the key in the Probe's volume: opt-in,
  depends on the sprint 2 add-on changes; the plan itself sanctions it
  slipping without blocking anything. Its honesty constraints (what it
  does and does not defend) are already written into the plan.

## 3. Next sprint, in plan order (decisions recorded, ready to implement)

Sprint 3, detections and scores:

- 3.0 The tunable-threshold table with secure defaults, owner-only, with
  the reset control (D-9). The full parameter table is in the plan.
- 3.1 to 3.9 rule fixes: address-family prefixes, bounded
  disabled_user_activity, evidence retention (D-6: 365 days, resolved and
  dismissed only), provisional posture (D-10: badge, computed-once-ever),
  reachable never_logged_in and reconciled factors, new_ip_login without
  amnesty, silent off-hours seeding, success_after_failures on new tokens
  only, closed episodes stay closed.
- 3.10 Entity exposure (D-19: grade only; user-id entity ids; note the
  owner must migrate any automation reading breakdown attributes).
- 3.11 MFA and external authentication (D-18 option (a): non-native
  provider users exempt from auto_deactivate, reported "MFA not
  assessable", plus the documentation line).

Sprint 4, honest coverage and hardening: 4.1 through 4.14 as written
(D-11 severity values as proposed; D-12: NVD disclosed with a toggle,
OSV opt-in; note 4.14's millisecond backup stamp already shipped with
1.9).

Sprints 5 through 8, visibility waves and export, as written in the plan.
Decision consequences to carry in: D-20's "acknowledged by design" row
for the Probe in the 7.1 add-on inventory (a visible documented
exception, never a silent exemption); D-15's syslog-over-TLS-first order
for 8.2; the login_ok to session_activity rename at the 8.1 schema
versioning step, with a migration note.

## 4. Owner actions (no code can substitute)

- Run scripts/ha_soc_verify_supervisor.sh from the SSH add-on (Protection
  Mode off for the container-level facts, then back on) and paste the
  output. This is the recorded D-21 decision's missing input and the
  gate for section 2 above.
- Mark the CI checks (pytest, bundle-drift) required in branch
  protection; a workflow file cannot set that.
- Review docs/UPSTREAM-CORE-PROPOSAL.md and decide whether to submit it
  (D-22 covers drafting only; filing is the owner's call).
- Optional: supply HA-SOC-Security-Review-2026-08-30.md and
  tests/test_review_verification.py from the review thread if their
  evidence text should be mirrored into this repository; the guarantee
  tests were written directly in their absence.
- Cut the next release through scripts/release.sh after merge.

## 5. Hygiene carried forward

- Repository-wide em-dash sweep of pre-existing prose (house style; new
  and rewritten lines already comply). Best done as its own mechanical
  commit so functional diffs stay reviewable.
- The plan's section 6.2 UniFi field-name # VERIFY markers remain until
  confirmed against the owner's console firmware.
