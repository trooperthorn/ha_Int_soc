# HA SOC Security Work Plan

Implementation brief for the agent maintaining `trooperthorn/ha_Int_soc`. It turns the 2026-08-30 security review of commit `9ddd23a` into ordered, testable work items for the integration and the HA SOC Probe add-on, and it separates the items that can be implemented as written from the ones that need a decision from the repository owner first.

Companion files: `HA-SOC-Security-Review-2026-08-30.md` (the review, with the evidence behind every item below), `tests/test_review_verification.py` (six pytest cases that pass on the unpatched tree because they reproduce defects; each is inverted into a regression test by the item that fixes it), and `ha_soc_verify_supervisor.sh` (the read-only verification script for decision D-21).

Revision 2, 2026-08-30: decisions D-1, D-2, D-3, D-4, D-5, D-7, D-8, D-9, and D-21 are recorded in section 2 and the affected items are rewritten; section 2A (secrets at rest) and item 3.0 (tunable thresholds) are new; section 6 reflects seven facts that were verified after the first revision.

Revision 3, 2026-08-30: the owner directed "implement all recommendations"; every remaining decision (D-6, D-10 through D-20, D-22, D-23) is recorded in section 2 with the recommendation from the decision register report as the choice, and the five intent statements below the register are settled the same way. Sprint 0 shipped in full. Work now proceeds in plan order; docs/HA-SOC-Sprint-Next-Open-Items.md carries every item deferred to the next sprint and why.

## 0. How to work this plan

1. Read `README.md`, the module docstrings of every file you touch, and this section before changing anything. The docstrings are the contract; when a change alters a documented behavior, update the docstring in the same commit.
2. Work the items in order within a sprint. Sprint 0 ships first and alone. Do not start a later sprint's item because it is nearby in the file.
3. Every item ends with all of: the named tests added or inverted and passing, the full suite passing (`pytest tests/` under `pytest-homeassistant-custom-component` on Python 3.13, see section 7), and the README, `ha_soc_probe/DOCS.md`, and `ha_soc_probe/CHANGELOG.md` updated wherever the item changes documented behavior.
4. Items tagged **Decision D-n** are blocked on the decisions register in section 2. Until the decision is recorded there, implement only the part marked "safe default" for that item.
5. Never state a fact you have not looked up. Platform facts you may rely on are listed in section 6 with the version they were verified against. Anything in section 6.2 is unverified and must be verified on a real install (or left labeled UNVERIFIED in code comments and docs) before code depends on it.
6. House style: complete sentences, explain why, no em dashes in any committed file (use a hyphen, a comma, or restructure), no attribution footers or generation notices, no real credentials or hostnames in examples, counts in prose must match the data.
7. Honesty labels are load-bearing. Do not remove or soften an `enforced`, `cosmetic`, `best_effort`, or `advisory` label; when a fix changes a control from cosmetic to enforced or the reverse, change the label and say why in the docstring.
8. Releases go through `scripts/release.sh` so the manifest, the add-on `config.yaml`, and `SCANNER_VERSION` move in lockstep. Never bump one by hand.
9. Do not weaken any existing gate. Specifically: `@require_owner` stays on Settings, `watchdog/set`, and `firewall/reset_pairing`; `async_set_password` stays owner-only; `access_level` stays owner-only by default.

Severity in this plan follows the review: High means the condition defeats a control or makes the tool tell the operator something false; Medium weakens a control; Low is hygiene or defense in depth.

## 1. Sprint map

Blocked-on columns show only decisions still pending after revision 2. D-1, D-2, D-3, D-4, D-5, D-7, D-8, D-9, and D-21 are recorded and their items are ready to implement.

| Sprint | Goal | Items | Blocked on decisions |
| --- | --- | --- | --- |
| 0 | Restore the claims the product already makes (hotfix release) | 0.1 to 0.7 | none (D-1 and D-4 recorded) |
| 1 | The integration's own data: secrets at rest (section 2A), chain integrity, audit completeness | 1.1 to 1.9, SEC-1 to SEC-7 | D-6, D-14 |
| 2 | The Probe contract: one owner, one state, IPv6 parity, honest privileges | 2.1 to 2.7 | D-20, D-23 |
| 3 | Detections and scores that mean what they say, with tunable thresholds | 3.0 to 3.11 | D-10, D-19 |
| 4 | Checks honest about their own coverage; scanner, NVD, GitHub, UniFi, frontend hardening | 4.1 to 4.14 | D-11, D-12, D-13, D-17, D-18 |
| 5 | Visibility wave 1: UI surface | 5.1 to 5.12 | none |
| 6 | Visibility wave 2: integrations | 6.1 to 6.8 | D-12 |
| 7 | Visibility wave 3: add-ons and the platform | 7.1 to 7.9 | D-20, D-21 |
| 8 | Off-box export, evidence pack, schema | 8.1 to 8.5 | D-15 |

## 2. Decisions register (ambiguous areas)

Each entry names the choice, the options, the recommendation from the review, and the safe default the agent applies until the owner records a decision. Record decisions by editing the "Decision" line in place so the plan stays the single source of truth.

### D-1  Probe authentication model

The Probe reaches Core through the Supervisor proxy, which forwards with the Supervisor's own token and passes no add-on identity (verified, section 6.1). Core therefore sees every proxied call as the Supervisor system user. Options:

- (a) Require the Supervisor system user context on both services and keep the shared secret as defense in depth (recommended).
- (b) Require the Supervisor context only and drop the secret and the pairing reset.
- (c) Keep trust-on-first-use only (not recommended; the race is reproduced by test).

Open sub-questions: on a Core or Container install the services cannot be legitimately called at all; should they be unregistered there (recommended) or registered and always rejecting? Should a rejection raise a detection (recommended, HIGH, one per caller per hour) or only an audit record?

Safe default: (a), unregister on non-Supervisor installs, audit record plus detection on rejection.
Decision: recorded 2026-08-30, option (a) as recommended. Item 0.1 is unblocked as written.

### D-2  Probe privilege packaging

`docker_api: true` sets the Supervisor rating to 1 unconditionally. Options:

- (a) Split the hard-cap applier into a second add-on that declares `docker_api` and nothing else; the port and firewall Probe then rates 3 (host_network -1, NET_ADMIN -1).
- (b) Remove hard caps and `docker_api`; keep the watchdog's supported-API restart and stop path.
- (c) Keep one add-on and document the rating of 1 accurately.

Safe default: (c) documentation only, no functional change, plus the `addon_unprotected` exemption in D-20.
Decision: recorded 2026-08-30: one add-on, and it must carry every feature the integration needs; the Supervisor rating is secondary to the report and to the corrective impact. Consequences: `docker_api` and hard caps stay in the Probe; item 0.5 documents the rating of 1 as a deliberate choice with a privilege ledger; item 2.5 becomes "harden the single add-on" (AppArmor profile, unprivileged scanner service, pinned base image, no listening sockets, local input validation) instead of a split.

### D-3  IPv6 firewall parity

The Probe reports IPv6 listeners but writes IPv4 rules only. Options: (a) mirror every rule into `ip6tables` in the same chain name, with the same backup and revert; (b) label the feature "IPv4 only" on the card, in the rule builder, and in the docs. (a) is the honest control; it also doubles the surface of the revert logic and should land after the sprint 2 state-machine fixes.

Safe default: (b) now, (a) as a follow-up item in sprint 2 once D-3 is recorded.
Decision: recorded 2026-08-30: IPv6 parity is required. The IoT and Wi-Fi networks users reach are fully IPv6-enabled, so every firewall capability must behave identically for IPv6 and IPv4. Item 2.4 is the full mirroring design; the label variant is dropped except as the honest fallback when the host kernel has no `ip6_tables` support (a D-21 fact).

### D-4  Privilege tier for host firewall mutation

`firewall/test`, `confirm`, and `cancel` are available to every admin under `owner_and_admins`; `watchdog/set` is owner-only. Options: (a) owner-only for all three (recommended, matches the watchdog and the stated reasoning); (b) a third access level such as `owner_and_admins_host` that unlocks host mutation for admins explicitly.

Safe default: (a).
Decision: recorded 2026-08-30: the firewall is owner-only in its entirety, including `firewall/status`, so that no other account can attempt a takeover or a change that ends in the platform being unreachable. Item 2.1 applies `@require_owner` to all five firewall commands and hides the card for non-owners. See D-23 for the same question applied to the other destructive commands.

### D-5  Behavior when the add-on goes silent mid-test

Sprint 0 blocks a new proposal until the add-on reports the previous test. If the add-on is stopped, reinstalled, or crashes without recovering, `pending` could stay occupied. Options: (a) owner-only `firewall/discard_pending` that archives the record as `discarded_unreported` and audit-logs it; (b) auto-archive after `window_seconds + 600` with status `expired_unreported` and unblock automatically; (c) both, with (b) only unblocking when the add-on has since reported an empty `current_test_id`.

Safe default: (a) plus the display-only auto-expire that exists today; never auto-unblock.
Decision: recorded 2026-08-30 together with D-4: owner-only `firewall/discard_pending`, no automatic unblocking, every discard audited. Item 2.1 includes it.

### D-6  Retention and evidence periods

Audit files default to 90 days or 200 MB; detections, findings, and firewall history have no retention at all. Options: (a) add `evidence_retention_days` (default 365) governing detections, findings, and firewall history, keep `audit_retention_days` for the log; (b) one retention setting for everything; (c) leave findings unbounded and prune only resolved detections.

Safe default: (a) with 365 days, pruning only `resolved` and `dismissed` records past the period.
Decision: recorded 2026-08-30 (owner: implement all recommendations): option (a), `evidence_retention_days` default 365, pruning only `resolved` and `dismissed` records; open items never expire. Item 3.3 is unblocked.

### D-7  Mirroring settings into `entry.options`

Nothing reads `entry.options` after first load. Options: (a) remove the mirror and the seed-from-options path entirely, with a one-release migration that scrubs secrets from existing options; (b) keep the mirror but strip `SECRET_SETTING_KEYS`. (a) deletes a code path that was written deliberately; (b) keeps a redundant copy of non-secret settings.

Safe default: (b).
Decision: recorded 2026-08-30 with D-8: secrets must live in a proper, dedicated secure area of the tool, must never be passed to other integrations, and must be as hard as the platform allows to leak or extract with malicious tools or integrations. The research and the resulting design are in section 2A; items SEC-1 to SEC-7 replace items 1.1 and 1.2. The `entry.options` mirror is removed entirely (option (a) of D-7).

### D-8  Secrets at rest beyond file mode

Core stores integration credentials in plaintext at 0o600. Options: (a) match core: `private=True, atomic_writes=True`, 0o600 audit files, nothing more; (b) additionally encrypt the four API keys and the pairing secret with a random key kept in a separate 0o600 file. (b) is obfuscation within the same trust boundary and must not be described as protection against `.storage` access.

