# Operations

Configuration keys and their consequences, thresholds and defaults, permissions and why they are needed, runtime knobs, and troubleshooting. Supervisor transport quirks (the journald log gateway) stay in `OPERATIONS-NOTES.md`; the watchdog's two-layer summary stays in `RESOURCE-WATCHDOG.md`; SNMP configuration and validation steps stay in `SNMPV3.md`.

## Access and MFA policy

`access_level` (`CONF_ACCESS_LEVEL`) is `owner_only` (the default) or `owner_and_admins`; it decides who may reach the panel and its `ha_soc/*` commands at all. The default is the strictest option because a security-posture tool is itself a high-value target, so it starts locked to the owner and must be deliberately opened up, never the other way around. A non-owner admin passes `require_soc_access` only when the setting is explicitly `owner_and_admins`; if the runtime is not reachable yet, the gate fails closed. `ha_soc/access/info` and `ha_soc/version/get` stay on plain `require_admin` so a locked-out admin can find out why and the version shows on the denied screen. The owner-only tiers above that are in `security.md`.

`mfa_policy` is `audit_only` (default) or `auto_deactivate`; `mfa_grace_period_days` defaults to 14. An instance that authenticates entirely through an external SSO or header-auth proxy should keep `audit_only`, because `auto_deactivate` has nothing it can honestly judge there (work item 3.11); users whose credentials all come from a non-homeassistant provider are reported "MFA not assessable" and exempted (D-18).

## Settings keys

Every setting is edited from the panel's Settings tab; Home Assistant's Configure dialog is informational only. Every control applies immediately, with no separate Save step, because a staged change did not survive the remount on tab switch. Secret fields are write-only from the UI: they come back masked ("[redacted]" when set, "" when unset) with a companion `<key>_set` boolean; sending the placeholder leaves a secret unchanged, an empty string clears it, and an untouched field never fires a change.

