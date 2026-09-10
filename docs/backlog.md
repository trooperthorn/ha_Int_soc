# Backlog

Open items moved out of code comments, dated when they were recorded. Larger sprint planning lives in `HA-SOC-Sprint-Next-Open-Items.md`; this file holds the small, code-adjacent items (VERIFY markers and deferred decisions) so no TODO survives in source.

## Verification against live systems

- 2026-09-03 unifi_core.py `network_snapshot`: verify the `network_table` row id key (`_id`) and the numeric VLAN id key (`vlan`) against a live controller.
- 2026-09-03 unifi.py `_resolve_site_id`: verify the site identifier key; the Integration API uses `id`, legacy `name` and `_id`.
- 2026-09-03 unifi.py `_ipv6_of`: verify the IPv6 field name and shape (`ipv6Addresses` list versus a single string).
- 2026-09-03 unifi.py `_bandwidth_of`: verify byte-counter field names, which differ across surfaces.
- 2026-09-03 unifi.py `_client_ssid`: verify the client-to-broadcast reference key.
- 2026-09-03 unifi.py `_normalize_client`: verify the VLAN field (first-class on some firmwares, nested under `access` on others, otherwise derivable from the network).
- 2026-09-03 unifi.py `_normalize_device`: verify the `firmwareUpdatable` field name and nesting.
- 2026-09-03 unifi.py `_derive_wan`: verify the exact WAN-port or uplink shape on the Integration API device object, the single most uncertain mapping in the file.
- 2026-09-03 unifi.py `_normalize_camera`: verify `isRecording` (boolean versus `recordingSettings.mode`) and the channels shape (name and/or width and height per channel).
- 2026-09-03 unifi.py `correlate_server_ports_with_rules`: confirm whether the Integration API's network list exposes per-network IP subnets, which would allow network-scoped rules to be classified as covered or uncovered.
- 2026-09-03 health.py `_check_samba_config_share`: verify the official Samba add-on's exact option key names against a live Supervisor (plan section 0, rule 5); the check probes the common shapes only.
- 2026-09-03 pihole.py: the `blocking` field may be a boolean on some builds instead of the documented string; confirm against a live instance.

- 2026-09-08 config_ledger.py `_device_rows`: confirm whether a UniFi device's API `id` survives an unadopt and re-adopt. One unadopt and re-adopt on a device that does not matter answers it. The MAC-first key is correct either way, so this only decides whether the id could be used as a secondary check.
- 2026-09-08 UniFi diagnostics scope: confirm the installed controller's `applicationVersion` (now surfaced in the Network Security tab from `GET /info`). The endpoint coverage this integration relies on was read from the v10.4.57 OpenAPI artifacts; a different generation changes the path set.
- 2026-09-08 UniFi diagnostics scope: confirm where the UniFi Network application actually runs. If it is not on the gateway, the IoT-to-Gateway allow rules point at the wrong destination and every device moved to IoT fails provisioning the same way.

- 2026-09-10 ssh_devices.COMMANDS: the access-point tools differ by device generation, observed directly on this estate. U7 Pro `/bin` carries `wifi_list`, `stainfo`, `stamgr -> stainfo` and `ubus`; UDB Pro `/sbin` carries `wstalist -> ubntbox`, `mca-dump -> mca.sh`, `mca-sta`, `amstainfo`, `wpa_cli` and `hostapd -> wpad`. Neither list is the whole device: `tail` and `whoami` are absent from the U7 Pro's `/bin` yet both run there, so every "absent" claim below is scoped to the directory that was listed. The allowlist is overlapping on purpose; an absent tool reports `unknown`.
- 2026-09-10 `/var/log/messages` exists on both generations and `syslog_tail` is verified against both. On an access point serving clients it carries the record no controller API has: UniFi's station tracker (`stahtd`) emits one `STA_ASSOC_TRACKER` JSON object per attempt, with `event_type` (association, success, soft failure, failure), `auth_failures` and `wpa_auth_failures`, `auth_rssi` and `avg_rssi`, per-stage deltas (`auth_delta`, `assoc_delta`, `wpa_auth_delta`, `ip_delta`), `ip_assign_type`, `dns_resp_seen`, and the 802.11 `disassoc_reason` / `deauth_reason`. Parsing those lines into per-client attempts is the next piece of work and would give the Wi-Fi join view its missing half. Note the two logs are not alike: an unadopted device's log is all `ace_reporter.reporter_fail()` and carries no wireless events at all, so a parser must not read "no attempts" as "no failures".
- 2026-09-10 still unverified: `board_info`, `system_cfg`, `mgmt_cfg`, `mca_info`, `stainfo`, `wstalist`, `mca_dump`. `_truncate` keeps the first `MAX_OUTPUT_BYTES`, which is the wrong half for a log; `syslog_tail` is bounded at 200 lines so it does not bite today, but a future log-shaped command would want tail-truncation instead.
- 2026-09-09 Device SSH: confirm which UniFi device types in this estate honor controller-pushed SSH keys, and whether the key survives a device reboot. Ubiquiti's documentation says support varies by device architecture and firmware, and help.ui.com is not fetchable from this environment, so this was not verified against a primary artifact.

## Deferred work

- 2026-09-08 UniFi diagnostics sibling integration: not created. Port profiles and effective native/tagged VLAN, device Network Override, the inform URL a device holds, STUN 3478 state, Mesh Parent, association tables, spectrum occupancy and DHCP leases have no route in the Network API at v10.4.57 (checked against the saved OpenAPI: `Port overview` carries connector, idx, maxSpeedMbps, poe, speedMbps, state only; `Adopted device details` carries no override or inform field; `Device uplink interface overview` carries deviceId only; `Wireless radio overview` carries the device's own channel, width, band and standard). All of it depends on read-only SSH whose command output has not been verified against real hardware, and the sibling's name is unconfirmed.
- 2026-09-08 Pre-flight validator rules 1 and 2 (uplink native VLAN changed without a matching Network Override; infrastructure device on an Edge-mode port profile): blocked on the same SSH collection. Rule 3 is blocked instead on a policy evaluation engine and per-network subnets; see decisions.md.
- 2026-09-03 health.py `_async_finalize_check`: the WS dismiss handler in websocket_api.py does not yet delete the Repairs issue directly; until it does, the sweep-side delete is what clears a dismissed finding's issue, at most one sweep interval later.
- 2026-09-03 config_hygiene.py `_trigger_entity_ids`: device triggers are out of scope because `entity_id` exposure is not reliable across targeted core versions; revisit when the minimum core version guarantees it.
- 2026-09-03 CI minimum-version job (test.yml): decision D-16 chose "test only the pinned latest harness" as a safe default until a minimum-version job is decided; that decision is still open (work plan section 7).
- 2026-09-03 Signed pre-built Probe image: recorded on 2026-08-30 as not implemented; moving to Cosign-signed pre-built images via the official builder actions and an `image:` key remains an option if the locally built mode is ever abandoned (work item 2.5).

No TODO or FIXME comments remained in the integration, frontend, probe, scripts, workflow, or test sources as of 2026-09-03.
