# Decisions

## 2026-09-06, external audit ingest verifies chains but does not import files

The Elk Programmer app keeps a hash-chained audit log under its own `/data`. HA SOC
could have read that file through a share mount, but a file the source can rewrite
is not evidence. Instead the source pushes records through `ha_soc.ingest_audit`
and HA SOC keeps the last accepted head per source, so any later edit of the
source's file cannot change what HA SOC already holds. A gap is treated as a break
rather than a warning because the link to a record HA SOC never saw cannot be
verified; the response tells the source where to resume. Rejected: a shared
secret for every source (one leak would let any tool speak for any other) and
reusing the Probe's pairing secret (the Probe's secret authorizes firewall changes;
audit ingest must not inherit that).

Dated decisions with the alternative rejected and why. Entries marked "recorded" were captured on 2026-09-03 from code comments and docstrings during the comment-to-docs pass; the original decision predates that date and, where a work item or decision number is known, it is given. Decision numbers (D-nn) and work items refer to `HA-SOC-Security-Work-Plan.md`.

## Access control and users

- 2026-09-03 (recorded; D-4). Every firewall command, status included, is owner-only. Rejected: letting admins read status under `owner_and_admins`, because reading the ruleset maps the attack surface and a change can leave the platform unreachable.
- 2026-09-03 (recorded; D-5). A pending firewall test the add-on never reported on is cleared only by an explicit owner discard (`ha_soc/firewall/discard_pending`, status `discarded_unreported`) or the add-on's own report, and the server refuses the discard while the countdown runs. Rejected: automatic clearing, because Core never learned what happened on the host and an early discard could race a merely late report.
- 2026-09-03 (recorded; D-14 option (a), work item 1.4). HA SOC's own actions go into its own audit chain: every mutating command and the three privileged reads are audited. Rejected: option (b), auditing ordinary list and summary reads too, because logging every panel refresh would bury the records that matter. Layout commands fall under the same carve-out for a caller's own preferences.
- 2026-09-03 (recorded; D-23 option (a)). Commands that can cut a user off are owner-only when the target is an admin-group user, resolved server-side; `entity_remap/apply` and `permissions/sidebar/push` are owner-only outright. Rejected: leaving them at the admins tier, because an admin who can cut off other admins or rewrite configuration can take the platform over.
- 2026-09-03 (recorded; D-18 option (a), work item 3.11). MFA compliance is assessable only for users Home Assistant's own provider authenticates; users whose credentials all come from an SSO proxy, `trusted_networks`, or a command-line provider are exempt from `auto_deactivate` and shown "MFA not assessable". Rejected: deactivating an externally-MFA'd admin for a factor HA cannot observe, which would punish a compliant account.
- 2026-09-03 (recorded; MED-9). `async_revoke_all_sessions` includes long-lived access tokens. Rejected: the earlier version that skipped them, because the incident-response action must not leave a compromised account's persistent tokens standing.
- 2026-09-03 (recorded; work item 4.12). A password reset revokes the target's interactive sessions by default with an explicit opt-out, and the browser `prompt()` was replaced with a masked in-panel field. Rejected: leaving sessions alive, which changes nothing for an attacker holding one, and a plain-text dialog for a password.
- 2026-09-03 (recorded). The options flow is a single informational step. Rejected: mirroring settings into Home Assistant's native Configure dialog, because the dialog cannot identify the requesting user and so could not honor the owner-only rule.
- 2026-09-03 (recorded; D-19 option (a), work item 3.10). Entities expose the posture grade and the user risk band only. Rejected: exposing the per-term breakdown and factor list as attributes, because entity attributes have no per-user ACL.

## Secrets and storage