| Key | Default | Consequence |
| --- | --- | --- |
| `audit_retention_days` | 90 | Audit day files older than this are deleted (see Audit retention). |
| `audit_max_bytes` | 200 MB | Oldest day files are removed while the total exceeds this. |
| `evidence_retention_days` (`detection_retention_days` on the wire) | 365, range 30 to 3650 | How long resolved detections and resolved or dismissed findings are kept before `async_prune_evidence` prunes them. Open and acknowledged items never expire. Distinct from audit retention. Age is measured from `status_at`, falling back to the record's last activity timestamp for records closed by an older build; a record with no parseable timestamp is kept, because deleting evidence whose age cannot be established would be guessing. The floor of 30 stops an accidental "1" from erasing an incident's evidence trail (work item 3.3, D-6 option (a)). |
| `nvd_lookups_enabled` | on | Whether device manufacturer and model strings are sent to NIST's NVD. When off, no request is made and only the network-free firmware check runs, with a debug log line. Read at scan time with an on-by-default fallback so it works whether or not the key has been persisted yet (D-12 option (a), work plan item 4.9). |
| `nvd_api_key` | unset (secret) | Raises the NVD rate limit from about 5 to about 50 requests per 30 s. |
| `github_token` | unset (secret) | Enables GitHub provenance lookups; without it `ha_soc/integration_security/refresh` returns a clear no-op reason and every GitHub signal stays "not collected". Raises GitHub's limit from 60 to 5,000 per hour. |
| `detection_thresholds` | empty | Sparse per-rule overrides `{rule: {param: value}}`, merged per field; effective values are always read through `detections.thresholds()`, so a missing key means secure default, never off. `risk_learning_period_days` (formerly 14) is no longer part of the schema; it was replaced by the two per-rule `learning_days` parameters and a stored value is migrated into both once (work item 3.0, D-9). |
| `scanner_enabled` | true | Governs every scan path: the weekly sweep and the on-install scan. |
| `scanner_network_checks_enabled` | false | Reserved for future network checks; nothing is implemented behind it. |
| `security_sources_enabled` | all enabled | Domain (integration or entity platform) to included in Security Integrations Health; a domain missing from the map is treated as enabled (opt-out, not opt-in), so a future addition to the known set does not silently start dark. |
| `syslog_transport` | disabled | RFC 5424 off-box export; UDP and TCP are explicit compatibility modes and TLS is the recommended destination once certificate work is done. |
| `syslog_format` | `rfc5424_json` | Payload format, independent of transport; CEF and bare JSON are receiver-compatibility choices (see `CEF-SCHEMA.md`). |
| `syslog_port`, `syslog_tls_verify`, `syslog_facility` | 514, True, 16 (local0) | Facility is restricted to 16 through 23 (local0 through local7); the narrow range avoids accidental use of kernel or auth facilities at a shared receiver. |
| `unifi_network_host`, `unifi_network_verify_ssl`, `unifi_protect_host`, `unifi_protect_verify_ssl` | unset, False | Direct-to-console connections for the Network tab; the API keys are secrets. An empty host means not configured. `DEFAULT_UNIFI_VERIFY_SSL` is False because consoles ship a self-signed certificate, the same default Home Assistant's official UniFi integration uses; a user fronting the console with a real certificate can turn it on per connection. The host may be a bare host, host:port, or https://host, and userinfo is rejected. The API key is created in the UniFi UI under Settings, Control Plane, Integrations. |
| `pihole_host`, `pihole_verify_ssl`, `pihole_iot_cidr` | unset, False, unset | Pi-hole v6 direct connection for the Network Security tab (http or https, no userinfo, a real hostname; a bare host defaults to https); the app password (Settings, then API, then App password in Pi-hole's UI) is a secret. Both host and password are required before the overview reports configured. `iot_cidr` is the subnet whose DNS the UniFi gateway forwards to Pi-hole; it is used only to check whether Pi-hole has a dedicated client group scoped to it, never to configure DNS. A snapshot exceeding 30 s reports partial data with an explanatory error. |
| `snmp_enabled`, `snmp_listen_address`, `snmp_port`, `snmp_username` | False, unset, 161, unset | The optional Net-SNMP agent in the Probe. Enabling requires listen address, username, and both passphrases (secrets), which must differ; the listener must be an explicit IP address, never a hostname, wildcard, or multicast address. There is deliberately no v1/v2c mode. |

`STORAGE_SAVE_DELAY` is 15 seconds, debounced; the secret store saves immediately.

## Detection thresholds

"Secure default" means the most sensitive value that does not alert on ordinary same-network activity: it misses the fewest attacks at the cost of more alerts, and the Settings tab says so. Changing a threshold is owner-only, audited as `soc_config_change` with a per-field diff, and reversible in one action via "Reset to secure defaults" (`ha_soc/detections/thresholds_reset`). Ranges are inclusive (work item 3.0, D-9).

| Rule | Parameter | Secure default | Range |
| --- | --- | --- | --- |
| `brute_force_ip` | `failures` | 5 | 3 to 100 |
| `brute_force_ip` | `window_minutes` | 15 | 5 to 120 |
| `success_after_failures` | `failures` | 3 | 2 to 50 |
| `success_after_failures` | `window_minutes` | 30 | 5 to 240 |
| `success_after_failures` | `require_new_token` | on | boolean |
| `success_after_failures` | `derate_shared_ip` | on | boolean |
| `new_ip_login` | `ipv4_prefix` | 24 | 16 to 32 |
| `new_ip_login` | `ipv6_prefix` | 64 | 32 to 128 |
| `new_ip_login` | `baseline_days_required` | 3 | 1 to 30 |
| `new_ip_login` | `prefix_expiry_days` | 90 | 30 to 730 |
| `new_ip_login` | `learning_days` | 7 | 1 to 90 |
| `off_hours_anomaly` | `quiet_start_hour`, `quiet_end_hour` | 23, 6 | 0 to 23 each |
| `off_hours_anomaly` | `burst_threshold` | 5 | 2 to 100 |
| `off_hours_anomaly` | `ratio_threshold` | 0.01 | 0.001 to 0.2 |
| `off_hours_anomaly` | `learning_days` | 7 | 1 to 90 |
| `dormant_revival` | `dormant_days` | 30 | 7 to 365 |
| `dormant_revival` | `min_account_age_days` | 60 | 7 to 365 |
| `mass_entity_burst` | `calls` | 20 | 5 to 500 |
| `mass_entity_burst` | `distinct_entities` | 10 | 2 to 200 |
| `mass_entity_burst` | `window_minutes` | 5 | 1 to 60 |
| `token_minting_anomaly` | `tokens` | 2 | 2 to 20 |
| `token_minting_anomaly` | `window_hours` | 24 | 1 to 168 |
| `disabled_user_activity` | `risk_cap_points` | 40 | 10 to 100 |
| `privilege_escalation` | `risk_cap_points` | 24 | 8 to 100 |

Per-rule `learning_days` replaced the old hard-coded 14-day maturity constant (work items 3.0 and 3.5). Lookbacks and query limits are not tunable.

## Audit retention and file modes

`_SEGMENT_MAX_BYTES` (32 MB): a day's file rolls to a new segment past this size, so one very high-volume day cannot grow a file past the size cap before the next UTC rotation, while keeping individual files quick to read and verify. `_FLUSH_INTERVAL` and `_POLL_INTERVAL` are both 30 s; `_DEFAULT_QUERY_LOOKBACK` is 7 days (`async_query` defaults to the last 7 days; `since` and `until` are aware UTC datetimes).

`login_fail` has a configuration dependency: it works only while the `homeassistant.components.http.ban` logger's effective level stays at WARNING or lower. Raising it through the `logger:` integration stops the record being emitted and silently blinds failed-login auditing; health.py's `audit_ban_logger_silenced` check watches for exactly that, reading `BAN_LOGGER_NAME` from audit.py so the string cannot drift.

Retention (`_sync_apply_retention`): day files older than `audit_retention_days` are deleted, then the oldest files are removed while the total exceeds `audit_max_bytes`. Every unlink removes the front of the chain, so each removed file's tail `(seq, hash)` is captured first and the highest becomes the retention anchor. Only files actually removed count. The last remaining file is never deleted, even if it alone exceeds the cap, because losing the entire log is worse than briefly going over budget. If files were removed but none yielded a parseable tail, any existing anchor is left in place and verification will honestly fail at the new front rather than being papered over. Deletions proceed oldest-first; if a new anchor is somehow behind the old one, the further-along anchor is kept. Once the anchor passes the reset point, the reset marker is cleared and logged at INFO, because the wiped range has aged out; the reset stays discoverable in the store mirror's history and the Repairs issue until dismissed.

The directory is 0o700 and every file (day files, `chain_head.json`, its `.tmp`) is 0o600; files a pre-1.1 build left wider are tightened once at startup with an INFO log (work item 1.1). Sizing note: the live install writes roughly 10 MB of audit records per day, which reaches the 200 MB cap in about three weeks; the Audit tab's per-category breakdown shows which category produces the bulk.

## Store constants and defaults

- `STORAGE_KEY` names the main Store; `AUDIT_STORAGE_SUBDIR` is the audit subdirectory under `.storage/`, never written on the event loop.
- `DEFAULT_SCANNER_ENABLED` True, `DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED` False, `DEFAULT_RISK_LEARNING_PERIOD_DAYS` 14 (legacy), `DEFAULT_SNMP_ENABLED` False, `DEFAULT_SNMP_PORT` 161, `DEFAULT_PIHOLE_VERIFY_SSL` False.
- `SECURITY_INTEGRATION_DOMAINS` (kidde_homesafe: Kidde HomeSafe smoke and CO detectors; elkm1: Elk-M1 alarm panel; emporia_vue: Emporia Vue energy monitor; unifiprotect: UniFi Protect cameras and NVR; keymaster: lock code management) and `SECURITY_ENTITY_DOMAINS` (lock, siren, valve) are the known set for the Security Integrations Health card; each is independently toggleable, the list is a default rather than a hard limit, and a domain not in it simply is not offered as a toggle yet.
- `INTEGRATION_SECURITY_CACHE_TTL_HOURS` (24): a repo's GitHub signals are not re-fetched within this window. `GITHUB_API_BASE` is a hardcoded literal.
- `INTEGRATION_TIER_CORE` ships inside Home Assistant and is hassfest-validated; `INTEGRATION_TIER_HACS` is tracked by HACS from a GitHub repo; `INTEGRATION_TIER_CUSTOM` is a hand-copied or unmanaged `custom_components` entry.
- `DEFAULT_FIREWALL_TEST_WINDOW_SECONDS` (45): the window a proposed ruleset stays live before the add-on reverts it if nobody confirms. The user asked for 30 to 60 seconds; 45 is the midpoint, and it is not user-configurable yet.
- `FIREWALL_REPORT_REASON_MAX` (200) bounds the add-on's free-text resolution reason; the add-on truncates to the same length so an honest long reason is cut short rather than rejected.
- `DEFAULT_WATCHDOG_ENABLED` False (opt-in; the watchdog never auto-acts out of the box); `DEFAULT_WATCHDOG_CPU_PERCENT` and `DEFAULT_WATCHDOG_MEMORY_PERCENT` 85; `DEFAULT_WATCHDOG_SUSTAINED_SAMPLES` 3; `DEFAULT_WATCHDOG_INTERVAL_SECONDS` 60; `DEFAULT_WATCHDOG_ACTION` restart (once enabled, a sustained breach restarts the add-on, with a per-container override to alert or stop); `WATCHDOG_MAX_ACTIONS_PER_HOUR` 3, after which a container is downgraded to alert-only because an add-on that re-breaches after every restart is a restart loop.
- `STALE_TOKEN_UNUSED_DAYS` (180, repairs.py) matches Spook's own long-lived-token staleness threshold, a field-tested value rather than this project's invention. `AUDIT_CHAIN_RESET_ISSUE_ID` is one fixed issue id: a second reset before the first was dismissed refreshes the same issue with newer numbers, and the incident-by-incident history lives in the chain itself. The issue renders `disk_seq` as "none" when the head file was gone entirely.

## Watchdog and container resources

`ws_watchdog_set`: a slug about to be stored must name an add-on the Supervisor reports as installed; off Supervisor the request is refused `not_supervisor`, and an unknown slug `addon_not_installed`. Clears are exempt from the installed check so an override or cap left behind by an uninstalled add-on stays removable, and a clear never sends the slug anywhere (the Probe resets removed caps from its own applied list); the slug's shape is still schema-enforced (`ADDON_SLUG_PATTERN`) for clears (work item 2.2). Clearing a hard limit also drops its `hard_limit_state` entry, since stale applied-state would read as "still capped". After any change the sampling timer is re-armed so enabled and interval changes apply immediately. `ws_watchdog_status` returns config plus per-container runtime state (breach counters, last outcome, usage history) plus hard-cap applied state.

`_HISTORY_SAMPLES` (60) is the ring-buffer depth per container, one hour at the default interval, enough to show a leak's growth curve. Per-container overrides set thresholds and an action of alert, restart, or stop; Core and the Supervisor are always alert-only. Hard caps require the Probe's Protection Mode disabled, are re-applied by the Probe on a timer, and report per container as `hard_limit_state`. containers.py flags `high_cpu` and `high_memory` at 85.0 percent and bounds fan-out with `_MAX_ADDONS` (80) and `_CONCURRENCY` (6). Container logs require a Supervisor install.

## Health thresholds and checks

| Constant | Value | Consequence |
| --- | --- | --- |
| `DETAIL_ITEMS_CAP` | 100 | Item lists in a finding's detail are capped so one pathological install cannot bloat the store and WS payload; `total_count` carries the true count (work plan item 4.4). |
| `MIN_TRUSTED_PROXY_V4_PREFIX` / `V6` | 24 / 64 | Any `trusted_proxies` network broader than these is flagged (work plan item 4.2). |
| `COLLECTION_UNAVAILABLE_RATIO_THRESHOLD` | 0.2 | A loaded, non-retrying integration with more than this fraction of entities unavailable is flagged "collection". |
| `ERROR_COUNT_ISSUE_THRESHOLD` | 5 | A loaded integration logging more than this many WARNING+ records in 24 h is flagged "errors". |
| `PROBE_NOT_REPORTING_GRACE` | 30 minutes | How long the Probe can be installed and running without reporting before a Repairs issue; generous because the add-on retries every 30 s to 5 min on a rejected report. |
| `STARTUP_GRACE` | constant | Sweeps do not evaluate until Home Assistant finished starting plus this. |

Repairs mirroring maps severity strings explicitly and anything unknown down to WARNING, because bad data must not page anyone as CRITICAL (work plan item 4.4, D-11). INFO findings are never mirrored; inventory checks (`cloud_egress_inventory`, `ssh_addon_inventory`) are upsert-only.

Per-check notes (severity, obvious false positive, could-not-evaluate behavior):

- `http_insecure`: the `no_ssl` LOW finding is quieted to INFO when the http configuration shows a deliberately configured reverse proxy (truthy `use_x_forwarded_for` with a narrow `trusted_proxies` list). False positive of the quieting: a proxy itself reachable over plain HTTP. When the YAML cannot be loaded the LOW finding stands (work plan item 4.2).
- `http_hardening` (cors, ip_ban, login_attempts_threshold, proxy trust): a failed YAML load skips the pass and leaves findings untouched. False positive: an isolated management network where every host on the range is the proxy tier. An unparseable `trusted_proxies` entry is reported as a problem, because an unparseable trust list is not a narrow one.
- `trusted_networks_permissive`: one finding per provider; HIGH when `trusted_users` maps a network to an admin or the owner. False positive: an isolated management VLAN mapped to the owner on purpose. An unreadable `auth_providers` shape skips the pass; a user id that no longer resolves is reported by id.
- `addon_unprotected`: Supervisor-only; HIGH, CRITICAL when the add-on also has `host_network`. False positive: an add-on that manages other add-ons or backups and legitimately needs Protection Mode off; confirm and dismiss it once, the status survives re-scans. Fail closed (work plan item 4.3): a cached info dict missing `protected` or `host_network` yields an INFO could_not_evaluate finding naming the key; `host_network` is consulted only once protection is off. An add-on whose info the Supervisor failed to serve is skipped rather than treated as clean. The Probe itself gets `acknowledged_by_design` only while hard caps are configured (D-20).
- `ssh_addon_inventory`: informational, best-effort. `ssh_addon_exposed`: Supervisor-only, mirrored; a missing `host_network` or `network` key must not read as "not exposed". `probe_addon_not_reporting`: a missing state key is reported, never read as "not running".
- `audit_ban_logger_silenced` (LOW, work item 1.7): see Audit retention. False positive: an operator who deliberately silenced the logger; the finding puts that decision on the record.
- `storage_file_modes` (LOW, SEC-7): `secrets.yaml` readable beyond 0o600 or `.storage` beyond 0o700; the summary carries the exact chmod. A stat that fails for a reason other than absence skips the check; an absent `secrets.yaml` is nothing to check. False positive: a filesystem that cannot represent POSIX bits (a network share, FAT).
- `config_mapping_addon` (MEDIUM, HIGH when also exposed via `host_network` or published ports, SEC-7): recognizes well-known config-mapping add-ons (SSH, Samba, File editor, Studio Code Server, and common forks) by name or slug substring because the cached info exposes no volume map; absence of a finding is not proof nothing maps the directory. False positive: a dashboard named "SSH Monitor". Off Supervisor there is nothing to check; an unpopulated cache skips the pass; a missing key is reported (work plan item 4.3).
- `backup_unprotected` (MEDIUM, SEC-7): an absent `.storage/backup` means backups were never configured and resolves any prior finding; an unreadable file skips the pass. False positive: deliberately unencrypted backups on physically secure media.
- `samba_unauthenticated` (HIGH, SEC-7): a key named exactly `password` (case-insensitive) with a falsy value, or any boolean key containing `guest` that is true; different key names are could_not_evaluate, and no readable options is an INFO finding naming the key. False positive: a fork that authenticates through host users.
- Reference checks: `unknown_service_references`, `unknown_area_floor_label_references`, `alert_unknown_references` (HIGH), `notify_group_unknown_members`, `person_unknown_trackers`, `lovelace_missing_resources` (informational), `unknown_customize_entities` (informational), `notify_coverage_gaps` (LOW for an untracked source, MEDIUM for one toggled off), `broken_entity_references` (one aggregated finding).

Security Integrations Health: each entity and integration domain can be toggled off under `security_sources_enabled`; a missing key means enabled.

## Scanner and provenance knobs

Skipped scanner files (over 500 KB or beyond the 400-file cap) are logged at warning with counts and the domain's coverage is marked partial; parse failures are logged at debug with the exception class. A domain with no coverage record renders "not scanned". GitHub provenance looks up at most 60 repos per refresh; the overflow is logged at info and reported as `skipped`; invalid slugs are logged at warning (first ten, slug names only) and a renamed repo whose manifest still carries a malformed URL stays "not collected" until fixed; an exhausted rate limit logs at warning and the refresh reports `ok: False, reason: rate_limited`. `hacs_installed` is true when HACS runtime data was readable or `hacs` is in `hass.config.components`; `hacs_source_introspectable` reports whether origins could be read.

## Entity ReMap backups

`REMAP_BACKUP_DIR` is `.storage/ha_soc_remap`. JSON snapshots of storage dashboards and helper entries land there before each rewrite, files 0o600 in a 0o700 directory, and backups older than 30 days are pruned at the start of every apply, so the directory is bounded by use without a timer. YAML files are copied aside as `<file>.ha_soc-<timestamp>.bak` with a millisecond timestamp so two applies in one second cannot collide (work plan item 4.14). All backup paths come back in the result's `backups` list. `YAML_TAINT_REASON` ("contains !include or !secret; manual edit required") is the one reason a refused file reports. Comment, anchor, and key-order loss in rewritten YAML is accepted and stated up front, exactly as core's own editor behaves (work plan item 1.9).

## Logs

`_MAX_READ_BYTES` is 64 KiB for the fault log; `_MAX_CONTAINER_LOG_BYTES` is 128 KiB and `_LOG_FETCH_TIMEOUT` 30 s. Both views mark `truncated: True` when the tail was cut. The target selector lists core, supervisor, host (full journal), and every installed add-on sorted by name; `ws_logs_targets` lists them and the Logs tab does not offer the selector off Supervisor. `ws_health_list` sorts findings most severe first using `SEVERITY_ORDER`; an unknown severity sorts last rather than raising.

## Firewall operations

Only one pending test can exist at a time; a second proposal is refused with `test_pending_unreported` until the first resolves or is discarded, and the panel's Test button is disabled with that reason. The card polls `ha_soc/firewall/status` every 2 s while a test is in flight. `ws_firewall_discard_pending` archives a pending test whose report will never arrive; the server refuses it while the countdown runs (`window_not_lapsed`), and the panel offers the button under the same condition (D-5). `ws_firewall_reset_pairing` is the owner-only recovery for the Probe pairing: it clears the pinned secret so the next non-empty one re-pins; use it after the add-on was reinstalled or rotated its secret, or a bad first-boot pin locked out the real add-on. The firewall card and Host Probe both require the add-on to be running. The latest archived test's failure reason (`backup_failed`, or a per-family apply failure) is shown on the card. A revert that finds its chain snapshot missing logs an error and leaves the chain as-is.

## Permissions matrix

Every failure returns `(False, error_reason)` with a stable string (listed in `protocol.md`). When no dashboards storage collection is reachable, `require_admin` and `show_in_sidebar` must be changed manually in Settings > Dashboards.

## Panel bundle

If `frontend/dist/ha-soc-panel.js` is missing, panel registration is skipped with a warning; build `frontend/` first (see frontend/README.md).

The panel is one JavaScript module. `panel.py` registers it with a module URL that ends in `?v=<token>`, where the token is the first sixteen hex characters of the bundle's SHA-256, and serves the file with caching disabled, so every new bundle has a new URL. The same token is passed to the frontend as `panel.config.bundle_token`.

Updating the panel still needs a browser reload, and no server-side action can avoid it: Home Assistant's frontend is a single-page application, and once the old module has defined the `ha-soc-panel` element the browser cannot replace that definition until the page is reloaded. The panel therefore detects the situation itself: it reads the `?v=` token from `import.meta.url` (the URL its own code was loaded from) and compares it with `panel.config.bundle_token`; when they differ it shows a banner with a Reload button above the header. The banner appears after a Core restart on a new release, and after Reconfigure when a new bundle is on disk.

The Configure dialog (Settings, Devices and services, HA SOC, Configure) holds no settings. Submitting it reloads the config entry, which re-registers the panel with the bundle currently on disk and refreshes the token. That is the tool to use when the bundle changed without a Core restart, for example during frontend development; a HACS update still needs the Core restart for its Python code. Removing and re-adding the integration is never required for a panel update.

## Probe add-on

### Privileges and options (config.yaml)

| Key | Value | Consequence |
| --- | --- | --- |
| `host_network` | true | The container shares the host network namespace; this makes `/proc/net/tcp[6]` the host's table and lets the SNMP agent bind a real host address. |
| `homeassistant_api` | true | The services call Core through the Supervisor proxy with `SUPERVISOR_TOKEN`. |
| `privileged: [NET_ADMIN]` | | Required for the firewall feature; a real CAP_NET_ADMIN is the only way a container can run iptables against the host's tables, Protection Mode or not. |
| `docker_api` | true | Exists for the optional resource hard-cap feature. Declaring it sets the Supervisor security rating to 1 unconditionally, a deliberate documented choice (the privilege ledger is in ha_soc_probe/DOCS.md and the README). With Protection Mode on (the default) the socket is not mounted and every cap reports `denied`; applying caps requires disabling Protection Mode on this add-on, a root-equivalent grant the panel spells out first. Users who do not use hard caps lose nothing by leaving Protection Mode on. |
| `options.scan_interval_hours` | 6 (schema `int(1,24)`) | Port-scan period; read once as root through `bashio::config` and passed to the unprivileged loop as `HA_SOC_SCAN_INTERVAL_HOURS`. |
| `init: false`, `startup: services`, `boot: auto` | | s6-overlay services, started with the Supervisor's other services, on boot. |
| no `image:` key | | The add-on is built locally by the Supervisor from the Dockerfile; consequently `signed: false` (see `decisions.md`). |

### Runtime knobs

| Constant | Value | Meaning |
| --- | --- | --- |
| `RETRY_INTERVAL_SECONDS` / `MAX_RETRY_INTERVAL_SECONDS` (scanner) | 30 / 300 | Rejected-report retry doubles each attempt up to the cap and resets after a success. |
| `POLL_INTERVAL_SECONDS` (firewall) | 5 | Poll period for firewall and resource-cap work. |
| `WINDOW_MIN_SECONDS` / `WINDOW_MAX_SECONDS` | 5 / 3600 | Bounds on the confirm window Core may deliver; Core's default is 45 s. |
| `MAX_RULES` | 200 | Rule-count cap, mirroring Core's `RULES_SCHEMA`. |
| `REASON_MAX_CHARS` | 200 | Must equal `FIREWALL_REPORT_REASON_MAX`. |
| `LIMIT_APPLY_EVERY` | 12 (x 5 s, about 60 s) | Resource caps are re-applied on this cadence. |
| `POLL_INTERVAL_SECONDS` (SNMP) | 30 | SNMP config poll period. |

State files under `/data`: `ha_soc_probe_secret` (0600, root-owned); `ha_soc_fw_current_test_id`; `ha_soc_fw_backup_<id>.rules` and `ha_soc_fw_backup6_<id>.rules` (full filter-table dumps for manual recovery only; no code path feeds them to iptables-restore); `ha_soc_fw_chain_<id>.rules` and `ha_soc_fw_chain6_<id>.rules` (the chain snapshots a revert replays); `ha_soc_fw_resolved_<id>`; `ha_soc_resource_limits.json` and `.applied`; `ha_soc_snmp/{config,persistent,generation,state.json}` (mode 700 directories).

### Troubleshooting

- "Holding, HA SOC did not accept the report (HTTP 400)" means the integration's service is not registered yet (not loaded, or Core mid-restart); the add-on retries on its own. Health's `probe_addon_not_reporting` fires only for a setup that never reported at all.
- "s6-setuidgid not found; the port scanner is running as root this session" is degraded-but-running: a degraded scanner that says so beats no scanner.
- "ip6tables is not functional on this host" at firewall startup means the IPv6 halves of rules are skipped and every report carries `firewall_ipv6_supported=false`; the panel marks affected rules partially applied.
- Resource caps reporting `denied` mean the Docker socket is not mounted: enable `docker_api` and disable Protection Mode on the Probe.
- The finish scripts log "stopped cleanly" for exit 0 and "exited with code N; s6 will restart it" otherwise, so a routine update does not read as a crash loop.
- Uninstall: the Supervisor offers no verified hook that runs on uninstall, so removal of the `HA_SOC_RULES` chains and their INPUT jumps is best-effort. A clean uninstall leaves an empty chain and one INPUT jump per family, which is inert; the add-on documentation describes the manual cleanup.
- Bumping the base image: re-resolve with `docker buildx imagetools inspect ghcr.io/home-assistant/base:<tag>` and replace tag and digest together, never the tag alone.
- Detection `probe_auth_rejected` with reason `no_secret` means an outdated Probe build; update it. Reasons are `not_supervisor`, `no_secret`, `bad_secret`, logged at WARNING at most once per caller per 600 s (`_REJECT_WARN_INTERVAL_SECONDS`).

### Verification script

Run `scripts/ha_soc_verify_supervisor.sh` from the Terminal & SSH or Advanced SSH & Web Terminal add-on: `bash ha_soc_verify_supervisor.sh | tee ha_soc_verify_$(date +%Y%m%d).txt`, then paste the whole output into the review thread and review every `FACT` line against work plan section 6.2. Two levels of detail: the Supervisor API level always works via the `ha` CLI; the container level needs the `docker` CLI and is available only when the SSH add-on runs with Protection Mode disabled, exactly the condition the `addon_unprotected` check flags, so re-enable Protection Mode afterwards. Set `PROBE_NAME` if the add-on is installed under a different name; `jq` is optional. The backup section reports only whether a default backup password and per-agent protection are set, never a value.

## CI and release

- requirements-test.txt pins the harness, which brings Home Assistant core 2026.2.3; the home-assistant-frontend pin must match the version in that core's `package_constraints.txt`, so bump both in the same change (work plan section 7). The live Core is 2026.8.3; D-16 suggests bumping the harness pin next sprint.
- The hacs/action digest in validate.yml is bumped deliberately when the weekly run starts failing on new HACS requirements; the hassfest digest likewise tracks head of master.
- Bandit runs at `-ll` over `custom_components/ha_soc` with B104 skipped.
- The compliance evidence artifact is retained 90 days on GitHub; `COMPLIANCE_ADMIN_TOKEN` (optional, fine-grained, read-only, Administration-read) makes the immutable-releases setting observable. The "Reject incomplete collection" step fails the run when the pack is partial or records a control deviation, after the artifact is uploaded.
- prepare-release.yml needs `RELEASE_AUTOMATION_CLIENT_ID` (repository variable) and `RELEASE_AUTOMATION_PRIVATE_KEY` (secret); see `automated-calver-release-design.md`.
- `scripts/release.sh` usage: no argument for today's date and next revision; `scripts/release.sh v2026.08.30.2` for an explicit version (the bare form works too); `--skip-tests` skips the pytest gate (not advised). The working tree must be clean; on main the script creates `release/v<version>`; `gh` must be authenticated. The three lockstep fields are manifest.json `version`, ha_soc_probe/config.yaml `version:`, and `SCANNER_VERSION` in the port-scanner run script. The script's final message records the first-time HACS cache clearing step and the private-repo authentication note.

## Unverified

Operational claims carried from code comments that were not re-verified in this pass:

- const.py:128-129: `DEFAULT_UNIFI_VERIFY_SSL` is "the same default Home Assistant's own official UniFi integration uses".
- const.py:336-337: "The user asked for '30-60 seconds'" for the firewall test window.
- const.py:309-310: "the add-on truncates to this same length before sending (head -c in the run script)".
- .github/workflows/test.yml:37: "The harness pin brings Home Assistant core 2026.2.3"; requirements-test.txt was not inspected by the pass that recorded it.
- ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run (pre-edit line 49): the probe secret "was found at 0644" on the first live verification run, a historical observation behind the chmod.
