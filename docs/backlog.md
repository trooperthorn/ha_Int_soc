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

## Deferred work

- 2026-09-03 health.py `_async_finalize_check`: the WS dismiss handler in websocket_api.py does not yet delete the Repairs issue directly; until it does, the sweep-side delete is what clears a dismissed finding's issue, at most one sweep interval later.
- 2026-09-03 config_hygiene.py `_trigger_entity_ids`: device triggers are out of scope because `entity_id` exposure is not reliable across targeted core versions; revisit when the minimum core version guarantees it.
- 2026-09-03 CI minimum-version job (test.yml): decision D-16 chose "test only the pinned latest harness" as a safe default until a minimum-version job is decided; that decision is still open (work plan section 7).
- 2026-09-03 Signed pre-built Probe image: recorded on 2026-08-30 as not implemented; moving to Cosign-signed pre-built images via the official builder actions and an `image:` key remains an option if the locally built mode is ever abandoned (work item 2.5).

No TODO or FIXME comments remained in the integration, frontend, probe, scripts, workflow, or test sources as of 2026-09-03.
