# HA SOC: open items for the next sprint

Companion to docs/HA-SOC-Security-Work-Plan.md (revision 3, every decision
recorded). This file is the boundary of the 2026-08-30 implementation
round: everything in section 1 shipped on this branch; everything below
is deferred, each item with the reason and what unblocks it. Sprints 0
through 4 are complete in full, including item 4.12's frontend half; the
next sprint starts from section 2.

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
- Sprint 2 in full: the firewall owner-only in full with the owner discard
  (2.1, D-4/D-5), cap slug validation end to end (2.2), chain-scoped
  revert with a checked backup (2.3), IPv6 firewall parity (2.4, D-3:
  family-pinned rules, mirrored HA_SOC_RULES chain in ip6tables, four
  checked backups per apply, atomic cross-family revert, a read-time
  partially_applied flag when a host lacks ip6tables, never persisted),
  hardening the single add-on (2.5, D-2: a custom AppArmor profile
  grounded in the official developer-docs example, the port-scanner
  service dropped to nobody, a digest-pinned base image, local
  re-validation of every field Core sends, and the recorded image-signing
  answer), stop-honesty in the add-on finish script (2.6), the D-23
  owner-only gates on admin-targeting and config-rewriting commands, and
  the firewall countdown re-anchored at apply confirmation.
- Sprint 3 in full (3.0 to 3.11): the owner-tunable detection-threshold
  table with secure defaults, ranges, audited per-field diffs, and a reset
  control (D-9); address-family-aware prefixes; new_ip_login losing its
  amnesty; silent off-hours seeding with a scaled burst threshold;
  success_after_failures requiring a genuinely new token; closed episodes
  staying closed; disabled-user and privilege-escalation risk caps;
  applied_points on every risk factor; reachable never_logged_in;
  provisional posture as a badge naming the missing terms (D-10); evidence
  retention at 365 days for resolved/dismissed records with bulk resolve
  (D-6); grade-only entity exposure with user-id-derived entity ids
  (D-19); the MFA not-assessable exemption for users authenticating solely
  through a non-native provider (D-18); password resets revoking the
  target's interactive sessions by default; and the audit tab's
  per-category volume breakdown.
- Sprint 4 in full (4.1 to 4.14): misconfiguration sweeps waiting out
  startup grace with findings surviving empty passes; the proxy-trust
  check; Supervisor checks failing closed on missing keys with a named
  could_not_evaluate finding; D-11 severity recalibration with the
  Probe's D-20 acknowledged-by-design exception (applied only while hard
  caps are configured, surfaced in the frontend as a distinct
  "acknowledged by design" tag rather than a silent pass); scanner
  per-domain coverage records so an unscanned domain never reads as zero
  findings, plus findings reconciliation on rescan; the NVD lookup toggle
  with paging and vendor-only-match downgrade; GitHub provenance slug
  validation against dot-segment redirection; UniFi client hardening (no
  redirects, capped bodies, bounded snapshots); the peripherals
  word-boundary matching fix; and item 4.12, frontend truthfulness, across
  all eleven panel views. Every view's load path now catches its own
  failure into a distinct could-not-load state, with the server's message
  and a Retry button, rather than ever rendering a failure the same as "no
  data," an endless loading spinner, or an unrelated specific backend
  state. Three genuine pre-existing bugs came out of that pass and are
  fixed as part of it: settings-view.ts and integration-security-view.ts
  had no catch around their outer fetch at all, so a failed load showed
  "Loading settings..."/its equivalent forever with no way to tell it
  apart from a slow network; peripherals-view.ts rendered a failed
  WebSocket call as the specific, false claim that Home Assistant's own
  usb discovery component had been disabled; and entity-remap-view.ts had
  no try/catch/finally at all around its broken-references load, so a
  rejection left that section's "Loading..." state permanent.
- Decision consequences shipped immediately: hacs.json minimum raised to
  the tested core version (D-16), the upstream proposal drafted for owner
  review (D-22, docs/UPSTREAM-CORE-PROPOSAL.md).

## 2. Still open (not started this round)

- SEC-6 envelope encryption with the key in the Probe's volume: opt-in,
  builds on the sprint 2 add-on changes; its honesty constraints (what an
  attacker with volume access still gains, and what they don't) are
  already written into the plan. This is the one item assigned in this
  round that never started; the agent given the task terminated before
  writing any files, and no other agent picked it up. First in line for
  whoever continues past this round.

## 3. Next sprint, in plan order

Sprints 5 through 8, visibility waves and export, as written in the plan.
Decision consequences to carry in: D-20's acknowledged-by-design pattern
already shipped for the health.py Probe case (sprint 4); extend the same
pattern, not a new one, to the 7.1 add-on inventory. D-15's
syslog-over-TLS-first order applies to 8.2. The login_ok to
session_activity rename at the 8.1 schema versioning step needs a
migration note that accounts for the new_token tag sprint 3 added to
login_ok records (success_after_failures needed it to distinguish the
token-grant branch; the renamed schema should keep the distinction, not
drop it).

## 4. Owner actions (no code can substitute)

- Mark the CI checks (pytest, bundle-drift) required in branch
  protection; a workflow file cannot set that.
- Review docs/UPSTREAM-CORE-PROPOSAL.md and decide whether to submit it
  (D-22 covers drafting only; filing is the owner's call).
- Optional: supply HA-SOC-Security-Review-2026-08-30.md and
  tests/test_review_verification.py from the review thread if their
  evidence text should be mirrored into this repository; the guarantee
  tests were written directly in their absence.
- Cut the next release through scripts/release.sh after merge.
- Decide whether and when to pick up SEC-6 (section 2).

## 5. Hygiene carried forward

- The live install writes roughly 10 MB of audit records per day, which
  reaches the 200 MB size cap in about three weeks. Verification survives
  that (the retention anchor), and the audit tab's new per-category
  volume breakdown (shipped with sprint 3) now gives a way to see which
  category is producing the bulk; actually looking at that breakdown
  against the live install and deciding whether any category's volume
  should be trimmed is still open.
- The live Core is 2026.8.3 while the pinned test harness brings 2026.2.3.
  The D-16 decision (test latest only) suggests bumping the harness pin,
  and its frontend companion, to the newest release in the next sprint so
  "tested on" tracks what actually runs in production.
- Repository-wide em-dash sweep of pre-existing prose (house style; new
  and rewritten lines already comply, including everything shipped this
  round). Confirmed still present in older prose carried into the
  compiled frontend bundle by the build step. Best done as its own
  mechanical commit so functional diffs stay reviewable.
- The plan's section 6.2 UniFi field-name # VERIFY markers remain until
  confirmed against the owner's console firmware.
- A revert that finds its chain snapshot missing logs an error and leaves
  the chain as-is (parity with the pre-existing missing-backup behavior,
  now checked per family since 2.4); if that path ever fires in practice
  it deserves a finding of its own.
