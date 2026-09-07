# Protocol

Wire and device facts: Supervisor endpoints, WebSocket message shapes, external API response shapes, USB and serial facts, the Probe add-on protocol, and the audit chain's on-disk format. Three topics have their own contract documents and are only pointed at here:

- CEF and RFC 5424 syslog export: `CEF-SCHEMA.md`.
- SNMPv3 agent, MIB objects, and credential shapes: `SNMPV3.md` (its "Agent and wire facts" section holds the facts moved from code).
- UniFi Local Integration API paths and verified schemas: `UNIFI-LOCAL-API-CONTRACT.md` (its "Verified response shapes" section holds the facts moved from code).

## Supervisor and Home Assistant core surfaces

### Probe callbacks through the Supervisor proxy

The add-on reaches Core only through the Supervisor's core-API proxy: `POST http://supervisor/core/api/services/ha_soc/<service>` with `Authorization: Bearer SUPERVISOR_TOKEN`, the same mechanism any add-on uses. The proxy forwards every call under the Supervisor system user's own token and passes no add-on identity, so Core requires exactly that context (see `security.md`). The three services are `ingest_probe_result` (periodic port, firewall, resource, and SNMP status), `poll_firewall_command` (the fast firewall command channel, `return_response=True`), and `poll_snmp_config` (a separate, slower response-returning channel so the two state machines cannot interfere; steady-state polling returns only `enabled` and `generation`, never passphrases).

`_INGEST_SCHEMA` fields:

| Field | Meaning |
| --- | --- |
| `open_ports` | Optional: the firewall poller also calls this service purely to report firewall state and must never be forced to send a port list; the handler touches `store.data["host_probe"]` only when it is present, so a firewall-only report never stomps the scanner's slower data. |
| `firewall_known_rules`, `firewall_resolved_test_id`, `firewall_resolved_status` | All optional so an add-on predating the firewall feature keeps reporting ports. `firewall_known_rules` rides on the regular cycle; the resolution fields are sent out-of-cycle right after a confirm or revert. |
| `firewall_resolved_reason` | Bounded free text: `backup_failed`, or the failing rule and family. Bounded to `FIREWALL_REPORT_REASON_MAX` because it is add-on-supplied text that is stored and rendered; the add-on truncates to the same length. |
| `firewall_ipv6_supported` | Whether `ip6tables -S` works on the host, once per cycle. Optional for pre-dual-stack builds (work item 2.4). |
| `resource_limit_state` | `{slug: {"status": applied|failed|denied, "detail": str|None}}`. Optional. |
| `snmp_status` | Non-secret runtime state from the snmpd supervisor. |
| `probe_secret` | Shared secret, defense in depth. Optional in the schema so its absence reaches the handler and is audited as `no_secret` instead of failing validation. |

`_PORT_SCHEMA` `address` and `interface`: the bind address decoded from `/proc/net/tcp[6]` (for example `192.168.10.5`, or `0.0.0.0` meaning every interface) and, for a non-wildcard IPv4 address, a best-effort match against the host's `ip addr` output. Both optional: older add-ons predate them, and IPv6 addresses are reported without decoding. The `poll_firewall_command` response gains a `resource_limits` key only when caps are configured; an older Probe ignores it.

The Supervisor user id is read first from the hassio component's config store (`hass.data[DATA_CONFIG_STORE].data.hassio_user`, verified against core 2026.2.3, components/hassio/__init__.py:341-361); `DATA_CONFIG_STORE` is internal, so the import is guarded and the fallback is the auth registry's system-generated user named `HASSIO_USER_NAME` ("Supervisor").

### Container stats and logs

The Supervisor exposes a live `/stats` per container. `_STAT_FIELDS` are aiohasupervisor's `ContainerStats` fields (`cpu_percent`, `memory_usage`, `memory_limit`, `memory_percent`, `network_rx`, `network_tx`, `blk_read`, `blk_write`), read from `client.addons.addon_stats(slug)`, `client.homeassistant.stats`, and `client.supervisor.stats`; a value the Supervisor omits stays None. Container logs use the fixed journald paths `/core/logs`, `/supervisor/logs`, `/host/logs`, and `/addons/<slug>/logs` for `addon:<slug>` targets, via `hassio.send_command(path, method="get", return_text=True, timeout=_LOG_FETCH_TIMEOUT)`; the transport quirks (no `Range` header, ANSI SGR stripping) are in `OPERATIONS-NOTES.md`. Log target ids are `core`, `supervisor`, `host`, and `addon:<slug>`.

