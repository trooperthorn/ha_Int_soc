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

## 2. Unblocked by the completed verification runs (D-21 delivered)

The owner ran the script twice on 2026-08-30; every fact is recorded in
ha_soc_probe/DOCS.md, the plan's section 6.2 is reduced to three
entries none of which gates code, and item 2.7 is complete. What the
runs settled for the items below: both the add-on and the host use the
nf_tables backend (no switch needed), ip6tables works, the LAN and VLAN
both carry global IPv6, the effective AppArmor profile is
docker-default, the capability set is the Docker default plus
NET_ADMIN, and the Docker socket is genuinely unmounted under
Protection Mode. These are now ordinary next-sprint work, first in
line:

- 2.4 IPv6 firewall parity (D-3 requires it): fully unblocked, no
  backend switch needed; mirror the chain, backups, atomic apply, and
  revert into ip6tables per the plan's item text.
- 2.5 Hardening the single add-on: custom AppArmor profile (baseline
  confirmed docker-default), unprivileged scanner service, base-image
  digest pin, image-signing investigation.
- SEC-6 envelope encryption with the key in the Probe's volume: opt-in,
  builds on the sprint 2 add-on changes; its honesty constraints are
  already written into the plan.

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

- (Done 2026-08-30: both verification runs delivered; nothing in
  section 2 waits on the owner any more.)
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

Two small gaps surfaced while shipping sprint 2, both add-on protocol
shaped and deliberately not widened mid-round:

- The ingest protocol carries a status but no failure reason, so a
  `backup_failed` refusal reports to Home Assistant as a plain
  `reverted`; the reason lives only in the add-on's log. Adding a
  bounded reason field is a small next-sprint item.
- A revert that finds its chain snapshot missing logs an error and
  leaves the chain as-is (parity with the pre-existing missing-backup
  behavior); if that path ever fires in practice it deserves a finding
  of its own.

Two observations from the first live run, filed here so they are not
lost:

- Every s6 service stop logs "exited with code 256, restarting" from
  both run scripts' supervision loops before s6 finishes the stop, so a
  routine add-on update reads like a crash loop in the log. The fix is
  graceful TERM handling in both run scripts, designed together with
  the finish script's recovery so a deliberate stop still reverts an
  armed test exactly once.
- The live install writes roughly 10 MB of audit records per day, which
  reaches the 200 MB size cap in about three weeks. Verification
  survives that now (the retention anchor), but the capture volume
  itself deserves a look alongside the sprint 3 threshold work: what
  category is producing the bulk, and whether it earns its space.
- The live Core is 2026.8.3 while the pinned test harness brings
  2026.2.3. The D-16 decision (test latest only) suggests bumping the
  harness pin, and its frontend companion, to the newest release in the
  next sprint so "tested on" tracks what actually runs in production.
- The pairing secret file mode fix (0600 at creation and on startup)
  shipped with this round after the verification run found 0644; listed
  here only so the changelog line is traceable to its evidence.


- Repository-wide em-dash sweep of pre-existing prose (house style; new
  and rewritten lines already comply). Best done as its own mechanical
  commit so functional diffs stay reviewable.
- The plan's section 6.2 UniFi field-name # VERIFY markers remain until
  confirmed against the owner's console firmware.