- 2026-09-03 (recorded; SEC-1). Secrets moved from the general settings dict and `store.data["firewall"]["addon_secret"]` into a dedicated private store, with the legacy copies drained once at setup. Rejected: leaving them in the settings blob, which was handed around in payloads, diagnostics, and audit detail.
- 2026-09-03 (recorded; SEC-2). The `entry.options` settings mirror was removed and a legacy copy is scrubbed to `{}` once. Rejected: keeping the mirror, because `.storage/core.config_entries` is world-readable.
- 2026-09-03 (recorded; D-8 option (a), work item 1.1). The general Store is private and atomic. Rejected: a default Store, because findings, baselines, and firewall history are sensitive even without secrets.
- 2026-09-03 (recorded; D-6 option (a), work item 3.3). Evidence retention prunes only resolved detections and resolved or dismissed findings after `evidence_retention_days`, with a floor of 30 days. Rejected: expiring everything by age, and allowing a value of 1, which would erase an incident's evidence trail.
- 2026-09-03 (recorded; D-12 option (a)). NVD lookups stay on by default with an owner-facing off switch. Rejected: defaulting off, because on was the existing behavior; the change was to disclose it in Settings and the docs.
- 2026-09-03 (recorded; D-9, work item 3.0). The single `risk_learning_period_days` setting was replaced by per-rule `learning_days` thresholds under `detection_thresholds`, validated against `THRESHOLD_SPECS` with a one-action reset. A stored legacy value is migrated into both rules once. Rejected: one global maturity constant.
- 2026-09-03 (recorded). `async_upsert_finding` overwrites `status`, `status_by`, `status_at`, `note`, and `first_seen` from the existing record. Rejected: `setdefault`, because every producer sets `"status": "new"` unconditionally and `setdefault` is a no-op when the key is present, which silently reset confirmed or dismissed findings on every re-scan.
- 2026-09-03 (recorded; work item 3.10). `async_upsert_detection` preserves analyst lifecycle fields when a different writer replaces a detection wholesale. Rejected: letting a re-tripped condition reopen an acknowledged or resolved detection.

## Audit chain

- 2026-09-03 (recorded; work item 3.8). `login_ok` records carry `detail.new_token` so `success_after_failures` can ignore token refreshes. Rejected: treating a refresh as a login, which made the rule fire on background activity.
- 2026-09-03 (recorded). `user_id` on user lifecycle records is the acting admin and the subject is `detail["target_user_id"]`. Rejected: the earlier layout storing the subject in `user_id`, which conflated "acted" with "was acted upon" in the per-user filter.
- 2026-09-03 (recorded; work item 1.7). Immediate flush tasks use `eager_start=False` and a done-check for dedup. Rejected: an eager task, which would drain the buffer inside the caller's frame, and a None reset in a callback, which the done-check makes unnecessary.
- 2026-09-03 (recorded). Helper storage collections and lovelace resources are not hooked. Rejected: reaching their change listeners through per-integration `hass.data` keys, which are not a stable API.
- 2026-09-03 (recorded). `_handle_call_service` has no ambient actor fallback. Rejected: contextvar recovery for the None case, which would re-attribute automation-driven calls to whichever user's session was upstream.

## Detections and risk

- 2026-09-03 (recorded; work item 3.1). `_network_prefix` applies the prefix length per address family. Rejected: the old /24 for everything, a defect for IPv6 because a /24 of a global address lumps entire registries together.
- 2026-09-03 (recorded; work item 3.6). `new_ip_login` evaluates every login since the checkpoint. Rejected: evaluating only the newest event, which granted amnesty to all but the last event of a burst.
- 2026-09-03 (recorded; work items 3.0 and 3.5). Per-rule `learning_days` replaced the hard-coded 14-day maturity constant.
- 2026-09-03 (recorded; work item 3.10). The privilege-escalation group snapshot is persisted in `user_baselines`. Rejected: the in-memory snapshot, which forced silent re-baselining after any restart.
- 2026-09-03 (recorded). Password spraying and per-username brute force are skipped rather than faked. Rejected: approximating them from IP alone, which would duplicate `brute_force_ip` under another name.
- 2026-09-03 (recorded; work item 3.5). The long-lived-token bonus is added before the cap. Rejected: the previous build's add-after-`min()`, which let the factor reach cap plus bonus.
- 2026-09-03 (recorded; work item 3.5). The `never_logged_in` age gate applies only when an age is known. Rejected: the old condition, which could never fire for the accounts it described, since accounts with no refresh tokens have no `account_age_days`.
- 2026-09-03 (recorded; work items 3.0 and 3.2). The `privilege_escalation` and `disabled_user_activity` factors are capped by tunable `risk_cap_points`. Rejected: leaving them uncapped, where many promotions or one stuck retry loop could saturate the whole score.
- 2026-09-03 (recorded; D-10 option (a), work item 3.4). The posture grade always shows, labeled provisional until every term has computed once. Rejected: hiding the grade, which reads as a broken tile.
- 2026-09-03 (recorded). `dormant_revival` contributes zero risk points because its intent is a notification. Rejected: treating a returning familiar user as a penalty.