### Fault log

`home-assistant.log.fault` is written by Python's faulthandler, enabled by `homeassistant/__main__.py` for the process lifetime. It writes only on a fatal signal (SIGSEGV, SIGABRT, SIGBUS, SIGILL, SIGFPE), never a normal exception. `__main__.py` deletes the file if empty after a clean shutdown, but a crashing session never reaches that code, and the file is reopened in append mode on every start, so a non-empty file means at least one crash and it grows until cleared by hand. logs.py only reads it. `fetchSystemLog` mirrors `system_log`'s `LogEntry.to_dict()` exactly (name, message, level, source, timestamp, exception, count, first_occurred), the same WARNING+ dedup buffer behind Settings > System > Logs.

### Supervisor add-on facts

- "Protected mode" is a generic add-on setting; disabling it grants the container elevated Supervisor API access.
- The official Terminal & SSH add-on (`core_ssh`) ships with its port unbound (ingress-only); a host-bound port (`network` map) or `host_network` means direct SSH that bypasses Home Assistant's login.
- The cached add-on info (aiohasupervisor `InstalledAddonComplete`, checked against core 2026.2.3) carries no volume-map field, so "does this add-on map config" cannot be read from data.
- aiohasupervisor's `AddonsClient` offers info, stats, options, security, start, stop, restart, rebuild, uninstall, and stdin; nothing sets limits.
- The Supervisor recreates an add-on's container on every update or restart, which drops Docker-level limits and can make the container name transiently absent.
- The `ha` CLI wraps every `--raw-json` payload in `{"result": ..., "data": {...}}`; `.data` must be unwrapped first or every field prints null (seen on Supervisor 2026.08.0). The add-on info keys `ha_soc_verify_supervisor.sh` extracts (`name, version, state, rating, protected, host_network, host_pid, host_uts, host_dbus, privileged, docker_api, full_access, apparmor, auth_api, homeassistant_api, hassio_api, hassio_role, ingress, network, signed, repository, auto_update, watchdog, boot, ip_address`) are what `get_addons_info()` caches.
- `PROBE_ADDON_NAME` is matched exactly against `get_addons_info()`'s per-addon `name` field, since slugs are repository-derived.

### Core auth, lovelace, and config facts