Safe default: (a).
Decision: recorded 2026-08-30, see D-7 and section 2A. Summary of the outcome: a dedicated private secret store separate from settings, secrets never held in shared runtime objects, never mirrored, never in audit, diagnostics, entity attributes, or WebSocket payloads; encryption at rest is implemented only where a real key boundary exists (the Probe's own volume), and is described as obfuscation where it does not; HA SOC's own cross-integration reads are narrowed to an allowlist; scanner rules and misconfiguration checks are added so the tool detects the extraction patterns it cannot prevent.

### D-9  Detection rule semantics and thresholds

The review recommends specific values; they change what the operator sees and should be confirmed:

- IPv6 baseline prefix length: `/48` (recommended) or `/56` or `/64`.
- `new_ip_login`: a prefix joins the baseline only after being seen on N distinct days (recommended N=3); `seen_prefixes` entries expire after 180 days.
- `success_after_failures`: require a genuinely new refresh token (the `previous is None` branch in `audit.py`), and de-rate to HIGH when the source IP is shared by more than one user in the window.
- `disabled_user_activity`: one detection per `(user, category)` per pass; cap the risk factor at 40.
- `off_hours_anomaly`: the seeding pass emits nothing; the burst threshold scales with the scanned span.
- `risk_learning_period_days`: used as the maturity gate for both `new_ip_login` and `off_hours_anomaly` (replacing the two hard-coded 14-day constants), or removed from Settings.

Safe default: the values above.
Decision: recorded 2026-08-30: every detection threshold is modifiable from the owner-only Settings tab, and the default for each is the most secure option. New item 3.0 defines the parameter set, the secure defaults, the allowed ranges, and the "Reset to secure defaults" control; items 3.1, 3.2, 3.6, 3.7, and 3.8 read their values from it.

### D-10  Provisional posture

When any posture term has never computed, show: (a) the grade with a "provisional" badge and the missing terms listed; (b) no grade, only the terms that exist. "Computed once ever" versus "computed within the last 24 hours" also needs a call.

Safe default: (a), computed-once-ever.
Decision: recorded 2026-08-30: option (a), computed-once-ever. A hidden grade reads as a broken tile; a labeled provisional grade is honest and useful on day one. Item 3.4 is unblocked.

### D-11  Severity recalibration

Proposed: `addon_unprotected` HIGH, CRITICAL when the add-on also has `host_network`; `notify_coverage_gaps` LOW for an untracked source and MEDIUM for a source the operator toggled off; unknown severities map to WARNING not CRITICAL in Repairs; `alert_unknown_references` stays HIGH. Confirm or amend.

Safe default: as proposed.
Decision: recorded 2026-08-30: as proposed. Note for operators: while the D-21 verification script runs with the SSH add-on's Protection Mode off, that add-on trips the CRITICAL case by design; it clears on re-enable. Item 4.4 is unblocked.

### D-12  Outbound lookups (NVD today, OSV later)

Device manufacturer and model strings go to NIST today with no disclosure or toggle. Options: (a) on by default with a disclosure in the docstring, README, and next to the key field, plus a toggle; (b) off by default (opt-in). The same choice applies to the sprint 6 `requirements` lookup.

Safe default: (a) for NVD (existing behavior, now disclosed), (b) for the new OSV lookup.
Decision: recorded 2026-08-30: option (a) for NVD (stays on, now disclosed in docs and Settings with an off toggle), opt-in for the new OSV lookup. Items 4.9 and 6.2 are unblocked.

### D-13  Entity ReMap and YAML fidelity

The YAML round-trip drops comments, anchors, and key order, and would inline `!include` and either fail or resolve `!secret` (UNVERIFIED which). Options: (a) accept comment loss as core's own editor does, state it in the consequence text, back everything up; (b) refuse to rewrite a file that contains `!secret` or `!include` and report "manual edit required" for it; (c) adopt a round-trip YAML library that preserves comments (new dependency).

Safe default: (a) plus (b).
Decision: recorded 2026-08-30: (a) plus (b) together; comment loss is accepted and stated, files carrying `!secret` or `!include` are refused with "manual edit required". A round-trip YAML dependency is rejected for now as supply-chain surface; revisit only if the refusals hit files that genuinely need remapping. Item 1.9 is unblocked as written.

### D-14  Audit logging of privileged reads

Logging reads of the host journal, Supervisor and add-on logs, and a user's token list adds volume. Options: (a) log those reads and nothing else; (b) log every `ha_soc/*` read; (c) log nothing new. The review recommends (a).

Safe default: (a).
Decision: recorded 2026-08-30: option (a), privileged reads only (host/Supervisor/add-on logs, the crash log, a user's token list). Item 1.4 is unblocked as written.

### D-15  Off-box export target

Syslog (RFC 5424) over TLS, CEF, and a generic HTTPS webhook are all reasonable; the first one to build depends on the SIEM the owner actually runs. Name it.

Safe default: syslog over TLS first, webhook second.
Decision: recorded 2026-08-30: the safe default stands as the recorded choice; syslog (RFC 5424) over TLS first, generic HTTPS webhook second. If the owner later names the SIEM actually in use, the first exporter gains a tested config example for it; the order itself is settled.

### D-16  CI matrix and minimum core version

`hacs.json` says 2025.1.0; the suite was run on 2026.2.3; sibling repositories target 2026.5 and later. Options: (a) test the minimum in `hacs.json` and the latest harness release; (b) raise the minimum and test only that and latest.

Safe default: test latest only until decided, and record the version tested in the README.
Decision: recorded 2026-08-30: option (b); the `hacs.json` minimum is raised to 2026.2.0, the core version the suite actually runs against, and CI tests latest only. The stated minimum must remain a tested fact; a second minimum-version CI job is added only if support for older cores is ever actually wanted.

### D-17  Frontend test approach

Options: (a) a Python contract test that extracts each `type: "ha_soc/..."` payload from `frontend/src/data/ha-soc-ws.ts` and asserts the keys satisfy the server's voluptuous schema; (b) Vitest with a mocked `hass`; (c) both. (a) is cheap and would have caught UI-1.

Safe default: (a).
Decision: recorded 2026-08-30: option (a), already shipped in sprint 0 item 0.4 (`tests/test_ws_contract.py`, all 58 panel payloads checked). Vitest is revisited only if visual or state-handling regressions recur.

### D-18  MFA policy and external authentication

`auto_deactivate` judges HA-native MFA only. An install fronted by a header-auth SSO proxy with upstream MFA would deactivate compliant admins. Options: (a) exempt users whose only credentials are from a non-`homeassistant` provider and report them as "MFA not assessable"; (b) leave as is and document.

Safe default: (b) with the documentation line added now.
Decision: recorded 2026-08-30: option (a); users whose only credentials come from a non-`homeassistant` auth provider are exempt from `auto_deactivate` and reported as "MFA not assessable". Implemented with sprint 3 (item 3.11 grows the code half); the documentation line lands with it.

### D-19  Entity attribute exposure

`sensor.ha_soc_posture` exposes the full breakdown to every user. Options: (a) grade only, breakdown stays behind `ha_soc/risk/posture`; (b) keep for automations. Also decide the per-user risk sensor naming (user name versus user id in the entity id; names change, ids do not).

Safe default: (a); entity id from the user id.
Decision: recorded 2026-08-30: option (a); the posture sensor exposes the grade only and per-user risk entity ids derive from the user id. Owner note: any automation reading the breakdown attributes must move to the grade or the WS data when item 3.10 lands.

### D-20  Add-on rating threshold and the Probe's self-flag

The new add-on privilege inventory needs a rating threshold that raises a finding (proposed: below 3). The `addon_unprotected` check flags the Probe itself whenever hard caps require protection off. Options: exempt the Probe only while hard caps are configured; never exempt; always exempt.

Safe default: exempt only while hard caps are configured.
Decision: recorded 2026-08-30: threshold as proposed (finding below 3), and for the Probe itself a third path replaces the exemption options: its inventory row renders as "acknowledged by design", linked to the privilege ledger, instead of an open finding, while every other low-rated add-on still gets the finding. A silent exemption is a blind spot and a permanent alarm trains alarm fatigue; a visible documented exception is the honest middle. Item 7.1 implements it this way.

### D-21  Verification on a real Supervisor

The README states the add-on has never run on a real Supervisor. Several items depend on facts only that run can settle (section 6.2). The owner has a Home Assistant OS install on generic-x86-64; a single session there, recording the facts below into `ha_soc_probe/DOCS.md`, unblocks them.

Decision: recorded 2026-08-30: the owner runs the read-only script `ha_soc_verify_supervisor.sh` from the SSH add-on (container-level facts need the SSH add-on's Protection Mode off for the duration of the run, then back on) and pastes the output into the thread; the agent then records every `FACT` line in `ha_soc_probe/DOCS.md` and clears the matching entries in section 6.2. Item 2.7 is the write-up step.

### D-22  Upstream proposals to Home Assistant core

Attempted-username on failed login, permission-denied events, and long-lived-token success signals are unobservable without core changes. Decide whether to draft an architecture proposal (an `auth_failed` bus event carrying provider and a hashed username; a `permission_denied` event). Not implementation work in this repository.

Decision: recorded 2026-08-30: option (a), draft the proposal. The draft lives at docs/UPSTREAM-CORE-PROPOSAL.md for owner review before anything is filed upstream; nothing is sent anywhere by the repository itself.

### D-23  Owner-only for the other destructive commands

D-4 makes the firewall owner-only to prevent a takeover by another admin. The same reasoning applies to commands that can lock out or disable the platform through HA SOC: deactivating, deleting, or revoking the sessions of a user in the admin group; `entity_remap/apply`; `sidebar/push`. Options: (a) owner-only when the target is an admin-group user or when the action rewrites configuration, admins keep the rest; (b) owner-only for all mutations, `owner_and_admins` becomes read-only plus finding triage; (c) leave as is.

Safe default: (a).
Decision: recorded 2026-08-30: option (a); owner-only whenever the target is an admin-group user or the action rewrites configuration (`entity_remap/apply`, `sidebar/push`), while admins keep routine management of non-admin users. Consistent with D-4's takeover reasoning without making the admins tier pointless.

### Ambiguities in existing intent (not defects, need a statement)

- `login_ok` is a token-activity signal, not an authentication event. Consider renaming the category to `session_activity` (with a migration note for exports) so downstream consumers stop reading it as a login. Owner's call, since it changes the exported vocabulary.
- Under `owner_and_admins`, a non-owner admin can deactivate other admins, revoke their sessions, and run entity remaps. Confirm this is the intended meaning of "open to admins".
- `expires_at` is set at propose time while the add-on's timer starts at apply time. Confirm that the display countdown may run up to one poll interval ahead of the real timer, or move `expires_at` to `applied_at` (sprint 0 item 0.3 leaves it as is).
- `notify_coverage_gaps` was written as HIGH; the review reads it as near-universal on real installs. Confirm the intent behind the severity.
- `risk_learning_period_days` exists in Settings but is read nowhere; confirm it was meant to be the maturity gate for the behavioral rules.

Statements recorded 2026-08-30 with the decisions above: the `login_ok` to `session_activity` rename happens at the sprint 8 schema-versioning step, once, with a migration note; the `owner_and_admins` meaning is settled by D-23 option (a); the firewall countdown is re-anchored at apply confirmation in the sprint 2 firewall work rather than documented as drift; the `notify_coverage_gaps` downgrade to the D-11 LOW/MEDIUM split is confirmed; `risk_learning_period_days` needs no further statement, D-9 already replaced it with per-rule learning periods.


## 2A. Secrets at rest: research, options, and the design (D-7, D-8)

### What Home Assistant actually provides

Every statement here was checked against the installed core 2026.2.3 source, the Supervisor source at `c5a5477`, or the published documentation; nothing is inferred.

| Mechanism | What it is | Who can read it | Verdict for HA SOC |
| --- | --- | --- | --- |
| `secrets.yaml` with `!secret` | A plaintext YAML file in the config directory whose values are substituted into YAML configuration at load time (`util/yaml/loader.py::secret_yaml`, delegating to the `annotatedyaml` package). It only applies to YAML files loaded with a `Secrets` object; `load_yaml(path)` without one raises `Secrets not supported in this YAML file`. Keyring and credstash back ends were removed years ago; there is no encrypted variant. | Any code in the Core process (same uid, same directory), any add-on with the config directory mapped (SSH, Samba, File editor, Studio Code Server), anyone with the disk. Usually written 0o644. | Not a security boundary. It is a convenience for keeping secrets out of shared YAML. HA SOC has no YAML configuration, so `!secret` does not apply to it; offering a "reference a secrets.yaml key" option would move the value to a file that is, if anything, more widely readable. Rejected. |
| Config entry `data` and `options` | Where UI-configured integrations keep credentials. Stored in `.storage/core.config_entries` by `ConfigEntryStore`, which does not pass `private=True` (`config_entries.py:1943-1951`), so the file is 0o644. | Any code in the Core process via `hass.config_entries.async_entries()`, every add-on with the config directory, anyone with the disk. | This is the "Credential area" most integrations use, and it is weaker than a private Store. HA SOC should not move its keys here, and should stop mirroring them here (item SEC-2). |
| Application Credentials (Settings, Devices and services, Application credentials) | OAuth client id and secret store for OAuth-based integrations, `Store(hass, STORAGE_VERSION, STORAGE_KEY)` without `private` (`components/application_credentials/__init__.py:151`). | Same as above. | Not applicable (HA SOC uses API keys, not OAuth clients), and no stronger than config entries. |
| `Store(private=True, atomic_writes=True)` | The helper core uses for the auth store (refresh tokens), the `homeassistant` auth provider (password hashes), and both MFA modules. Files are written 0o600 through a temp file and rename (`helpers/storage.py:238`, `util/file.py:55-62`). | The Core process (any integration in it), root on the host, add-ons that run as root with the config directory mapped. Not readable by other uids. | The strongest at-rest primitive core offers. HA SOC's secrets belong in exactly this, in their own file, separate from settings (item SEC-1). |
| Process isolation | None. Integrations are modules imported into one Python process. Any integration can read another's `hass.data`, `entry.runtime_data`, module globals, and files. The static scanner in HA SOC exists because of this. | Every integration. | The honest limit. No arrangement inside Core keeps a secret from a hostile integration running in Core. What can be done is to shrink the number of places a secret exists, keep it out of shared objects, and detect the extraction patterns. |
| Add-on volumes (`/data` per add-on) | The Supervisor gives each add-on its own persistent volume that other add-ons and Core do not see unless explicitly mapped. | That add-on (root inside it), the Supervisor, root on the host. | The only real key boundary available on a Supervisor install. Used for the Probe's own secret today. Usable as a key holder for Core's ciphertext (item SEC-6), which is a genuine improvement only against a single leaked file, not against a hostile integration. |
| Backups | Cloud backups are encrypted by default; other locations are optional. Since 2026.4 the format is SecureTar v3 (Argon2id, XChaCha20-Poly1305). The encryption key is retained inside the system (`.storage/backup`), with the emergency kit as the off-system copy. | A backup taken off-box is protected only if encryption was on for that location. | Backup encryption on for every location is the control that protects `.storage` once it leaves the box. HA SOC should check it (item SEC-7, and sprint 7.7). |
| Disk encryption | Home Assistant OS has no native full-disk or data-partition encryption; the requests are open community feature requests. | Anyone with the storage device. | Out of HA SOC's reach; document it as the boundary. |
| Logs, diagnostics, entity attributes, WebSocket payloads | Places a secret leaks after being read. HA SOC already masks settings on the wire (`_masked_settings`), redacts audit details at one chokepoint, and reduces diagnostics to counts. | Anyone with the panel, the log viewer, or a diagnostics download. | Keep, and extend to the scanner snippet (item 1.3) and to the new secret store. |

### What "not passed to other integrations" can and cannot mean

Inside the Core process the boundary cannot be enforced, only respected. Three things follow:

1. HA SOC must be the model citizen. Today it stringifies every other integration's `entry.data` and `entry.options` (passwords included) into a search haystack in two places: `peripherals.py:70` and `entity_remap.py:488`. Nothing is persisted or returned, but the pattern is exactly the one the owner is worried about, and a scanner rule written to catch it in other integrations would flag HA SOC. Item SEC-4 narrows both to an allowlist of host and device keys.
2. The tool should detect the extraction patterns it cannot prevent: an integration that enumerates config entries of other domains, opens files under `.storage/`, reads `secrets.yaml`, or reaches into another domain's `hass.data`. Item SEC-5 adds those scanner rules, and the misconfiguration sweep gains checks for the add-ons that map the config directory (SEC-7).
3. Claims must match the mechanism. "Encrypted at rest" is only true where the key lives on the other side of a boundary the attacker does not already hold. A key file next to the ciphertext in `.storage` is obfuscation and must be described as such in the docstring, the README, and the Settings tab.

### The design

**SEC-1  A dedicated secret store.** New module `secrets_store.py`: `HaSocSecretStore` wraps `Store[dict[str, str]](hass, 1, "ha_soc.secrets", private=True, atomic_writes=True)`. It holds exactly the values behind `SECRET_SETTING_KEYS` plus the Probe pairing secret; nothing else. `SettingsData` loses the four `*_api_key`/`*_token` value fields and keeps only derived booleans (`nvd_api_key_set` and so on) that the frontend already consumes. Access is through `await secrets.async_get(key)` and `await secrets.async_set(key, value)`; there is no dict-style access and no property that returns all values. The object is held by the runtime data (any in-process code can still reach it, and the docstring says so), but it is never placed in `hass.data` under its own key, never logged, and its `__repr__` prints only the key names that are set. Migration on first load: move existing values out of `ha_soc.storage`, save the new file, then rewrite the old store without them; log at INFO with key names only.

**SEC-2  No second copy anywhere.** Remove the `entry.options` mirror and `_seed_settings_from_options_once` (D-7 option (a)). One-time migration: if `entry.options` contains any secret key, rewrite the entry with `options={}` and log at INFO. The options flow stays informational. Verify after the change that no code path reads `entry.options` (grep) and add a test that a settings save leaves `entry.options` empty.

**SEC-3  Callers fetch at use time.** `vulns.py`, `github_provenance.py`, and `unifi.py` call `secrets.async_get()` immediately before the request and drop the value when the request completes; no module-level or long-lived attribute holds a key. `_Conn` in `unifi.py` becomes a short-lived object built inside `async_network_overview` and its `__repr__` masks the key. The audit redaction chokepoint (`_redact_secrets_deep`) stays as defense in depth even though secrets no longer flow through `settings`.

**SEC-4  Narrow HA SOC's own cross-integration reads.** `peripherals._assigned_integration` and `entity_remap._find_helper_refs` (the "other" fallback at `:485-488`) stop stringifying whole entries. Define `INTEGRATION_LOCATOR_KEYS = ("host", "hosts", "ip", "ip_address", "address", "url", "base_url", "device", "port", "serial_port", "path", "usb_path", "entity_id", "source", "source_entity_id")` in `const.py` and read only those keys (recursively for nested dicts under those keys). Document in both modules that credentials in other entries are deliberately never read. `unifi.py:284-297` already uses an allowlist; keep it.

**SEC-5  Scanner rules for extraction patterns.** Four new AST rules, each advisory like the rest, each with an evasion note: (a) `hass.config_entries.async_entries()` called with no domain argument, or with a domain that is not the integration's own; (b) `open`, `Path.read_text`, or `os.path.join(hass.config.path(".storage"), ...)` targeting `.storage` or `secrets.yaml`; (c) `hass.data[...]` subscripted with a string literal that is another integration's domain; (d) `Store(...)` constructed with a key that does not start with the integration's own domain. Severity HIGH for (b) and (d), MEDIUM for (a) and (c). HA SOC's own code must pass all four after SEC-4 (add a test that scans `custom_components/ha_soc` itself and asserts zero findings from these rules).

**SEC-6  Optional envelope encryption with the key in the Probe's volume (Supervisor installs only).** Because the Probe's `/data` is a real boundary from Core's `.storage`, a key held there and delivered on the poll channel lets Core keep only ciphertext on disk. Design: the Probe generates a 32-byte key once (`/data/ha_soc_vault_key`, 0o600) and includes it in every authenticated `ingest_probe_result` call; Core keeps it in memory only, encrypts the secret store's values with AES-GCM (the `cryptography` package is already a core dependency), and refuses to decrypt until the Probe has delivered the key after a restart. What it defends: a copied `.storage` directory or an unencrypted backup of the config directory alone no longer yields the API keys. What it does not defend, and the README must say: a hostile integration in Core (it can read the decrypted values from memory), root on the host (both volumes), a full backup (both volumes are in it, so backup encryption remains the control there). Trade-offs: the Network tab and the NVD and GitHub lookups are unavailable until the Probe has reported after a restart (typically seconds; up to one poll interval), and on Core or Container installs the option is not offered and the store stays plaintext-private. Ship as an owner-only opt-in setting labeled "Keep HA SOC's API keys encrypted with a key held by the Probe add-on", with the two limitations printed next to it.

**SEC-7  Detect what widens the boundary.** Misconfiguration checks: `secrets.yaml` or `.storage` readable by others (mode wider than 0o600 and 0o700, LOW, with the exact `chmod` in the summary); any add-on that maps `config` read-write or `homeassistant_config` (SSH, Samba, File editor, Studio Code Server), listed by name with severity HIGH when the add-on also has `host_network` or published ports (sprint 7.1 carries the general inventory; this check ships in sprint 1 because it is the direct answer to "who can read the secret store"); backup protection off for any configured location (from `.storage/backup`: `config.create_backup.password` and each `config.agents[].protected`; MEDIUM, values never read); Samba share of the config directory without a password or with guest access (HIGH, from the add-on's options keys, values never read).

Tests: `test_secret_store_is_private_and_separate`, `test_settings_never_contain_secret_values`, `test_entry_options_stay_empty`, `test_unifi_conn_repr_masks_key`, `test_peripherals_reads_only_locator_keys`, `test_entity_remap_reads_only_locator_keys`, `test_scanner_extraction_rules`, `test_ha_soc_passes_its_own_extraction_rules`, `test_vault_key_roundtrip` (SEC-6), `test_config_mapping_addons_flagged` (SEC-7). Invert `test_audit_files_and_store_are_world_readable` and `test_settings_set_copies_raw_secret_into_entry_options` from the verification file as part of SEC-1 and SEC-2.

Order inside sprint 1: SEC-1, SEC-2, SEC-3, SEC-4, then 1.3 to 1.8, then SEC-5, SEC-7, SEC-6 last (it depends on the Probe authentication from item 0.1 and on the add-on changes from sprint 2, so it may slip to sprint 2 without blocking anything).

## 3. Work items, sprint 0 through 2

Each item: what to change, where, acceptance, tests. File paths are relative to the repository root; `probe run` means `ha_soc_probe/rootfs/etc/services.d/ha_soc_probe_firewall/run` unless the scanner service is named.

### Sprint 0  Restore the claims (hotfix release)

#### 0.1  Authenticate the Probe's callbacks  (AUTH-1, High, Decision D-1 partial)

Files: `custom_components/ha_soc/probe.py`, `custom_components/ha_soc/firewall.py`, `custom_components/ha_soc/detections.py` (new rule), `README.md`, `ha_soc_probe/DOCS.md`.

Change:

- In `probe.py`, add `async def _async_supervisor_user_id(hass) -> str | None` that returns the Supervisor system user id. Preferred source: `hass.data[DATA_CONFIG_STORE].data.hassio_user` where `DATA_CONFIG_STORE` is imported from `homeassistant.components.hassio.const` inside a `try` (it is internal). Fallback: iterate `await hass.auth.async_get_users()` and return the id of the user with `system_generated is True` and `name == HASSIO_USER_NAME` (`homeassistant.components.hassio.const.HASSIO_USER_NAME`, value `Supervisor`). Cache the id on the store's runtime after first resolution.
- In both handlers, before anything else: `if call.context.user_id is None or call.context.user_id != supervisor_id:` reject. Rejection means: log at WARNING once per caller per 10 minutes (not per call), write an audit record `probe_auth_rejected` with `detail={"service": ..., "caller_user_id": call.context.user_id, "reason": "not_supervisor" | "bad_secret" | "no_secret"}`, and return (`{"action": "none"}` for the poll).
- In `firewall.async_verify_or_pin_secret`: remove the "nothing pinned and nothing presented returns True" branch; a missing secret is a rejection. Compare with `hmac.compare_digest(presented, pinned)`. Pinning happens only after the Supervisor-context check passed.
- On a non-Supervisor install (`is_hassio(hass)` false), do not register the services at all; `async_unregister_probe_service` must tolerate that.
- New detection rule `probe_auth_rejected` (HIGH, one detection per `(caller_user_id, hour)`), fed from the audit category above.
- Docs: replace the trust-on-first-use paragraph in the README and `DOCS.md` with the Supervisor-context description; keep the pairing reset and describe the secret as defense in depth.

Acceptance: a read-only user's call is rejected and produces the audit record and detection; an automation (no user context) is rejected; a call whose context is the Supervisor user and whose secret matches (or pins, on first contact) succeeds; the services are absent on a Core install.

Tests: invert `test_probe_ingest_accepts_unauthenticated_call_before_pinning` and `test_probe_poll_lets_first_caller_pin_and_read_pending_rules` in `tests/test_review_verification.py` (they now assert rejection); add `test_probe_requires_supervisor_context`, `test_probe_rejection_is_audited_and_detected`, `test_probe_services_absent_on_core_install`, and update `tests/test_probe.py` and `tests/test_firewall_addon_protocol.py`, which currently call the services with no secret and no Supervisor context, to use a fixture that creates the Supervisor system user and passes its context.

#### 0.2  Anchor the audit chain across retention  (AUD-1, High)

Files: `custom_components/ha_soc/audit.py`, `custom_components/ha_soc/frontend/src/views/audit-view.ts`, `README.md`.

Change:

- `_sync_apply_retention`: before unlinking a day file, read its last non-empty line, parse `seq` and `hash`, and keep the highest `seq` seen among deleted files. After the loop, if anything was deleted, write the anchor into `chain_head.json` as `"anchor": {"seq": N, "hash": H, "expired_through": "YYYY-MM-DD", "expired_at": iso}` alongside `prev_hash` and `seq`. `_sync_write_chain_head` must preserve an existing anchor when it rewrites the head after a flush.
- `_sync_verify_chain`: read the anchor; start `prev_hash` at `anchor.hash` and expect the first surviving record's `prev_hash` to equal it and its `seq` to equal `anchor.seq + 1`; report `verified_from_seq` (1 when no anchor) and `expired_through`. A surviving record with `seq <= anchor.seq` is `reason: anchor_inconsistent`.
- `chain_head.json` is rewritten atomically today (`tmp` plus `os.replace`); keep that.
- Audit view: render "Verified from record N; records before D expired under retention" instead of a bare OK.

Acceptance: a healthy log that has had retention applied verifies `ok: True` with `verified_from_seq > 1`; editing any surviving record still fails with `hash_mismatch`; deleting the newest file still fails with `tail_truncated`.

Tests: invert `test_retention_breaks_chain_verification_on_healthy_log`; add `test_tamper_after_anchor_detected`, `test_anchor_survives_flush_rewrite_of_head`.

#### 0.3  One firewall test at a time  (FW-1, High)

Files: `custom_components/ha_soc/firewall.py`, probe run, `custom_components/ha_soc/frontend/src/views/scanner-view.ts`, `README.md`, `ha_soc_probe/DOCS.md`.

Change:

- `async_propose_test`: refuse with `test_pending_unreported` whenever `fw["pending"]` is not `None`, whatever its status. Only `async_report_from_addon` (or the D-5 owner discard) clears `pending`.
- `_lazily_expire_if_stale`: unchanged in effect (display only), but the status string it sets is `expired_unreported` so the panel can say "the add-on has not confirmed the revert yet".
- `async_report_from_addon`: when the add-on reports a resolution for a test id that matches `pending`, archive as today. When it reports `current_test_id` empty and `pending` is `expired_unreported`, archive `pending` as `reverted` with `resolved_by: "addon_timer"` (the add-on's report of an empty current test after the window is the evidence the timer ran).
- Probe run, `apply` branch: if `CURRENT_TEST_FILE` is non-empty and its resolved marker is absent, do not apply; log "refusing to apply test B while test A is still armed" and continue polling. Include `current_test_id` in every poll (already done) so Core never issues `apply` for a different id while one is held: in `async_next_addon_command`, if `current_test_id` is non-empty and differs from `pending.test_id`, return `{"action": "none", "reason": "addon_holds_other_test"}`.
- Panel: the Test button is disabled with the reason while `pending` exists.

Acceptance: the second proposal is refused; the first test always reaches history; a poll carrying a different `current_test_id` never receives `apply`.

Tests: invert `test_second_proposal_overwrites_unreported_expired_test`; add `test_poll_with_other_test_id_gets_none`, `test_unreported_expired_test_archives_on_empty_poll`; add-on: a shell test (bats or the existing fixture approach) that a non-empty `CURRENT_TEST_FILE` without a marker makes `apply` a no-op.

#### 0.4  Make Entity ReMap apply reachable and confirmed  (UI-1, REMAP-1 part, High)

Files: `custom_components/ha_soc/frontend/src/data/ha-soc-ws.ts`, `custom_components/ha_soc/frontend/src/views/entity-remap-view.ts`, `custom_components/ha_soc/websocket_api.py`, rebuild `frontend/dist/ha-soc-panel.js`.

Change:

- `applyEntityRemap(hass, oldId, newId, backupAcknowledged: boolean)` sends `backup_acknowledged`.
- The view gets the same acknowledgement checkbox and consequence copy the firewall card has (`scanner-view.ts` near the `_fwBackupAck` checkbox). The copy states exactly which files are backed up (the three YAML files) and which are not yet (storage dashboards and helper entries, until item 1.9 lands), that comments and formatting in YAML files do not survive, and that automations, scripts, and scenes reload after the write.
- `_onApply` gets a `catch` that stores the error message into a visible state; the server's error message (`invalid_format`, `backup_not_acknowledged`, or a per-item error list) is rendered, never swallowed.
- Rebuild the bundle and commit it in the same change.

Acceptance: apply works from the panel; a rejected apply shows the message; the checkbox is required.

Tests: `test_entity_remap_client_payload_matches_schema` (Decision D-17 safe default: a Python test that extracts the `ha_soc/entity_remap/apply` payload keys from `ha-soc-ws.ts` with a regex and asserts every `vol.Required` key of the handler's schema is present). Apply the same contract test to every command in `ha-soc-ws.ts` while writing it; it is cheap and it is the class of bug that shipped.

#### 0.5  Tell the truth about the Probe's rating, socket, and privileges  (FW-4 documentation half, High, D-2 recorded)

Files: `README.md`, `ha_soc_probe/config.yaml`, `ha_soc_probe/DOCS.md`, probe run, `custom_components/ha_soc/const.py` (comment near `HA_SOC_RULES_CHAIN`).

Change: state that with `docker_api: true` the Supervisor rates the add-on 1 regardless of anything else (`rating_security` sets `rating = 1` when `access_docker_api` or `full_access` is set, verified against Supervisor commit `c5a5477`); that this is a deliberate choice, because the project wants one companion that carries every host-level capability the SOC needs rather than several partially-privileged ones; and that with Protection Mode on the Docker socket is not mounted at all (the Supervisor mounts it only when `not protected and access_docker_api`), rather than "read-only". Replace the "-1" language everywhere. Add a privilege ledger table to `DOCS.md` and the README with one row per `config.yaml` grant (`host_network`, `NET_ADMIN`, `docker_api`, `homeassistant_api`, and Protection Mode off) stating the feature that needs it, what the add-on does with it, what stops working without it, and how the add-on limits its use (no listening sockets, local input validation, chain-scoped iptables writes, container-name allowlist for Docker calls).

Acceptance: no remaining occurrence of "one point" or "-1" describing the rating; the ledger exists and every row is true of the shipped code.

Tests: none (documentation). Optional: a test that recomputes the rating from `config.yaml` with the `rating_security` algorithm and asserts the README's stated number, so a future privilege change cannot silently drift the docs.

#### 0.6  Run the suite in CI, pin actions, restrict token  (CI-1, Medium)

Files: `.github/workflows/validate.yml`, `.github/workflows/release.yml`, new `.github/workflows/test.yml` (or a job in validate).

Change:

- Add a pytest job: Python 3.13, `pip install pytest-homeassistant-custom-component==<pinned> home-assistant-frontend==<the version pinned by that core> aiousbwatcher pyserial pyudev`, then `pytest tests/ -q`. Pin the harness version explicitly and record the core version it brings in the README's Development section. (Decision D-16 decides whether a second, minimum-version job is added.)
- Add a bundle job: `cd custom_components/ha_soc/frontend && npm ci && npm run build && git diff --exit-code dist/`, so a committed bundle that does not match the source fails.
- Pin `actions/checkout`, `hacs/action`, and `home-assistant/actions/hassfest` by commit SHA with the tag in a comment.
- Add `permissions: contents: read` at the top of `validate.yml` (and the test workflow). `release.yml` keeps `contents: write`.
- Make the release workflow run the test job before creating the release (or have `release.sh` remain the only path that runs tests, and say so in the README).

Acceptance: a pull request with a failing test cannot merge; a bundle drift fails CI.

#### 0.7  Ship

`scripts/release.sh` (no `--skip-tests`). CHANGELOG entry for the add-on. GitHub Release notes list the five behavior changes above in plain language, including that the Probe now requires Supervisor-originated calls and that operators on Core or Container installs will no longer see the two services.

### Sprint 1  The integration's own data

#### 1.1  Private store and audit files  (DATA-1, Medium, D-8 recorded)

Superseded by SEC-1 for the settings and secret stores. The audit half stays here: in `audit.py`, create the directory with `os.makedirs(path, mode=0o700, exist_ok=True)` and `os.chmod(path, 0o700)` on existing directories; open day files via `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)` wrapped in `os.fdopen`; write `chain_head.json.tmp` the same way; `os.chmod` existing files to 0o600 once at startup (one-time migration, logged at INFO). Also pass `private=True, atomic_writes=True` on `HaSocStore` itself, since findings, baselines, and firewall history are sensitive even without the secrets.

Acceptance: on a real filesystem run, every file under `.storage/ha_soc_audit/` is 0o600 and the directory 0o700; both stores report `_private is True`.

Tests: invert `test_audit_files_and_store_are_world_readable`.

#### 1.2  Stop copying secrets into `entry.options`  (DATA-2, Medium, D-7 recorded)

Superseded by SEC-2 (remove the mirror entirely, with the one-time scrub). Invert `test_settings_set_copies_raw_secret_into_entry_options` there.

#### 1.3  Mask the credential in scanner snippets  (SCAN-2, High)

Files: `custom_components/ha_soc/scanner.py`, `custom_components/ha_soc/frontend/src/views/scanner-view.ts`.

Change: for `hardcoded_credential`, the stored `snippet` becomes the assignment target and a masked value (`token = "[redacted, 40 chars]"`); never the literal. `export_ghsa` keeps the masked form. The export button shows a confirmation naming the snippet and the target integration before copying.

Acceptance: no stored finding, WS response, or export contains the matched literal.

Tests: `test_scanner_snippet_masks_credential_value`; extend `tests/test_scanner_hardcoded_credential.py`.

#### 1.4  Put HA SOC's own actions in the chain  (AUD-3, Medium, Decision D-14 safe default)

Files: `custom_components/ha_soc/websocket_api.py`, `custom_components/ha_soc/firewall.py`, `custom_components/ha_soc/store.py`.

Change:

- `ws_detections_set_status`: record `status_by`, `status_at`, and `previous_status` on the detection; audit `detection_status_changed` with detection id, rule id, old and new status.
- `ws_permissions_dashboard_flags_set` and `ws_permissions_sidebar_push`: audit `lovelace_change` with the flags or hidden paths and the target user.
- `ws_logs_container`, `ws_logs_fault`, `ws_users_detail`: audit `privileged_read` with the target (`core`, `supervisor`, `host`, add-on slug, or user id). (D-14 safe default: these three only.)
- `async_report_from_addon`: audit `firewall_resolved` with `actor_source: "addon"`, test id, status, and the reported rule count when a test moves to history.
- `ws_watchdog_set` already audits; keep.

Acceptance: each action yields exactly one chain record with the fields above.

Tests: `test_audit_covers_soc_own_actions` (one assertion per command).

#### 1.5  Detect a wiped or reset chain  (AUD-2, Medium)

Files: `custom_components/ha_soc/audit.py`, `custom_components/ha_soc/store.py`, `custom_components/ha_soc/repairs.py`.

Change: after every successful `_sync_flush`, copy `{"seq", "hash", "at"}` into `store.data["audit_head"]` (on the event loop, after the executor job returns) and schedule a save. On `async_start`, compare the on-disk head with the store copy: if the store copy exists and the on-disk head is absent or behind it, write an audit record `audit_chain_reset` (with both heads in `detail`), raise a Repairs issue `audit_chain_reset`, and continue with a fresh chain that carries the store copy's hash as `prev_hash` of its first record (so the discontinuity is itself chained). `_sync_verify_chain` reports `reason: chain_reset` when the store copy is ahead of the on-disk head.

Acceptance: deleting `.storage/ha_soc_audit/` and restarting yields the record, the repair, and `chain_reset` on verify.

Tests: `test_audit_directory_wipe_is_detected`, `test_chain_reset_is_itself_chained`.

#### 1.6  Deeper service-data redaction  (AUD-4, Low)

Files: `custom_components/ha_soc/audit.py`.

Change: `_redact_service_data` walks nested dicts and lists; the key set becomes `password, token, code, api_key, apikey, secret, pin, passphrase, access_token, refresh_token, client_secret, authorization`, matched case-insensitively on the key; `message` and `title` are redacted for `notify`, `tts`, and `persistent_notification`; `payload` is redacted for `mqtt.publish`. Keep the redaction inside `async_log` as the single chokepoint.

Tests: `test_service_data_redaction_is_deep`.

#### 1.7  Flush high-value records immediately  (AUD-5, Low)

Files: `custom_components/ha_soc/audit.py`.

Change: `async_log(..., flush=True)` for the categories `user_added`, `user_updated`, `user_removed`, `soc_config_change`, `firewall_*`, `detection_status_changed`, `probe_auth_rejected`, `audit_chain_reset`, `privileged_read`; the flag schedules `_async_flush` as a task rather than waiting for the 30 s timer. Document that the `http.ban` logger must remain at WARNING or lower for `login_fail` to be captured, and add a health check (`audit_ban_logger_silenced`, LOW) that reads `logging.getLogger("homeassistant.components.http.ban").getEffectiveLevel()`.

Tests: `test_high_value_records_flush_immediately`, `test_ban_logger_level_check`.

#### 1.8  Bound add-on-supplied state  (DATA-3, Low)

Files: `custom_components/ha_soc/resource_watchdog.py`, `custom_components/ha_soc/probe.py`.

Change: `resource_limit_state` schema becomes `{vol.Match(r"^[a-z0-9][a-z0-9_-]{0,63}$"): {"status": vol.In(["applied","failed","denied"]), vol.Optional("detail"): vol.All(str, vol.Length(max=200))}}` with at most 64 keys; `async_store_limit_report` drops slugs not present in `hard_limits`.

Tests: `test_limit_report_is_bounded`.

#### 1.9  Back up dashboards and helpers before remap  (REMAP-1, Medium, Decision D-13 safe default)

Files: `custom_components/ha_soc/entity_remap.py`, `custom_components/ha_soc/websocket_api.py`, `entity-remap-view.ts`.

Change: before `config.async_save(new_config)`, write the previous config to `.storage/ha_soc_remap/<url_path or default>-<stamp>.json` (0o600); before `async_update_entry`, write the previous options to `.storage/ha_soc_remap/<entry_id>-<stamp>.json`; return the backup paths in the result and show them. Prune backups older than 30 days at the start of each apply. With D-13 safe default (b): before touching a YAML file, scan its text for `!include` or `!secret`; if present, mark every item in that file `editable: False, reason: "contains !include or !secret; manual edit required"` and skip it. Verified behavior that motivates this: `load_yaml(path)` without a `Secrets` object raises `HomeAssistantError("Secrets not supported in this YAML file")` on `!secret`, so today such a file fails loudly per item (safe but unexplained), while `!include` is resolved at load and would be written back inlined (destructive). Extend `_contains_exact` to check dict keys and report a key-position hit as detect-only. Read `entry.data` as well as `entry.options` in `_find_helper_refs`, `_apply_helper_fix`, and `async_scan_broken_references`, and move the `continue` so the substring fallback still runs when no structural field matched (subject to SEC-4's allowlist). Reload once per domain for scripts and scenes after the loop; keep the per-automation `automation.reload` with `id`, which core's schema accepts (`vol.Schema({vol.Optional(CONF_ID): str})`, verified) and which is the cheaper call.

Tests: `test_remap_backs_up_dashboard_and_helper`, `test_remap_refuses_secret_tagged_yaml`, `test_remap_detects_dict_key_reference`, `test_remap_reads_entry_data`.

### Sprint 2  The Probe contract

#### 2.1  Owner-only firewall, in full  (FW-3, Medium, D-4 and D-5 recorded)

Files: `custom_components/ha_soc/websocket_api.py`, `custom_components/ha_soc/firewall.py`, `custom_components/ha_soc/frontend/src/views/scanner-view.ts`, `README.md`.

Change: `ws_firewall_status`, `ws_firewall_test`, `ws_firewall_confirm`, `ws_firewall_cancel`, and the existing `ws_firewall_reset_pairing` are all `@require_owner`. Add `ws_firewall_discard_pending` (`@require_owner`): archives the current `pending` record into history with `status: discarded_unreported`, `resolved_by: <owner id>`, clears `pending`, and audit-logs `firewall_pending_discarded`; the panel offers it only when `pending` exists and its countdown has lapsed. Nothing ever unblocks automatically. The Firewall Rules card renders for the owner only; a non-owner admin sees a one-line "Owner only" note in its place, the same treatment Settings uses. The README's access-control section lists the firewall as owner-only regardless of `access_level`.

Acceptance: every firewall command returns `unauthorized` for a non-owner admin under `owner_and_admins`; discard works only for the owner and always leaves a history entry and an audit record.

Tests: `test_firewall_all_commands_owner_only`, `test_firewall_discard_pending_is_owner_only_and_audited`.

#### 2.2  Validate the cap slug end to end  (FW-3, Medium)

Files: `custom_components/ha_soc/websocket_api.py`, `custom_components/ha_soc/resource_watchdog.py`, probe run.

Change: `override.slug` and `hard_limit.slug` use `vol.All(str, vol.Match(r"^[a-z0-9][a-z0-9_-]{0,63}$"))` and must be present in the Supervisor's installed add-on list (reuse `logs.py`'s `_addons_by_slug` pattern; on a non-Supervisor install reject with `not_supervisor`). In the add-on, quote the `jq` iteration (`while IFS= read -r slug; do ...; done < <(jq -r 'keys[]')`) and validate the slug with the same regex before building the Docker URL.

Tests: `test_watchdog_slug_validation`; add-on fixture test for the regex.

#### 2.3  Chain-scoped revert and a checked backup  (FW-2, Medium)

Files: probe run, `ha_soc_probe/DOCS.md`, `README.md`.

Change:

- Backup: `iptables-save -t filter > "$backup"` for the full-table file (kept for manual recovery), plus a chain-only snapshot `iptables -S HA_SOC_RULES > "$chain_backup"`. Check both exit statuses; on failure log, report the test as `reverted` with reason `backup_failed`, and do not apply.
- Revert: `iptables -F HA_SOC_RULES` then replay the chain snapshot lines (each `-A HA_SOC_RULES ...` line becomes `iptables -A ...`; the `-N` line is skipped). Never `iptables-restore` the whole table during a revert.
- `ensure_chain`: keep the `INPUT` jump insertion; document that the jump sits at position 1 of `INPUT`, ahead of Docker's and the host's rules, and why (a deny that sits below an accept is not a deny). Update the README's "never the host's raw INPUT chain" sentence to say exactly this.
- Remove the jump and the chain on a clean uninstall if the Supervisor offers a hook (UNVERIFIED whether it does; if not, document that an empty chain and one jump remain).

Tests: add-on fixture tests for the revert replay parser and the backup failure path.

#### 2.4  IPv6 parity  (FW-2, Medium, D-3 recorded)

Files: `custom_components/ha_soc/firewall.py`, `custom_components/ha_soc/const.py`, probe run, `scanner-view.ts`, `README.md`, `ha_soc_probe/DOCS.md`.

Change:

- Rule model: `RULE_SCHEMA` gains `family: vol.In(["4", "6", "both"])`. When `source` is set, `family` is derived from the address family of the source and a mismatching explicit value is rejected; when `source` is absent, the default is `both`. `known_rules` entries carry `family` as reported by the add-on.
- Add-on apply: a rule with family `4` is written with `iptables`, `6` with `ip6tables`, `both` with both, into a chain named `HA_SOC_RULES` in each table. `ensure_chain` creates and jumps to the chain in both tables. Backups and chain snapshots are taken for both tables before any apply (item 2.3), and the revert replays both. A test is applied atomically across families: if any rule fails in either table, both tables are restored and the test reports `reverted` with the failing rule and family in the reason.
- Add-on report: `known_rules` is the union of both chains with `family` set per entry; `ipv6_supported: true|false` is reported once per cycle based on `ip6tables -S` succeeding. When it is false (a host kernel without `ip6_tables`), Core marks every `both` and `6` rule `partially_applied` and the card shows "IPv6 rules not applied: the host kernel does not support ip6tables", never a silent IPv4-only success. This is the only surviving use of the D-3 label.
- Port scan correlation: the Scanner tab's port table already reports IPv6 listeners; each row gains a "covered by rule" indicator computed per family so an operator can see that a deny on 22 covers both the `0.0.0.0` and `::` listeners.
- Docs: the README's firewall section states that rules are dual-stack by default, how `source` picks a family, and what `ipv6_supported: false` means.

Acceptance: a `deny tcp 22` with no source produces one rule in each table; a rule with an IPv6 source lands only in `ip6tables`; a failure in `ip6tables` reverts both; a host reporting `ipv6_supported: false` is shown as partial, not clean.

Tests: Core: `test_rule_family_derivation`, `test_partial_ipv6_is_visible`; add-on fixture tests for dual-table apply, atomic failure, and revert replay in both tables. D-21 facts needed first: `ip6tables` presence and kernel support on the host, and whether the Probe's `iptables` binary uses the same backend (legacy or nft) as Docker on the host.

#### 2.5  Harden the single add-on  (FW-4, High, D-2 recorded)

Files: `ha_soc_probe/apparmor.txt` (new), `ha_soc_probe/config.yaml`, `ha_soc_probe/Dockerfile`, both service `run` scripts, `ha_soc_probe/DOCS.md`.

Change, in order of value:

1. Custom AppArmor profile (`apparmor.txt`, loaded by the Supervisor when present): allow the s6 tree, bashio, `curl` to `http://supervisor`, read of `/proc/net/*`, `/data` read-write, `iptables*` and `ip*` execution with `CAP_NET_ADMIN`, and the Docker socket; deny everything else, including writes outside `/data` and `/tmp`. Test on the real Supervisor (D-21) with `ha addons info` showing `apparmor: profile`.
2. Run the port-scanner service as `nobody` (the `s6-setuidgid` re-exec already sketched in the scanner `run`), after confirming on the real install that `/run/s6/container_environment/*` and `/data/options.json` are readable by that uid; keep the firewall service as root with the capability.
3. Pin the base image by digest in the `Dockerfile` (`ghcr.io/home-assistant/base:3.23@sha256:<digest>` from the published image), and record the digest and date in `DOCS.md`.
4. Local input validation in the add-on for everything Core sends (rule fields, slugs, `window_seconds` range) so a compromised Core cannot turn the add-on into an arbitrary iptables or Docker client.
5. Confirm the add-on opens no listening socket (`ss -ltnp` in D-21) and state it in the ledger.
6. Investigate image signing through the official add-on builder so `signed: true` appears in the store (UNVERIFIED which mechanism third-party add-ons can use today; record the answer either way).

Acceptance: `ha addons info` shows `apparmor: profile`; the scanner service runs unprivileged; the image reference is immutable; every input from Core is validated locally.

#### 2.6  Stopped-mid-test honesty  (FW-5, Low)

Files: `ha_soc_probe/rootfs/etc/services.d/ha_soc_probe_firewall/finish`, `README.md`.

Change: `finish` runs the same startup recovery (revert an unresolved test) before exiting, so a deliberate stop reverts immediately; the README states that a host reboot with the add-on disabled leaves the pre-test ruleset only if the timer or `finish` ran, and that the next start reverts otherwise.

Tests: add-on fixture test that `finish` reverts an unresolved test.

#### 2.7  Real-Supervisor verification pass  (D-21 recorded)

Input: the output of `ha_soc_verify_supervisor.sh` pasted by the owner. Record in `ha_soc_probe/DOCS.md`, with the Supervisor and OS versions from the output: the observed rating; the Docker socket path and whether `/var/run` is a symlink to `/run`; the iptables backend (legacy or nft) inside the add-on versus the one Docker on the host uses, and `ip6tables` support; the secret file mode; the AppArmor profile in effect; the container's capability set; that the add-on holds no listening socket. Then remove the corresponding UNVERIFIED labels in code and docs and clear the entries in section 6.2. If the backends differ (the add-on's `iptables` writes legacy tables while the host uses nft, or the reverse), the firewall feature must switch the add-on to the host's backend before item 2.4 ships; both variants are available in Alpine's `iptables` package.

## 4. Work items, sprint 3 and 4

### Sprint 3  Detections and scores

#### 3.0  Tunable detection thresholds with secure defaults  (D-9 recorded)

Files: `custom_components/ha_soc/const.py`, `store.py`, `detections.py`, `risk.py`, `websocket_api.py`, `frontend/src/views/settings-view.ts`, `README.md`.

Change: a `detection_thresholds` dict in settings, one sub-dict per rule, every field validated with a `vol.Range` and every default set to the most sensitive value that does not alert on ordinary same-network activity ("most secure" means the setting that misses the fewest attacks; the cost is more alerts, which the Settings tab says next to the control). Owner-only to change, audited as `soc_config_change` with a per-field diff, and a "Reset to secure defaults" button. The table below is the shipped parameter set; ranges are inclusive.

| Rule | Parameter | Secure default | Range | Current hard-coded value |
| --- | --- | --- | --- | --- |
| brute_force_ip | failures | 5 | 3 to 100 | 10 |
| brute_force_ip | window_minutes | 15 | 5 to 120 | 15 |
| success_after_failures | failures | 3 | 2 to 50 | 5 |
| success_after_failures | window_minutes | 30 | 5 to 240 | 30 |
| success_after_failures | require_new_token | true | bool | not implemented |
| success_after_failures | derate_shared_ip | true | bool | not implemented |
| new_ip_login | ipv4_prefix | 24 | 16 to 32 | 24 |
| new_ip_login | ipv6_prefix | 64 | 32 to 128 | 24 (defect) |
| new_ip_login | baseline_days_required | 3 | 1 to 30 | 1 pass |
| new_ip_login | prefix_expiry_days | 90 | 30 to 730 | never |
| new_ip_login | learning_days | 7 | 1 to 90 | 14 |
| off_hours_anomaly | quiet_start_hour | 23 | 0 to 23 | 23 |
| off_hours_anomaly | quiet_end_hour | 6 | 0 to 23 | 6 |
| off_hours_anomaly | burst_threshold | 5 | 2 to 100 | 10 |
| off_hours_anomaly | ratio_threshold | 0.01 | 0.001 to 0.2 | 0.01 |
| off_hours_anomaly | learning_days | 7 | 1 to 90 | 14 |
| dormant_revival | dormant_days | 30 | 7 to 365 | 60 |
| dormant_revival | min_account_age_days | 60 | 7 to 365 | 90 |
| mass_entity_burst | calls | 20 | 5 to 500 | 30 |
| mass_entity_burst | distinct_entities | 10 | 2 to 200 | 10 |
| mass_entity_burst | window_minutes | 5 | 1 to 60 | 5 |
| token_minting_anomaly | tokens | 2 | 2 to 20 | 3 |
| token_minting_anomaly | window_hours | 24 | 1 to 168 | 24 |
| disabled_user_activity | risk_cap_points | 40 | 10 to 100 | uncapped |
| privilege_escalation | risk_cap_points | 24 | 8 to 100 | uncapped |

`risk_learning_period_days` is replaced by the two per-rule `learning_days` fields (a migration copies its value into both). Every rule reads its values through one helper `thresholds(store, rule)` that merges stored values over the secure defaults, so a missing key never means "off".

Acceptance: each parameter is changeable from Settings within its range, rejected outside it, audited, and reset by one action; the dashboard's rule inventory shows the effective value next to each rule.

Tests: `test_thresholds_defaults_are_secure` (asserts the table above), `test_thresholds_range_validation`, `test_thresholds_change_is_audited`, `test_reset_to_secure_defaults`, plus each rule's own test reads a non-default value and observes the change.

#### 3.1  Address-family-aware prefixes  (DET-1, High, D-9 recorded)

`detections.py::_network_prefix`: uses `ipv4_prefix` and `ipv6_prefix` from item 3.0 (secure defaults 24 and 64). Test: `test_network_prefix_ipv6` asserts two unrelated global IPv6 addresses yield different prefixes and that two addresses in one `/64` yield the same one.

#### 3.2  Bound `disabled_user_activity`  (DET-2, High)

One detection per `(user, category)` per pass (bucket by pass, not by event hour); `DISABLED_USER_ACTIVITY_CAP = 40` applied with `min` in `risk.py`; also cap `privilege_escalation` at 24. Test: `test_disabled_user_activity_bounded`.

#### 3.3  Detections retention and bulk resolve  (DET-2, AUD-3, Decision D-6 safe default)

`store.py`: `evidence_retention_days` setting (default 365) and a sweep in the periodic analysis that prunes `resolved` and `dismissed` detections and findings older than the period. New command `ha_soc/detections/bulk_set_status` (ids list, status, audited once with the id list). Test: `test_detections_retention`, `test_bulk_resolve_is_audited`.

#### 3.4  Provisional posture  (DET-3, Medium, Decision D-10 safe default)

`risk.py`: each term records `computed_at`; `async_compute_posture` returns `provisional: True` and `missing_terms: [...]` until every term has computed at least once; the dashboard tile shows the badge and the list. Test: `test_posture_provisional_until_complete`.

#### 3.5  Reachable `never_logged_in`, reconciled factors, live learning period  (DET-3)

`never_logged_in` fires for an active, non-system user with at least one credential and no refresh tokens (age from credential creation where available, else "unknown age, never logged in"); after clamping, factors carry `applied_points` so the list sums to the score, and the two uncapped factors get caps; the LLAT bonus is applied before the cap; `risk_learning_period_days` replaces `NEW_IP_LOGIN_MIN_HISTORY_DAYS` and `OFF_HOURS_MIN_HISTORY_DAYS` (or the setting is removed, per D-9). Tests: `test_never_logged_in_fires_for_credentialed_user`, `test_risk_factors_reconcile`, `test_learning_period_setting_is_used`.

#### 3.6  `new_ip_login` without amnesty  (DET-4, D-9 recorded)

Evaluate every `login_ok` since the per-user checkpoint, not only the newest; add a prefix to the baseline only after it has been seen on `baseline_days_required` distinct days; expire baseline entries after `prefix_expiry_days`; do not baseline a prefix in the same pass that flagged it. Test: `test_new_ip_login_no_amnesty`.

#### 3.7  Silent seeding pass for off-hours  (DET-4)

The first pass fills the histogram and sets the checkpoint without emitting; thereafter scale the burst threshold by `span / ANALYSIS_INTERVAL`; use the pass `now` as both the query `until` and the checkpoint to stop double counting. Test: `test_off_hours_first_pass_is_silent`.

#### 3.8  `success_after_failures` on new tokens only  (DET-4, D-9 recorded)

When `require_new_token` is set (secure default), require the `login_ok` to come from the `previous is None` branch (a new token); when `derate_shared_ip` is set, de-rate to HIGH when the IP is shared across users in the window. Test: `test_success_after_failures_not_on_refresh`.

#### 3.9  Closed episodes stay closed  (DET-4)

`_upsert_detection` only bumps `last_seen` when the triggering event's timestamp is newer than the stored `last_seen`; `recurrence_count` counts distinct triggering events. Test: `test_detection_last_seen_is_event_time`.

#### 3.10  Entity exposure and naming  (DET-5, Decision D-19 safe default)

`PostureScoreSensor.extra_state_attributes` returns `grade` only; `UserRiskSensor` sets `_attr_name` from the user id (`Risk <id[:8]>`) so entity ids are distinct; the watchdog preserves an existing detection's `ack`/`resolved` status on re-trip; the privilege-escalation group snapshot is persisted in `user_baselines`. Tests: extend `tests/test_sensor_access.py`; `test_watchdog_preserves_ack`; `test_privilege_escalation_survives_restart`.

#### 3.11  MFA policy documentation line  (MFA-1, Decision D-18 safe default)

Docstring and README state that the policy assesses Home Assistant's own MFA modules only; an instance authenticating through an external proxy should keep `audit_only`.

### Sprint 4  Honest coverage and hardening

#### 4.1  Startup grace and protected confirmations  (HLTH-1, High)

`health.py`: the full sweep runs only after `_on_started` and `STARTUP_GRACE`; `_async_resolve_missing` skips `confirmed` as well as `dismissed`; each hygiene helper returns a tri-state (`evaluated`, `empty`, `could_not_evaluate`) and `could_not_evaluate` leaves findings untouched. Add `automation`, `script`, `person`, `group`, and `alert` to `after_dependencies` in `manifest.json`. Tests: `test_sweep_respects_startup_grace`, `test_confirmed_survives_empty_pass`, `test_could_not_evaluate_leaves_findings`.

#### 4.2  Proxy trust check  (HLTH-2, High)

`_check_http_hardening`: HIGH finding when `use_x_forwarded_for` is truthy and `trusted_proxies` is absent, contains `0.0.0.0/0` or `::/0`, or contains any network with an IPv4 prefix shorter than 24 or an IPv6 prefix shorter than 64 (reuse the `ipaddress` logic already in the file); a truthy `use_x_forwarded_for` with a narrow list quiets the `no_ssl` LOW finding with a note. Also add `trusted_users` mapping a network to an admin or the owner as HIGH. Tests: `test_proxy_trust_check`, `test_trusted_users_admin_mapping`.

#### 4.3  Supervisor checks fail closed  (HLTH-3)

A missing key in the add-on info yields an INFO `could_not_evaluate` finding naming the key; never silence. Test: `test_supervisor_checks_fail_closed`.

#### 4.4  Severity recalibration  (HLTH-3, Decision D-11 safe default)

Apply the D-11 values; `_new_finding` sets `status: "new"`; dismissing a finding deletes its Repairs issue; item lists in `detail` are capped at 100 with `total_count`; Repairs severity for an unknown string is WARNING. Tests: update existing health tests; `test_new_finding_has_status`; `test_dismiss_removes_repair`.

#### 4.5  Missing security entities alarm  (HLTH-3)

`security_health.py`: enumerate `lock`, `siren`, and `valve` from the entity registry, not only from `hass.states`; an entity with no state object renders `problem: True, reason: "no state (integration not loaded)"`. Test: `test_missing_lock_state_is_a_problem`.

#### 4.6  `action:` inside `data` is not a service  (HLTH-3)

`config_hygiene._walk_service_refs` does not descend into `data`, `data_template`, or `variables` subtrees when looking for `action`/`service` keys. Test: `test_action_key_in_data_is_not_a_service`.

#### 4.7  One YAML load per sweep  (HLTH-3)

Cache `async_hass_config_yaml` for the duration of one sweep and share it across the three checks that load it; log a failed load at WARNING once per sweep, not DEBUG. Also stop setting `resources.loaded = True` from the read-only sweep; call `async_load()` and leave core's flag to core. Test: `test_yaml_loaded_once_per_sweep`.

#### 4.8  Scanner robustness and coverage  (SCAN-1, SCAN-3, High and Medium)

Move the rule loop inside the per-file `try`; make `_dotted_name` iterative; store per-domain coverage `{scanned_files, skipped_oversize, skipped_over_cap, parse_failures, scanned_at}` and render "not scanned" (never "0 findings") for a domain with no coverage record; reconcile findings per domain after each scan (findings absent from the new scan move to `resolved` with `resolved_reason: "not_found_on_rescan"`); order the file list by path but select the cap deterministically by size descending so large modules are not silently skipped; honor `scanner_enabled` in `_on_config_entry_changed`; add `os.system` and `os.popen` to the shell rule and `AnnAssign` to the credential rule; state in the Scanner tab that the rules detect unobfuscated instances only. Tests: `test_scanner_survives_recursion_bomb`, `test_unscanned_domain_is_not_zero`, `test_scanner_reconciles_findings`, `test_install_scan_honors_toggle`.

#### 4.9  NVD disclosure, lock, and paging  (SCAN-4, Decision D-12 safe default)

Docstring, README, and the Settings field say what leaves the instance (manufacturer and model strings) and to whom; a toggle `nvd_lookups_enabled` (default per D-12); an `asyncio.Lock` around `async_run_scan`; page through NVD results before ranking, and treat a vendor-only CPE match as INFO. Tests: `test_cve_pass_respects_toggle`, `test_vuln_scan_is_serialized`.

#### 4.10  GitHub provenance hardening  (GH-1, now Medium)

yarl collapses `..` segments before the request (verified: `URL("https://api.github.com") / "repos" / "../../x/y"` becomes `/x/y`), so a manifest whose repository URL carries `..` can point the owner's token at any GitHub API path on that host (for example `/user/repos`), and the response would be cached in the store. Validate `owner/repo` with `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$` and reject `.` and `..` components before building the path; catch `ValueError` (which covers `JSONDecodeError`) per repository; honor `INTEGRATION_SECURITY_CACHE_TTL_HOURS`; on 403 with `X-RateLimit-Remaining: 0` stop and report `rate_limited`; either produce `custom_source_list` from HACS data or remove the flag. Tests: `test_repo_slug_validation`, `test_github_refresh_survives_bad_json`, `test_github_cache_ttl_honored`.

#### 4.11  UniFi client hardening  (NET-1, NET-2, High and Medium)

`unifi.py::_get`: `allow_redirects=False`, treat 3xx as `UniFiError("unexpected redirect")`; reject a `Content-Length` above 8 MB and read at most 8 MB; wrap `async_network_overview` in one `asyncio.timeout(60)`; allow only `http` and `https` in the configured host and reject userinfo; catch `ValueError` in `_hosts_from_value`; choose the gateway by role field first and name tokens last; `_Conn.__repr__` masks the key; replace `except (UniFiError, Exception)` with the intended narrow handling. Tests: `test_unifi_get_never_follows_redirects`, `test_unifi_body_cap`, `test_unifi_bad_host_in_other_entry_does_not_raise`.

#### 4.12  Frontend truthfulness  (UI-2, UI-3, AUTH-2)

Every view's `_load` has a `catch` that sets a distinct "could not load" state rendered as such (never an empty table); permission toggles roll back on a rejected write and show the server's reason; the password reset uses a masked in-panel field, the server's error is shown, and the result offers "revoke this user's sessions now" (server side: `ws_users_set_password` gains `revoke_sessions: bool`, default true, audited); the three `href` bindings in `network-view.ts` pass through a client-side `http(s)` scheme check; the README's sortable-tables claim is narrowed to the tables that use `sortable.ts`. Tests: contract test from 0.4 extended; frontend smoke tests per D-17.

#### 4.13  Peripherals  (PERIPH-1)

Move `os.path.realpath` into the executor job; anchor the device-path match on a word boundary or compare parsed candidate fields. Test: `test_peripheral_path_prefix_collision`.

#### 4.14  Small items  (HLTH-4, MISC-1)

`repairs.py` imports `TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN` as `users.py` does; `SettingsData` gains `github_token: str | None`; remap backups get a millisecond stamp.

## 5. Work items, sprint 5 through 8 (visibility expansion)

Every new check or signal follows one shape: an entry in a check inventory (id, source, severity, enforcement label, what "could not evaluate" means for it), a positive test, a negative test, and a docstring line naming its obvious false positive. The `LEVEL_*` vocabulary in `const.py` is rendered on every misconfiguration row from sprint 5 on.

### Sprint 5  UI surface

5.1 Provider inventory (`trusted_networks` INFO, `command_line` HIGH, order shown). 5.2 No MFA module configured (MEDIUM). 5.3 Owner without MFA as its own factor and repair (HIGH); admin `local_only=False` without MFA (MEDIUM). 5.4 Refresh-token client baseline per user and a `new_client` detection (MEDIUM). 5.5 Long-lived token rules: created without an interactive session in the prior hour, older than 365 days, never used (MEDIUM). 5.6 `allowlist_external_dirs` containing `/` or the config directory (HIGH); broad `allowlist_external_urls` (MEDIUM). 5.7 "Code that runs in every browser session" inventory: custom panels, `panel_iframe` targets, `extra_module_url`, Lovelace resources, with a change detection between sweeps (MEDIUM on change). 5.8 Webhook triggers with `local_only: false` or ids shorter than 16 characters (MEDIUM). 5.9 Cloud remote UI enabled as posture context (INFO, raises the weight of `no_ssl` and proxy findings). 5.10 `server_host` and `ssl_profile` (LOW). 5.11 IP bans tile from `ip_bans.yaml` (INFO). 5.12 Recorder purge days and exclusions covering security entities (MEDIUM).

### Sprint 6  Integrations

6.1 `requirements` inventory with pin status per integration (unpinned HIGH). 6.2 OSV lookup for pinned requirements, opt-in per D-12 (known-vulnerable HIGH). 6.3 Scanner rule: `requires_auth = False` on a `HomeAssistantView` subclass (HIGH). 6.4 Scanner rules: `.storage` and config-directory writes, `Store(...)` with a foreign key, `os.remove` outside the integration directory (HIGH). 6.5 Scanner rules: computed `importlib.import_module`, `pip` subprocesses, writes into `custom_components/` (HIGH). 6.6 Static egress targets from string literals joined to the `iot_class` inventory (MEDIUM when an `iot_class: local_*` integration has public hostnames). 6.7 Per-integration integrity baseline (directory hash) and a `integration_code_changed` detection when the hash changes without a manifest version change (MEDIUM). 6.8 Attack-surface inventory per integration: services (public API), HTTP routes and WebSocket commands (internal registries, labeled best-effort).

### Sprint 7  Add-ons and the platform

7.1 Add-on Security tab with the full privilege inventory per add-on (`host_network`, `privileged`, `docker_api`, `full_access`, `host_pid`, `host_uts`, `hassio_role`, `auth_api`, `apparmor`, ingress versus published ports, `map` write access to `config` or `ssl`), each with the severity from the review and the D-20 threshold. 7.2 Recomputed Supervisor rating with its factors shown, compared against the Supervisor's own value. 7.3 Repository provenance and image signing per add-on. 7.4 `auto_update`, `watchdog`, `boot`, version currency. 7.5 Supervisor `supported`, `healthy`, version, and the GHSA-gh5m-4m97-c95h rule (Supervisor below 2026.03.2 with any `host_network` add-on, HIGH). 7.6 Any `host_network` add-on with published ports (generalize the SSH check, HIGH). 7.7 Backup age, encryption, and off-box location (MEDIUM). 7.8 OS boot-slot health and last update result (MEDIUM). 7.9 Add-on option keys named like credentials (names only, LOW) and secret-pattern redaction in the Logs tab (LOW).

### Sprint 8  Export and evidence

8.1 Versioned event schema (`schema_version` on every record; a `SCHEMA.md` listing fields per category). 8.2 Exporter per D-15 carrying `seq`, `prev_hash`, `hash` so a receiver can re-verify; TLS with certificate pinning option; backpressure that never blocks the event loop. 8.3 Actor-source filter in the Audit tab and in exports. 8.4 Evidence pack: users and MFA state, access-control settings, chain verification result including anchor and `verified_from_seq`, findings and detections by status, retention settings, export configuration, signed with the chain head; one file per period. 8.5 Map each pack section to the SOC 2 criteria and 800-53 controls listed in the review's section 7.

## 6. Platform facts

### 6.1  Verified, with the version they were checked against

Home Assistant core 2026.2.3:

- `websocket_api/commands.py:272-290`: `call_service` performs no admin check; any authenticated user may call any registered service.
- `helpers/service.py:920-985`: `async_register_admin_service` wraps the handler in `_async_admin_handler`, which checks `is_admin` only when `call.context.user_id` is set; a call with no user context (an automation) passes.
- `helpers/storage.py:238` and `util/file.py:61-62`: `Store(private=False)` is the default and the writer chmods the file 0o644; `auth/auth_store.py:63`, the `homeassistant` auth provider, and both MFA modules pass `private=True, atomic_writes=True`.
- `components/lovelace/websocket.py:130-147`: `lovelace/config` has no admin gate; any authenticated user can read any dashboard's configuration.
- `components/frontend/__init__.py:828-841`: a panel's `require_admin` filters the `get_panels` list only.
- `components/hassio/__init__.py:341-361`: the Supervisor system user is created with `async_create_system_user(HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN])` and its id stored in the hassio config store (`hass.data[DATA_CONFIG_STORE].data.hassio_user`).
- `components/http/ban.py:125-136`: the invalid-auth warning is a preformatted string `"Login attempt or request with invalid authentication from <host> (<addr>). Requested URL: ..."`, which the existing regex parses.
- `auth/__init__.py`: only `user_added`, `user_updated`, and `user_removed` are fired from the auth package; there is no login event, and `last_used_at` is updated only in `auth_store.py:283` on the token grant path.

Supervisor commit `c5a5477` (2026-08-28):

- `apps/utils.py::rating_security`: start 5; AppArmor disabled -1 or custom profile +1; ingress +2, or no host network and no ports +2, or `auth_api` +1; signed +1; any of BPF, CHECKPOINT_RESTORE, DAC_READ_SEARCH, NET_ADMIN, NET_RAW, PERFMON, SYS_ADMIN, SYS_MODULE, SYS_PTRACE, SYS_RAWIO, or kernel modules -1; `hassio_role` manager -1 or admin -2; `host_network` -1; `host_pid` -2; `host_uts` with SYS_ADMIN -1; then `docker_api` or `full_access` sets the rating to 1; clamp to 1..8.
- `docker/app.py:620-621`: the Docker socket is mounted only when `not protected and access_docker_api`; `docker/const.py:169-174`: the mount is `/run/docker.sock` with `read_only=True` (a bind-mount flag; socket I/O is unaffected).
- `api/proxy.py`: the Core API proxy authenticates the add-on by its token, requires `homeassistant_api`, forwards with the Supervisor's own Home Assistant token, and passes no add-on identity to Core.

Also verified in core 2026.2.3 and its dependencies after revision 1:

- `util/yaml/loader.py::secret_yaml` delegates to `annotatedyaml`, which raises `YAMLException("Secrets not supported in this YAML file")` when `loader.secrets is None`; `load_yaml(path)` passes no secrets object, so a file containing `!secret` fails loudly at load with `HomeAssistantError` and nothing is written. `!include` is resolved at load and would be written back inlined.
- `components/automation/__init__.py:381-388`: `automation.reload` is registered with `schema=vol.Schema({vol.Optional(CONF_ID): str})`, so passing `{"id": ...}` is accepted, not rejected. `script` and `scene` reload take an empty schema, so their calls must carry no data.
- `components/hassio/coordinator.py:542-553` with `aiohasupervisor` 0.3.3: `get_addons_info()` is fed by `addons.addon_info(slug).to_dict()` (renamed to the legacy `hassio_api`/`hassio_role` keys) for every installed add-on, and the `InstalledAddonComplete` model carries `apparmor, auth_api, docker_api, full_access, host_network, host_pid, host_uts, ingress, rating, protected, privileged, network, signed, hassio_role, auto_update, watchdog, boot` among others. So the add-on privilege inventory (sprint 7) and the `addon_unprotected` fail-open fix (item 4.3) can rely on these keys being present on a Supervisor install. The exact JSON shape on the owner's install is still confirmed by D-21.
- yarl 1.x normalizes `..` path segments before sending, so `URL(base) / "repos" / "../../x/y"` resolves to `/x/y` (GH-1 impact is real, not theoretical).
- Backups: cloud backups are encrypted by default, other locations optional; since 2026.4 the format is SecureTar v3 (Argon2id, XChaCha20-Poly1305); the key is retained in `.storage/backup` with the emergency kit as the off-system copy. Home Assistant OS has no native disk encryption (open feature requests only).

Developer documentation: `docker_api` "works only for not protected apps".

Advisories: GHSA-gh5m-4m97-c95h (March 2026, CVSS 9.6, unauthenticated add-on endpoints exposed to the LAN through `host_network`; fixed in Supervisor 2026.03.2); CVE-2023-41899 (an unvalidated add-on slug in `hassio.addon_stdin` reached Supervisor API paths).

aiohttp 3.13.x: on a cross-origin redirect the client strips `Authorization`, `Cookie`, and `Proxy-Authorization` only; other headers, including `X-API-KEY`, are re-sent.

Test environment used: Python 3.13.13, `pytest-homeassistant-custom-component` 0.13.316 (brings Home Assistant 2026.2.3), `home-assistant-frontend` 20260128.6, plus `aiousbwatcher`, `pyserial`, `pyudev`. Repository suite: 254 passed; with the six verification tests: 260 passed.

### 6.2  Unverified; verify before code depends on it

Settled since revision 1 (moved to 6.1): the `get_addons_info()` field set, `!secret`/`!include` behavior, the `automation.reload` schema, and yarl `..` normalization.

Settled by the first live D-21 run (2026-08-30, output pasted by the owner; recorded in `ha_soc_probe/DOCS.md`): Supervisor 2026.08.0 (GHSA-gh5m-4m97-c95h patched); the add-on installs, scans, and reports on the real Supervisor, and the 502 hold-and-retry path recovered from a live Core restart; the observed rating is 1 with `apparmor: default`, `protected: true`, `signed: false`; the live `get_addons_info()` payload carries every key the sprint 7 inventory needs; both services are registered through the proxy; the pre-fix build's file modes (0o644 store and audit files, 0o755 audit directory) confirmed the DATA-1 finding on disk; backup encryption is on for the default and the one configured agent. The run's container-level section found no container to inspect (the add-on was mid-recreate under auto-update), so the entries below stay open; the script now discovers the container instead of assuming its name.

Still open, all covered by `ha_soc_verify_supervisor.sh` (D-21) except the last two:

- Whether `/var/run/docker.sock` resolves to `/run/docker.sock` inside the running Probe container on this host.
- Which iptables backend (legacy or nft) the Probe's binaries use and which one Docker on the host uses; whether `ip6tables` and the `ip6_tables` kernel module are present. Item 2.4 depends on this.
- The AppArmor profile, capability set, secret file mode, and absence of listening sockets in the running container (item 2.5).
- The exact `get_addons_info()` JSON as returned on this install (field set confirmed against the model; the live shape confirms it).
- Whether the Supervisor runs an add-on-provided uninstall hook usable to remove the `INPUT` jump and the chain. The Supervisor has an `app_uninstall` step but no documented add-on-authored pre-uninstall script; treat removal as best-effort and document that an empty chain and one jump may remain (item 2.3).
- UniFi field names per firmware (the `# VERIFY` markers in `unifi.py`); confirmed only against the owner's console.

## 7. Running the suite

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install "pytest-homeassistant-custom-component==0.13.316" \
  "home-assistant-frontend==20260128.6" aiousbwatcher pyserial pyudev
pytest tests/ -q
```

Pin the two versions together: the harness pins a core version, and `home-assistant-frontend` must match the version listed in that core's `package_constraints.txt`. When the harness is bumped, read the constraint and bump the frontend pin in the same change. Record the resulting core version in the README's Development section so the "tested on" claim is checkable.

The six verification tests are in `tests/test_review_verification.py`. Each has a comment naming the finding it reproduces. When an item lands, invert the corresponding test (assert the fixed behavior), rename it to describe the guarantee, and move it into the module's own test file; the file should be empty and deleted by the end of sprint 1.

## 8. Definition of done for the whole plan

- Every High finding in the review is closed by a merged item with its regression test, and CI runs that test.
- Every Medium finding is either closed or recorded in section 2 with a decision and a date.
- The README, `DOCS.md`, and every module docstring describe the shipped behavior, including the Probe's real rating, the `INPUT` jump, the IPv4-only or dual-stack state of the firewall, what leaves the instance and to whom, and what the audit chain does and does not prove after retention and after a wipe.
- Section 6.2 is empty or every remaining entry is labeled UNVERIFIED in the code comment or docstring that depends on it.
- No secret value exists anywhere but the private secret store: not in `settings`, `entry.options`, `entry.data`, `hass.data`, a module global, an entity attribute, a WebSocket payload, the audit log, diagnostics, or a scanner snippet. The self-scan test (`test_ha_soc_passes_its_own_extraction_rules`) passes.
- The firewall is owner-only end to end and behaves identically for IPv4 and IPv6, or reports honestly when the host cannot do IPv6.
- Every detection threshold is owner-tunable with a secure default and a reset control.
- The single add-on carries every host feature the integration needs and states each privilege it holds and why in its ledger.