## Scanner and provenance

- 2026-09-03 (recorded; work plan item 4.8). The scanner file cap selects by size descending with path tie-break. Rejected: first-N-by-path, which let a padded directory push the largest modules past the cap.
- 2026-09-03 (recorded; work plan item 4.8). The on-install scan honors `scanner_enabled`. Rejected: the previous behavior where only the weekly sweep did.
- 2026-09-03 (recorded). Network checks (PyPI staleness, typosquat detection) are deferred to a future `scanner_network_checks_enabled` feature. Rejected: stubbing them, because half-implementing them would be worse than omitting them.
- 2026-09-03 (recorded). A dependency-free stdlib rule set. Rejected: a third-party static analyzer, which would add a large, frequently-CVE'd dependency to every install.
- 2026-09-03 (recorded; work plan item 1.3). The hardcoded-credential rule stores a masked snippet and stays at medium confidence forever. Rejected: escalating confidence with an entropy check, because fixtures and examples are an accepted permanent false positive.
- 2026-09-03 (recorded). The NVD match-string cache is in-memory. Rejected: a persisted cache, because one extra re-fetch after a restart is cheaper than reconciling a second cache format against the finding store.
- 2026-09-03 (recorded; work plan item 4.9). Vendor-only curated CPE matches report as INFO regardless of CVSS. Rejected: carrying the CVE's own severity, which says nothing about the specific model.
- 2026-09-03 (recorded; work plan item 4.10). The `custom_source_list` flag named in the design was removed rather than produced. Rejected: pretending it might be produced, because HACS runtime data exposes only the default/custom split.
- 2026-09-03 (recorded; variance from the feature request). Only the two lowest-provenance HACS origins are flagged (`INTEGRATION_FLAG_CUSTOM_REPO`, `INTEGRATION_FLAG_CUSTOM_SOURCE_LIST`), not default-store content.

## Health, hygiene, and Entity ReMap