- `trusted_users` maps a network to a list of user-id hex strings or `{"group": group_id}` dicts (verified against core 2026.2.3's trusted_networks provider). `.storage/backup` carries `config.create_backup.password` and `config.agents[<id>].protected` (verified against core 2026.2.3 components/backup/config.py and store.py).
- The default dashboard's `url_path` is None, which Store serializes as the literal string "null" and never converts back; permissions.py uses the sentinel `"__default__"` everywhere it reads or writes the store.
- `ConfigNotFound` from `lovelace_config.async_load` means "registered but never saved", a normal state, logged quietly; every other `HomeAssistantError` keeps the louder log. Writing an empty `visible` list means "visible to no one", a different state from a reset, so a reset writes `visible: True` instead.
- `lovelace/resources.py` (core 2026.2.3): `async_load()` never sets `loaded` itself; each core call site (`async_get_info`, `_update_data`, the resources WS command) calls it and then sets the flag, which is why config_hygiene reads through `async_get_info()`.
- `auth_ha.async_get_provider` is synchronous despite the `async_` prefix, and that convention has flipped before, so users.py tolerates either shape. `hass.auth.async_deactivate_user` also revokes all of the user's refresh tokens. `hass.auth.async_update_user` raises `ValueError` or `HomeAssistantError` for system-generated users among other invalid updates.
- `load_yaml` without a Secrets object raises `HomeAssistantError` ("Secrets not supported in this YAML file") on `!secret`; `!include` is resolved at load time, so a write-back would inline it (core 2026.2.3, work plan section 6.1). `script.reload` and `scene.reload` are registered with an empty schema; `automation.reload` accepts `{"id": ...}`.
- `Store`'s signature is `Store(hass, version, key)`; `Store[T](...)` parses as a Subscript callee. `_CORE_HASS_DATA_KEYS` in scanner.py was collected from `HassKey("...")` registrations in `homeassistant/*.py` and `homeassistant/helpers/*.py` of core 2026.2.3.
- aiohttp routes live for the process lifetime; `async_remove_panel()` removes only the sidebar registration, and re-adding the GET route raises `RuntimeError` ("Added route will never be executed" or "method GET is already registered").
- Home Assistant's ban warning on core 2026.2 is a fully formatted f-string ("Login attempt or request with invalid authentication from <host> (<addr>). Requested URL: ...") logged with no args, so `_BAN_MESSAGE_RE` on the formatted message is the live extraction path; the structured-args branch in `_extract_ip` is a compatibility path.

## WebSocket message shapes

- `ws_users_revoke_all_sessions` returns `{"revoked": {"sessions": N, "long_lived_tokens": M}}`. `ws_users_set_password` accepts `revoke_sessions` (default True) and returns `{"ok": True, "sessions_revoked": N}`; the client always sends the flag explicitly so the audit record reflects a choice. `ws_detections_bulk_set_status` returns `{"updated": <count>, "missing": [<ids>]}`.
- `ws_logs_container`'s audited target is the bare slug for an add-on or `core` / `supervisor` / `host`. `ws_containers_resources` returns `available=False` on a non-Supervisor install rather than erroring; `SocContainerResources` stat fields are null when unreported, and `memory_usage` and `memory_limit` are bytes.
- `ws_watchdog_set` `override` payload: a slug plus any subset of the fields; `clear=True` removes the override. `hard_limit` payload: `memory_mb` and `cpus` both None (or missing) clears the cap; the cap is applied by the Probe. A cap's `status` is `applied`, `failed`, `denied`, or `unknown`.
- `ws_settings_set`: a secret field left as `REDACTED_PLACEHOLDER` ("[redacted]") means unchanged; an empty string clears the secret. UniFi and Pi-hole host fields accept a string or None; None or "" clears the connection. `iot_cidr` is plain. Syslog facility is 16 through 23. The SNMP configuration can only represent an explicit unicast listener and SNMPv3 AuthPriv. `_masked_settings` returns every secret key as the placeholder (when set) or "" (when unset) plus a `<key>_set` boolean. `SocSettings` mirrors store.py's `SettingsData` exactly. `detection_thresholds` is sparse; send only the fields being changed.
- `fetchDetectionThresholds` returns per rule and parameter the effective value, secure default, inclusive min and max (null for booleans), and input type. Bulk detection dismissal is one action producing one audit record carrying the id list. `fetchAuditStats` returns per-category counts and byte shares for the newest day only. Audit verify result: `verified_from_seq` is 1 when the whole chain was re-checked and greater when verification restarted at the retention anchor.
- Per-user risk result: `{user_id, score, band, factors}`, each factor `{name, points, applied_points, detail}`; `applied_points` is optional so an older backend still renders and the values sum exactly to `score`. Posture result: `{score, grade, provisional, missing_terms, term_computed_at, breakdown: {p_user, p_vuln, p_misconfig, p_integration, p_detection}}`, score `100 - round(0.35 p_user + 0.25 p_vuln + 0.20 p_misconfig + 0.10 p_integration + 0.10 p_detection)` clamped to 0-100, grades A at 90 or above, B 80, C 70, D 60, else F. Posture history keeps 90 daily `{date, score, grade}` snapshots with a local calendar date.
- Detection rows: `id` (sha256 of `rule_id:subject:bucket` truncated to 24, bucket the UTC hour floor), `rule_id`, `severity`, `user_id`, `ip`, `ts`, `last_seen`, `status`, `recurrence_count`, `trigger_event_ts` (capped at 200), `title`, `detail`. `login_ok` audit records carry `detail.new_token`; `probe_auth_rejected` records carry `detail.caller_user_id`, `detail.service`, and `detail.reason`.
- Scanner finding: `{id: "<domain>:<sha256(rel_path:lineno:pattern)[:16]>", domain, file, line, snippet, pattern, cwe, confidence, severity, first_seen, last_seen, status}` plus `acknowledged` and optional `acknowledged_reason`. Confidence maps high to high, medium to medium, advisory to info. Coverage record `{scanned_files, skipped_oversize, skipped_over_cap, parse_failures, scanned_at}` per domain under `scanner_coverage`; `ScannerListing.coverage` is optional so a pre-coverage backend still parses. Acknowledgment marker: `# ha-soc-allow: <pattern_id> <reason>` on the flagged line or the one above; the reason is truncated to 200 characters.
- Integration security overview: `{github_configured, hacs_installed, hacs_source_introspectable, tier_counts, integrations: [{domain, name, tier, is_custom, quality_scale, integration_type, version, license_present, repo_url, flags, scanner_findings, github}]}`. Cached GitHub signal: `{stars, forks, archived, pushed_at, commit_verified, has_release, latest_release_tag, collected_at}` under `integration_security.github[owner/repo]`. Refresh summary: `{ok, refreshed, skipped, cache_fresh, invalid_slugs, reason?}`, reason `no_github_token` or `rate_limited`; `invalid_slugs` is a count, and the three count fields are absent on the no-token early return.
- `SocUser.mfa_assessable` is false when every credential comes from a non-homeassistant provider (D-18). `ISSUE_CATEGORY` is at most one per integration, priority credential > failing > communication > collection > errors > debug_logging > disabled. `DEVICE_STATUS_*` is live availability, a separate axis from severity. Security-overview entity rows: `state` null on a registry entity with no state object, always with `problem` true and `reason` "no state (integration not loaded)"; `reason` is null on a healthy row.
- Firewall types mirror `RULE_SCHEMA`: `family` "4", "6", or "both", optional on the wire and derived from the source (an IPv4 source pins "4", IPv6 "6", none defaults to "both"; a contradicting value is rejected); `partially_applied` is set by the server at read time while `ipv6_supported` is false. Pending statuses: `expired_unreported` (display-only until the add-on's report archives it), `expired` (the pre-rename spelling), `discarded_unreported` (history only). `applied_at` is null until the add-on applies; `expires_at` is propose time plus window until then, re-anchored to `applied_at` plus `window_seconds` afterwards. `resolution_reason` appears only on archived records. `ipv6_supported` is null until any report carried the field. `applyFirewallRules` requires `backup_acknowledged` server-side. `EntityRemapApplyResult.backups` lists pre-rewrite snapshots under `.storage/ha_soc_remap/` (kept 30 days), optional for older backends.
- Probe report `bind_address` is absent or null from an older add-on or for an IPv6 listener. `SocResourceWatchdog` actions are alert, restart, stop, with restart and stop add-ons only.
- UniFi types: every per-row field is nullable and renders as a dash; `uptime` is seconds, `last_seen` epoch seconds; the Devices table drops IPv6 and uptime and shows `firmware_updatable`. `filter_type` is "IPV4" or "MAC"; `origin` is `metadata.origin` verbatim plus a derived `custom` (true only for USER_DEFINED, null when origin was not reported). `auto_allow_return_traffic` is ALLOW-only, null for BLOCK/REJECT. Protect `last_ring`, event `start` and `end` are epoch seconds, `duration` seconds; `console_url` is a deep link such as `https://<console>/protect/dashboard/devices/<id>`.
- `ws_firewall_discard_pending` is refused with `window_not_lapsed` while the countdown runs. `ws_watchdog_set` refuses `not_supervisor` off Supervisor and `addon_not_installed` for an unknown slug. permissions.py failure reasons: `lovelace_internals_unavailable`, `dashboard_not_found`, `dashboard_load_failed`, `view_not_found`, `yaml_dashboard_read_only`, `dashboard_save_failed`, `dashboards_collection_unavailable`, `dashboard_update_failed`, `sidebar_store_unavailable`. `ha_soc/permissions/dashboard_config` sends a `not_found` error for a dashboard with no saved config.

## Audit chain on-disk format

Each record's hash is `sha256(prev_hash + json.dumps(record, sort_keys=True))` over the record without its hash field; `prev_hash` is the previous record's hash and `_GENESIS_PREV_HASH` is the empty string. `chain_head.json` carries `{prev_hash, seq}` plus optional `anchor` and `reset` dicts. The retention anchor is `{seq, hash, expired_through, expired_at}`: the newest record whose day file retention deleted. The reset marker is `{seq, hash, at, disk_head_seq}`: the store-mirrored head a wiped or rolled-back chain was continued from. Both are kept in memory (`_anchor`, `_reset`) so every head rewrite preserves them; the anchor is None until retention first deletes, and the reset marker clears only when retention expires the reset point. `_head_file_found` distinguishes "directory wiped" from "head rolled back". Both must be restored across restarts: dropping the anchor would break verification after expiry, and dropping the reset marker would make a wiped chain verify clean (work item 1.5).

Verification result fields: `ok`, `records_checked`, `first_break_seq`, `reason`, `verified_from_seq`, `expired_through`, plus extras per failure. `reason` values: `corrupt_record`, `hash_mismatch`, `anchor_inconsistent`, `chain_reset` (with `store_head_seq` and `checkpoint_seq`, or `reset_seq`), and `tail_truncated` (with `checkpoint_seq` and `last_on_disk_seq`). The store mirror `audit_head` is `{seq, hash, at}`.

## External APIs

### NVD

Endpoint `https://services.nvd.nist.gov/rest/json/cves/2.0`, queried with `virtualMatchString` (a curated CPE prefix such as `cpe:2.3:o:shelly:*`) or `keywordSearch` (`"<manufacturer> <model>"`), plus `resultsPerPage` (20) and `startIndex`; the optional key travels in the `apiKey` header. The response carries `vulnerabilities[]` (each with `cve.id`, `cve.descriptions[]` with `lang` and `value`, and `cve.metrics.cvssMetricV31|cvssMetricV30|cvssMetricV2[].cvssData.baseScore`) and `totalResults`. Rate limits: about 5 requests per 30 s without a key, about 50 with one; `NVD_DELAY_NO_KEY` (6 s) and `NVD_DELAY_WITH_KEY` (0.7 s) apply after every real HTTP call, with headroom. A 429 means NVD is actively asking to slow down: one bounded retry (`NVD_MAX_RATE_LIMIT_RETRIES` = 1) honors `Retry-After` in seconds form only (NVD does not send the HTTP-date form); when retries are exhausted the query stops with the pages collected, and a 429 body is never parsed. `NVD_TIMEOUT_SECONDS` is 15. Firmware findings have id `<device_id>:firmware_outdated`, severity medium, confidence heuristic, source "heuristic"; CVE findings have id `<device_id>:<cve_id>`, source "nvd". Summaries are truncated to 500 characters.

### GitHub

Provenance requests carry `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, and `X-GitHub-Api-Version: 2022-11-28`, timeout 15 s. Per repo: `/repos/{owner}/{repo}` (`stargazers_count`, `forks_count`, `archived`, `pushed_at`, `default_branch`), `/repos/{owner}/{repo}/commits/{default_branch}` (`commit.verification.verified`), and `/repos/{owner}/{repo}/releases/latest` (`tag_name`; 404 means no release). A 404 on the repo object yields `{"error": "not_found"}`. A 403 with `X-RateLimit-Remaining: 0` means the quota is exhausted. The token raises the limit from 60 to 5,000 requests per hour. `_GITHUB_REPO_RE` tolerates trailing `/issues`, `.git`, and slashes. HACS runtime data is read from `hass.data["hacs"].repositories.list_all`, each repo's `data.domain` (or `data.full_name`) and `data.default` / `repo.is_default`.

Workflow endpoints: `/repos/<repo>/branches/main` is readable with the read-only `GITHUB_TOKEN` and exposes `protected` and `protection.required_status_checks`; `/repos/<repo>/immutable-releases` (header `X-GitHub-Api-Version: 2026-03-10`) requires Administration-read; `/repos/<repo>/code-scanning/alerts?state=open&per_page=100` is summarized by `rule.security_severity_level`, with `result_truncated` set when exactly 100 came back.

### Pi-hole v6

Paths, auth flow, and field names follow pi-hole/FTL's published OpenAPI spec (the one `http://pi.hole/api/docs` serves, generated from `src/api/docs/content/specs/*.yaml`). `POST {base_url}/auth` with `{"password": <app password>}` returns `{"session": {"valid", "sid", "csrf", "validity", "message", "totp"}}`. The `sid` rides on the `X-FTL-SID` header on every call (FTL's `x_header_sid` scheme; a query parameter would leak into proxy access logs). A session is created per snapshot and logged out with `DELETE {base_url}/auth`. An open API with no password is not supported; a password accepted with no sid indicates 2FA, also unsupported. Endpoints read: `/dns/blocking` (`blocking` as "enabled"/"disabled"), `/stats/summary` (`queries.total`, `queries.blocked`, `queries.percent_blocked`, `queries.unique_domains`), `/groups` (`groups[]` with `id`, `name`, `enabled`, `comment`), `/clients` (`clients[]` with `client`, `name`, `comment`, `groups[]`), `/stats/top_domains?blocked=true&count=N` (`domains[]` with `domain`, `count`), and `/stats/recent_blocked?count=N` (`blocked[]`). Group 0 "Default" is always present; a client carrying only `[0]` has no dedicated group, the "not scoped" signal. A client identifier may be an IP, CIDR, MAC, hostname, or interface (`:eth0`); only IP and CIDR forms are matched against the IoT CIDR. Redirects are never followed; bodies are bounded by declared length and actual read (4 MiB); per-request timeout 15 s, whole snapshot 30 s.

### Core UniFi in-memory objects

Network reports MACs as `aa:bb:cc:dd:ee:ff` and Protect uppercase without separators; `normalize_mac` lowercases and colon-separates before any join. The aiounifi `uptime` field is sometimes a duration and sometimes an epoch start; `_EPOCH_THRESHOLD` (1,000,000,000) disambiguates as core does. Protect hands out datetimes, Network epoch ints. uiprotect uses string enums (`.value`), aiounifi IntEnums (`.name`). `OFFLINE_DEVICE_STATES` are DISCONNECTED, HEARTBEAT_MISSED, ISOLATED. `hass.data["unifi_wireless_clients"]` is core's registry of wireless MACs. aiounifi handler containers are not dicts; `.values()` is the way in. Raw client keys `rx_bytes-r` / `tx_bytes-r` are wireless rate counters and `wired-rx_bytes-r` / `wired-tx_bytes-r` wired ones, bytes per second; a gateway's `uplink` dict is the WAN interface (`ip`, `*_r` rates); `uptime_stats` holds WAN monitors, with `availability` the WAN-up percent and `internet` the controller's verdict; `network_table` rows are read with `_id`, `name`, `vlan`, `vlan_enabled`, `ip_subnet`; a Wlan object carries `x_passphrase`; Protect lands an LPR match in `detected_thumbnails[].group.matched_name`.

## USB and serial devices

`scan_serial_ports()` (`homeassistant.components.usb.utils`) returns both `USBDevice` and `SerialDevice` objects; the split and the `resolved_device` field (backed by the `serialx` library) exist on core 2026.9.0 (`usb/models.py`). Only `USBDevice` has `vid` and `pid`; `SerialDevice` (native ports) has neither, and `getattr` degrades both to None on an older core or a genuine `SerialDevice`. `_scan_and_resolve` falls back to `os.path.realpath(device.device)` on a core lacking `resolved_device`. `_device_key` is `vid:pid:serial` (`noserial` when missing) for USB and `native:<resolved_device>` otherwise; `by_id_path` is `device.device` when it differs from the resolved tty.

## Probe add-on protocol

### Port scanner

- `/proc/net/tcp` and `/proc/net/tcp6`: column 2 is `hex_bind_address:hex_port`, column 4 the state, `0A` TCP_LISTEN.
- The IPv4 bind address is 8 hex chars in the kernel's little-endian word order: `0100007F` is 127.0.0.1. IPv6 is 32 hex chars, four little-endian 32-bit words, materially harder to decode, so it is reported with `address: null, interface: null`.
- 0.0.0.0 is reported with interface `(all interfaces)`; an address absent from `ip -4 -o addr show` is `unresolved`.
- Report: `POST .../services/ha_soc/ingest_probe_result` with `{open_ports: [{"port", "proto", "address", "interface"}], scanner_version, probe_secret}`. HTTP 200 is accepted; any other code (curl failure reported as `000`) enters the retry loop.

### Firewall poller

- Poll: `POST .../services/ha_soc/poll_firewall_command?return_response` with `{current_test_id, probe_secret}`; the response's `.service_response.action` is `apply`, `confirm`, `revert`, or absent (`none`), with `.test_id`, `.rules` (`[{action, proto, port, source, family}]`), `.window_seconds`, and optionally `.resource_limits.limits`. Core answers `{"action": "none", "reason": "addon_holds_other_test"}` when the add-on holds a different test.
- Resolution report: `{firewall_known_rules, firewall_ipv6_supported, firewall_resolved_test_id, firewall_resolved_status, firewall_resolved_reason, probe_secret}`. `firewall_resolved_reason` is truncated to `REASON_MAX_CHARS` = 200, which must equal `FIREWALL_REPORT_REASON_MAX` or the report bounces off Core's schema; an empty reason is sent as null. Statuses: `confirmed`, `reverted`. Reasons: `backup_failed`, `rejected by add-on: rule count out of bounds`, `rejected by add-on: rule N has an invalid action, proto, port, or family`, `rejected by add-on: rule N has an invalid source for family F`, `rejected by add-on: window_seconds out of bounds`, and `rule N (<action> <proto>/<port> family F) failed to apply in <binary>`.
- `known_rules` entries carry `family` "4" or "6" per table; `action` is `allow` for ACCEPT and `deny` otherwise (DROP is what `apply_rule` writes).
- `FIREWALL_RULE_FAMILY_*`: "4" is written with iptables, "6" with ip6tables, "both" with both, always into `HA_SOC_RULES`. `FIREWALL_RULE_ACTIONS` are allow and deny; `FIREWALL_RULE_PROTOS` tcp and udp. The chain snapshot is iptables' own `-S` output; only `-A HA_SOC_RULES ...` lines are replayed. Core-side `_valid_source` accepts None or a real IP or CIDR via `ipaddress.ip_network(value, strict=False)`.
- Core writes `firewall_resolved` (actor_source `addon`, `user_id` None, `reported_rule_count` the size of the known-rules snapshot or None) when a test moves to history via the report path, and `firewall_pending_discarded` naming the owner for the discard path.
- Resource-limit report: `{resource_limit_state: {<slug>: {status, detail}}, probe_secret}`.
- Docker Engine API over `/var/run/docker.sock`: `POST http://localhost/containers/addon_<slug>/update` with `Memory`, `MemorySwap`, `NanoCpus` (memory bytes = memory_mb x 1048576, NanoCpus = cpus x 1e9). `0` means unlimited (the reset body also sends `CpuShares: 0`). `MemorySwap` must equal `Memory` or Docker rejects the update, and a cap the container can dodge by swapping is not a cap. HTTP 200 is applied, 404 container not found, curl `000` socket unreachable.
- s6 behavior relied on: every service starts as root; SIGTERM on every stop, restart, and update; the finish script receives the exit code as `$1`; a non-zero exit is restarted once finish returns.

## External audit ingest

`ha_soc.ingest_audit` accepts hash-chained audit records from another tool on the
host, today the Elk Programmer app. The caller must carry the Supervisor user's
context (an app reaching Core through `http://supervisor/core/api/services/ha_soc/ingest_audit`
with `SUPERVISOR_TOKEN`) and present `secret`, pinned per `source` on the first
accepted call and compared with `hmac.compare_digest` after that; the pinned
secrets live as one JSON map under the `external_audit_secrets` key of the secret
store. Registered only on Supervisor installs, like the Probe services.

Request: `{source, secret, records: [{seq, time, event, user_id, user_name, details, previous, hash}]}`,
1 to 200 records in sequence order; `source` matches `^[a-z][a-z0-9_]{0,31}$`.

Record contract: `hash` is SHA-256 over the canonical compact JSON
(`sort_keys`, separators `,` and `:`) of `{time, event, user_id, user_name, details, previous}`
followed by `previous`; the first record's `previous` is the empty string. This is
exactly what the Elk Programmer's audit log writes, so its file verifies unchanged.

Per source HA SOC keeps `{seq, hash, at}` of the last accepted record in the store
(`external_audit_heads`). Each record is checked in order: a sequence at or below
the head is a replay and is skipped, unless it carries a different hash under the
head's own sequence (`rewritten_history`); a sequence above `head + 1` is `gap`
(the link to the missing records cannot be verified); `previous` must equal the
head's hash (`previous_hash_mismatch`); the recomputed hash must match
(`hash_mismatch`); `details` above 8192 bytes of JSON is `details_too_large`.
Accepted records become `external_audit` entries in HA SOC's own chain carrying
the source's sequence, hash, time, event, user id, and details (redacted at the
usual chokepoint). The first failure stops the batch and writes one
`external_audit_chain_break` record; a rejected caller writes
`external_audit_rejected`.

Response (`return_response`): `{accepted, last_seq, rejected}`; `last_seq` is where a
source resumes after a gap.

HA SOC also records `elkm1.programming_started` and `elkm1.programming_ended` bus
events as `programming_session` entries (phase, source, purpose, attributed,
rp_seen), so an unattributed panel programming session is in the same chain.

## Unverified

Wire and platform claims carried from code comments that were not re-verified in this pass:

- audit.py:403-406: "On core 2026.2, http/ban.py builds the invalid-auth warning as a fully formatted f-string ... and logs it with NO args".
- audit.py:95-96: "no bus event exists for these - confirmed against the installed core source"; audit.py:1109-1110: "There is no bus event for either a successful login or a new long-lived access token - confirmed against core's dev branch"; audit.py:120-123: "core updates last_used_at and last_used_ip only on the /auth/token grant path".
- permissions.py:13-15: "There is no permission check on that command [`lovelace/config`] in Home Assistant core as of the 2025.x/dev branch this was written against".
- users.py:307-308: "Core's async_remove_user does NOT block removing the owner (verified)", the original author's verification.
- scanner.py (original lines 380-387): "every string below was collected from the HassKey(...) registrations in homeassistant/*.py and homeassistant/helpers/*.py of core 2026.2.3".
- health.py `_CONFIG_MAPPING_ADDON_MARKERS`, `_check_config_mapping_addons`, `_async_privileged_trusted_users`, `_check_backup_protection`, probe.py `_async_supervisor_user_id`, config_hygiene.py `async_lovelace_missing_resources`, and entity_remap.py `_yaml_text_tainted` and the reload-schema comment all cite verification against core 2026.2.3; not re-verified against core 2026.9.0.
- unifi.py module docstring: "the exact per-field shape of that API's client/device objects could not be verified against a live controller from this environment"; the individual keys are the VERIFY entries in `backlog.md`. `correlate_server_ports_with_rules`: "the Integration API's network list was not confirmed to expose per-network IP subnets". `_normalize_firewall_traffic_filter`: REGION, VPN_SERVER, SITE_TO_SITE_VPN_TUNNEL, and IPV6_IID nested field names "this project hasn't verified". data/ha-soc-ws.ts (original lines 531-534) repeats the same admission.
- unifi_core.py `network_snapshot`: "VERIFY: network_table row id key" (`_id`) and "VERIFY: numeric VLAN id key" (`vlan`).
- pihole.py module docstring (original lines 19-29): the spec was checked but the authoring environment could not reach `http://pi.hole`, so every response shape is best available evidence; pihole.py:302: "some builds report a plain boolean `blocking` field instead of the documented enabled/disabled string; tolerate both".
- tests/test_peripherals.py:119-121 and the peripherals `resolved_device` comment: the serialx-backed `USBDevice | SerialDevice` union (the peripherals claim was verified for core 2026.9.0).
- tests/test_entity_remap.py:550-551: "Section 6.1 verified fact: script.reload and scene.reload take an EMPTY schema", consistent with the test running the real services.
- scripts/ha_soc_verify_supervisor.sh:45-46: "seen on the first live run, Supervisor 2026.08.0"; lines 128-129: "the first live run hit exactly that window ('No such container')".
- ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run:67-70: "bashio::config reads /data/options.json, whose read mode for other users is not among the verified platform facts"; run:72-75: "/run/s6/container_environment/*, whose readability as nobody is also not a verified fact".
- ha_soc_probe/rootfs/etc/services.d/ha_soc_probe_firewall/run:68-69 and firewall.py `_derive_rule_family`: "the verified host runs the nf_tables backend for both families and ip6tables works" and "the verified host's LAN and VLAN carry global IPv6" (recorded D-21 facts).
- ha_soc_probe/Dockerfile:5-7: the digest was "resolved on 2026-09-02 from ghcr.io's registry API (anonymous token flow, Docker-Content-Digest of the tag's manifest index)".
- tests/test_unifi.py:555-557: "confirmed against a live controller: acl-rules returned count=0 while the real rules lived under firewall/policies", a historical observation.