- 2026-09-03 (recorded; D-11). Repairs severity mapping: unknown severities map down to WARNING; `addon_unprotected` is HIGH, CRITICAL with `host_network`; `notify_coverage_gaps` splits LOW and MEDIUM. Rejected: mapping unknown strings up, because bad data must not page anyone as CRITICAL.
- 2026-09-03 (recorded; D-20). The Probe's own `addon_unprotected` finding is stored with `acknowledged_by_design=True` and opens no Repairs issue only while hard caps are configured. Rejected: silent suppression, and a blanket exception when no by-design reason exists.
- 2026-09-03 (recorded; work plan item 4.1). Confirmed findings, like dismissed ones, are never auto-resolved by an empty pass. Rejected: letting a pass that could not see the condition override an analyst's judgment.
- 2026-09-03 (recorded; work plan item 4.7). `async_lovelace_missing_resources` reads through `async_get_info()`. Rejected: calling `async_load()` directly, which would leave the `loaded` flag unset and re-fire the collection's change notifications on every sweep.
- 2026-09-03 (recorded). A proactive template-mention sweep is not built. Rejected: a live Jinja render per template (CPU-bound on the loop and unreliable without trigger context) and a regex scan (false positives on similar names); the per-entity interactive search already covers the one-at-a-time case.
- 2026-09-03 (recorded; D-13 (a) plus (b), work item 1.9). Comment, anchor, and key-order loss in rewritten YAML is accepted and stated up front, and a file containing `!include` or `!secret` is refused entirely. Rejected: attempting a write-back of a tainted file, because `!include` would be inlined and `!secret` fails to load; over-refusing (a quoted literal "!include" also refuses) is safe, silently inlining is not.
- 2026-09-03 (recorded; work item 1.9). The apply result carries the `backups` list; the `ApplyResultWithBackups` alias remains only so existing references keep reading.
- 2026-09-03 (recorded; work item 2.2). A watchdog clear is exempt from the installed-add-on check. Rejected: applying it, which would strand a cap left by an uninstalled add-on.
- 2026-09-03 (recorded). Runtime watchdog state is memory-only. Rejected: persisting counters and history through the debounced Store on every sample, which would churn it for no configuration value.
- 2026-09-03 (recorded). Hard caps are applied by the Probe against the Docker socket. Rejected: the Supervisor API, which exposes nothing that sets add-on limits (verified against aiohasupervisor's `AddonsClient`).
- 2026-09-03 (recorded; per the feature request). `DEFAULT_WATCHDOG_ACTION` is restart once the watchdog is enabled. Rejected: alert-only as the enabled default; the watchdog itself stays off by default.
- 2026-09-03 (recorded). Peripherals reuse core's USB discovery data. Rejected: Probe-side enumeration, which would add container privileges for data core already has.

## Network integrations

- 2026-09-03 (recorded). `DEFAULT_UNIFI_VERIFY_SSL` is False, matching Home Assistant's official UniFi integration, because consoles ship self-signed certificates; per-connection opt-in verification was kept.
- 2026-09-03 (recorded). unifi.py targets the Integration API only, with `_ACL_ENDPOINT_SUFFIXES` limited to `acl-rules`. Rejected: private-controller fallback paths, because the user explicitly selected the supported Local Integration API.
- 2026-09-03 (recorded; superseding history). The ACL schema was rebuilt against the user-uploaded Network 10.4.57 OpenAPI spec, replacing the third-party extraction the module was first built against.
- 2026-09-03 (recorded). All four ACL filter fields are read unconditionally rather than dispatching on `type`; correct because each leaf variant populates only its own fields, with less code.
- 2026-09-03 (recorded; feature request). IPv6 was dropped from the devices table (not in the API) and uptime replaced by `firmware_updatable`; `ipv6` stays in the device payload.
- 2026-09-03 (recorded). `_fetch_firewall_policies` does not probe candidate paths because the endpoint is confirmed real, so a failure is a real problem. No undocumented Protect calls are made for events; the core unifiprotect bootstrap is the events source.
- 2026-09-03 (recorded). ACL Rules and Firewall Policies are treated as two separate resources, confirmed against a live controller whose ACL endpoint returned zero rules while its real configuration lived under Firewall Policies. Rejected: treating them as two names for one feature.
- 2026-09-03 (recorded). unifi_core.py never imports `aiounifi`, `uiprotect`, or the core unifi components. Rejected: importing the core constants, which would import those libraries transitively and crash installs without them. Snapshots whitelist fields rather than copying `.raw` and redacting.
- 2026-09-03 (recorded). Network-security findings have no dismiss or resolve lifecycle. Rejected: a persisted status like the CVE and hygiene findings, because these concern live network and DNS configuration that changes between refreshes, so recomputing fresh is more honest than a status that could go stale; add it later if real false-positive noise argues for it. Every finding is advisory; the project does not edit UniFi rules, toggle Pi-hole blocking, or reassign clients.
- 2026-09-03 (recorded). Pi-hole is queried directly. Rejected: core's `pi_hole` integration, which exposes no query log, group, or client-scoping surface. An unrecognized response shape degrades to None, as in unifi.py.
- 2026-09-03 (recorded). `SERVICE_POLL_SNMP_CONFIG` is a separate poll endpoint. Rejected: sharing the firewall poll, so SNMP configuration is never confused with the `current_test_id` protocol.

## Probe and firewall

- 2026-09-03 (recorded). The Probe add-on is matched by its `name:` field. Rejected: matching the slug, which the Supervisor derives from the repository URL the user added. Probe services are not registered at all on Core or Container installs. Rejected: registering and always rejecting.
- 2026-09-03 (recorded). The add-on picks up firewall commands by polling an ordinary service call with `return_response=True`. Rejected: opening a new listening port on the add-on, because scanner.py already treats extra listening sockets on a security tool as the wrong default.
- 2026-09-03 (recorded; D-3, work item 2.4). A firewall rule with no source defaults to family "both", a sourced rule is pinned to its source's family, and a contradicting explicit family is rejected outright. Rejected: IPv4 only, because the verified host carries global IPv6 and an IPv4-only deny there is not a deny; and silently correcting a contradiction, because a rule claiming family 6 with an IPv4 source is a misunderstanding the operator needs to see. The old "IPv4 only" label survives only as `partially_applied`.
- 2026-09-03 (recorded). The firewall test window is fixed at 45 s, the midpoint of the requested 30 to 60 s, and is not user-configurable yet.
- 2026-09-03 (recorded). `FIREWALL_TEST_EXPIRED_UNREPORTED` replaced the bare "expired" string so the panel can say the add-on has not reported.
- 2026-09-03 (recorded; work plan section 2). `expires_at` is re-anchored to `applied_at` plus the window at apply time. Rejected: leaving it at propose time plus window, which ran up to one poll interval ahead of the add-on's real timer.
- 2026-09-03 (recorded; HIGH-1). The trust-on-first-use acceptance of "nothing pinned and nothing presented" was removed; a missing secret is always a rejection, and pinning can only happen on a call that passed the Supervisor-context check. Rejected: the old branch, which let any local caller through until the real add-on's first report.
- 2026-09-03 (recorded). An unresolved firewall test found at startup is treated as failed and reverted immediately. Rejected: treating it as in progress, because there is no way to know how long its window has been open.
- 2026-09-03 (recorded; work item 2.6). Stop-time revert lives in the finish script, not the TERM trap. Rejected: reverting in the trap, because the finish script runs for both crashes and deliberate stops, and the resolved marker makes every path idempotent.
- 2026-09-03 (recorded). IPv6 addresses are reported undecoded by the port scanner. Rejected: decoding them, because a security tool showing an incorrect bind address is worse than one that says "not decoded".
- 2026-09-03 (recorded). Resource caps are re-applied on a timer. Rejected: applying once, because the Supervisor recreates containers on update or restart and silently drops Docker-level limits.
- 2026-09-03 (recorded). snmpset and tempio are removed from the Probe image. Rejected: retaining them, because validation runs from the external monitoring host and no service uses TempIO.
- 2026-09-03 (recorded). Apply-failure reasons are reported by the add-on and shown on the card. Rejected: leaving `backup_failed` and per-family failures only in the add-on log.
- 2026-09-03 (recorded). Every service chmods the probe secret to 0600 on start and hands the value to the unprivileged scanner through the environment. Rejected: loosening the file, after the first live verification run found it at 0644.
- 2026-08-30 (work item 2.5, recorded as the answer, not implemented). Image signing for the Probe: per the developer documentation (docs source at commit 186ad06, docs/apps/security.md and docs/apps/publishing.md), add-on image signing is done with Cosign through the official builder workflow and applies to pre-built images published under an `image:` key. This add-on is built locally (no `image:` key), so a signed image is structurally unavailable and `signed: false` is accurate. Rejected for now: moving to signed pre-built images via the official builder actions and an `image:` key. The older CodeNotary mechanism no longer appears in the documentation. The base-image digest pin is the compensating control.
- 2026-09-02 (work item 2.5). The base image is pinned by digest `sha256:93ef607824e3f27e868f11b10938283a98bf880ed57bcf8eaa81c6c2d521f6f5`, the multi-arch index for `ghcr.io/home-assistant/base:3.24` covering linux/amd64 and linux/arm64. Rejected: the bare moving tag, whose contents change between rebuilds.
- 2026-09-03 (recorded; D-21). The verified host runs the nf_tables backend for both families and ip6tables works; the design still probes ip6tables per cycle rather than assuming it.
- 2026-09-03 (recorded). `ha_soc_verify_supervisor.sh` discovers the container by name and falls back to `addon_<slug>`. Rejected: assuming the conventional name, after the first live run failed with "No such container" during an auto-update recreate.

## Frontend

- 2026-09-03 (recorded; original date unknown). The Customize editor reorders a compact chrome list. Rejected: live-dragging full card content, because cards can be large tables and re-rendering on every dragover would be slow for no benefit. Native HTML5 drag alone was rejected as the only path because it is not keyboard-usable; Up/Down buttons are primary and drag is a progressive enhancement.
- 2026-09-03 (recorded). IPv6 CIDR containment is not implemented in device-match.ts. Rejected: guessing, because it needs 128-bit arithmetic; an IPv6 subnet entry is left unmatched.
- 2026-09-03 (recorded). The firewall matrix reports "mixed" rather than a winning policy. Rejected: modeling UniFi's ordered evaluation with implicit deny, which was not verified well enough to claim a winner.
- 2026-09-03 (recorded). types.ts declares only the `HomeAssistant` surface the panel touches. Rejected: vendoring a full copy of frontend's types.ts (Alarmo's approach).
- 2026-09-03 (recorded). Core commands (`system_log/list`, container logs) are called directly. Rejected: proxying them through `ha_soc/*`, since they are already admin-gated and the panel gates tab content first.
- 2026-09-03 (recorded; work plan item 0.4, UI-1). `backup_acknowledged` is always sent by `applyFirewallRules`. Rejected: the earlier omission, which made every apply fail schema validation so the feature was unreachable; `tests/test_ws_contract.py` now guards this class of bug.
- 2026-09-03 (recorded). The log-level palette was split from the finding-severity pill classes. Rejected: sharing them, which rendered ERROR and CRITICAL identically; five distinct tiers replaced that.
- 2026-09-03 (recorded). The ACL Rules card, HA-server-port correlation, and Pi-hole section moved out of the Network tab into the Network Security view.
- 2026-09-03 (recorded). The Network tab keeps the Dashboard view's visual language (stat tiles, searchable paginated table) because the user asked for it to look close to identical.
- 2026-09-03 (recorded). permissions-view stores the server's message on a failed load and treats `fetchDashboardConfig`'s `not_found` as an empty view list. Rejected: falling through to the "no views" empty state, which read as a working page with nothing to manage, and letting `not_found` bubble as an unhandled rejection, which read as "broken until you reselect" even though reselecting cannot fix an unconfigured dashboard.
- 2026-09-03 (recorded). Settings controls apply immediately. Rejected: a Save button, because a staged change did not survive the remount on tab switch and read as "my selection didn't take".
- 2026-09-03 (recorded; work plan item 4.12). Every view keeps a distinct `_error` rendering a could-not-load state with the server's message. Rejected: rendering a failure as an empty result, a stuck "Loading..." page, or an unrelated backend state.

## CI and release

- 2026-08-30. hacs/action and hassfest are pinned to a head commit with the date recorded. Rejected: a floating ref, because upstream publishes no release tags (hacs/action stopped at 22.5.0; home-assistant/actions documents `@master`).
- 2026-09-03 (recorded; D-16). CI tests only the pinned latest harness version until a minimum-version job is decided. Rejected: a version matrix, in favor of the safe default.
- 2026-09-03 (recorded). Test-suite choices: the elkm1 entry is left NOT_LOADED in test_security_health rather than forced LOADED, to avoid importing `elkm1_lib` at teardown; `_check_unused_labels_and_blueprints` is excluded from the "nothing broken" health test because the harness ships a real example blueprint.
- 2026-09-05. Customizable views render their own sections and use `<ha-soc-customize-list>` only as the editor. Rejected: rendering the sections inside the list's shadow root, which the list did from its introduction on 2026-09-01 through the console redesign; the view's stylesheets do not reach that shadow root, so every card, table, donut, and gauge on every Customize-enabled view rendered as unstyled text. Also rejected: duplicating `sharedStyles` and each view's styles into the list, because the view-specific rules live in eleven different components and would drift. A structural test in tests/test_frontend_visual_contract.py guards the fix.
- 2026-09-05. The Overview uses sentence-case KPI labels, rounded tinted state pills for posture, trend delta, security-source health, and priority-queue severity, and coarse relative ages (exact timestamp in the cell title) in the priority queue, matching the approved console reference. The uppercase `metric-label` style remains on the secondary detail cards so the reference's visual hierarchy between overview and detail holds.
- 2026-09-05. Submitting the Configure dialog reloads the config entry explicitly with `async_schedule_reload`. Rejected: `OptionsFlowWithReload`, because core reloads only when the saved options changed and this flow always saves `{}` (entry.options must stay empty, see test_init.py); an update listener was rejected for the same reason and because it is the pattern the 2026.12 deprecation removes. Also rejected: trying to hot-swap the panel module without a browser reload, which the custom element registry does not allow; the panel shows a reload banner instead.
