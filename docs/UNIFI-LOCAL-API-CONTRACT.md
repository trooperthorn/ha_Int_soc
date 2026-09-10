# UniFi Local API Contract Verification

Verified 2026-09-01 against the user-selected, versioned Ubiquiti artifacts:

| Artifact | SHA-256 |
|---|---|
| Network 10.4.57 OpenAPI | `3773947b4572b1bdc84272d3d2b9ebb5cad0d9aaa2640c3418568df97c9df59d` |
| Network 10.4.57 Postman | `6ac7c129e7be3d748974f23a9e4462cbfa2ccaf1281553a0da9187d0cceddcbf` |
| Protect 7.2.105 OpenAPI | `1d43b82969c3f792719572d2bf05956305f7ec5287c406e822bc97a8ea2b0de3` |
| Protect 7.2.105 Postman | `8628200b894509f37b60ce0d2e4520731d779ef74a85973c9cfb1f8de454e4a5` |

Primary sources: [Network getting started](https://developer.ui.com/network/v10.4.57/gettingstarted),
[Network OpenAPI](https://developer.ui.com/network/v10.4.57/openapi.json),
[Network Postman](https://developer.ui.com/network/v10.4.57/postman-collection.json),
[Protect getting started](https://developer.ui.com/protect/v7.2.105/gettingstarted),
[Protect OpenAPI](https://developer.ui.com/protect/v7.2.105/openapi.json), and
[Protect Postman](https://developer.ui.com/protect/v7.2.105/postman-collection.json).

## Implemented connection contract

- Network base: `https://{console}/proxy/network/integration/v1`
- Protect base: `https://{console}/proxy/protect/integration/v1`
- Authentication: local Integration API key in `X-API-KEY`; secrets remain in
  HA SOC's private secret store and are redacted from representations/audit.
- Redirects are refused so a custom authentication header cannot be forwarded
  to a redirect target. Responses and aggregate request time are bounded.
- HTTP remains accepted for an explicitly configured local console, and TLS
  verification can be disabled for the present self-signed deployment. Both
  are transitional risk acceptances; see the transport migration plan.

## Corrected calls

Network collection calls use `/sites`, then the documented site routes:
`clients`, `devices`, `devices/{id}`, `devices/{id}/statistics/latest`,
`wifi/broadcasts`, `networks`, `acl-rules`, `firewall/zones`, and
`firewall/policies`, plus, since 2026-09-08, the read-only
`acl-rules/ordering`, `firewall/policies/ordering`, and
`networks/{networkId}/references` site routes and the site-independent
`GET /info`, and since 2026-09-09 `wifi/broadcasts/{wifiBroadcastId}`. Ten
of the specification's 44 paths were called before the 2026-09-08 change;
fourteen are now. The implementation no longer probes undocumented legacy
ACL or `network-confs` paths.

Protect camera inventory uses an unpaginated `GET /cameras`. Protect 7.2.105
does not define historical REST `/events`, `/detections`, or `/alarms` calls.
Live events use the persistent WebSocket `GET /subscribe/events`; HA SOC uses
Home Assistant's loaded UniFi Protect integration as the recent in-memory
event source and otherwise shows an explicit limitation.

Contract regression tests fail if the versioned bases drift, guessed event
routes return, or the required statistics/subscription paths disappear.

### Firewall Policies vs. ACL Rules

These are two genuinely separate resources, not two names for the same
thing. `GET /sites/{siteId}/acl-rules` is real and probed, but a live
controller returned `{"offset":0,"limit":25,"count":0,"totalCount":0,"data":[]}`
for it on an install whose actual rules turned out to live under Firewall
Policies instead (Settings -> Security -> Create Policy in the UniFi UI,
UniFi's newer zone-based default allow/deny model). An honest security
audit reads both.

Confirmed real paths:

- `GET /sites/{siteId}/firewall/zones` (`id`, `name`, `networkIds`)
- `GET /sites/{siteId}/firewall/policies` (the rules)

Schema verified against the community-maintained OpenAPI extraction for
this controller version (github.com/beezly/unifi-apis), parsed directly
rather than through a lossy summarizer, since developer.ui.com itself is
unreachable from every environment this project has been built in.


## Verified response shapes

Facts moved out of `unifi.py` and `unifi_core.py`. "Verified" means checked against the versioned OpenAPI artifacts above or a live controller response; "Unverified" rows are the candidate-key mappings that `backlog.md` lists for confirmation.

### Client, device, and pagination shapes

| Fact | Verified |
| --- | --- |
| `_rows` tolerates a bare list or `{"data": [...]}`, the Integration API paginated envelope. `_get_paginated` follows offset/limit pagination and falls back to a single unpaginated response; a bare list or a short page means there is no more to fetch. Pagination is bounded by `_PAGE_LIMIT` (200) and `_MAX_PAGES`. | Verified |
| The site identifier is `id` on the Integration API and `name` or `_id` on the legacy API. | Unverified (backlog) |
| `_as_epoch` accepts an epoch in seconds or milliseconds (a 13-digit value above 10,000,000,000 is milliseconds) or an ISO string. | Verified (code) |
| The Integration client object exposes IPv6 as a list (`ipv6Addresses`); other shapes use a single string. | Unverified (backlog) |
| Byte counters are nested under `statistics` (and a device's under `statistics.uplink`). | Unverified (backlog) |
| A wireless client carries either the SSID name directly or a reference to a WiFi broadcast whose name lives in `/wifi/broadcasts`. | Unverified (backlog) |
| VLAN is a first-class field on some firmwares (`vlan`, `vlanId`, `networkVlanId`, `vlan_id`), nested under `access` on others, and otherwise derivable only from the network. | Unverified (backlog) |
| Client uptime is an explicit seconds field if present (`uptime`, `uptimeSeconds`, `uptime_seconds`), otherwise derived from `connectedAt`, which is what the Integration API returns for a client. | Verified for `connectedAt` |
| Firmware-updatable is a boolean on the device detail object (`firmwareUpdatable`, `updateAvailable`, `update_available`). | Unverified (backlog) |
| A gateway's `interfaces` may be a dict (`interfaces.wan` / `interfaces.ports`) or a list; the WAN-port or uplink shape is the single most uncertain mapping. | Unverified (backlog) |
| `/devices/{id}` supplies configuration and detail fields and `/devices/{id}/statistics/latest` supplies heartbeat, utilization, uptime, and uplink rates; each request is independent and non-fatal, and detail values win over list values. | Verified |

### Why a client cannot join, and what the API does not say

| Fact | Verified |
| --- | --- |
| No endpoint in the specification carries an association attempt, an authentication failure, a retry or error counter, or any per-client history. A client that cannot join is absent from `/clients` entirely, because that collection is connected clients only. The Wi-Fi join view therefore reports configuration that refuses a join, never a failure. | Verified (all 44 paths) |
| The whole client object is `id`, `name`, `macAddress`, `ipAddress`, `connectedAt`, `type`, `uplinkDeviceId`, and `access.type`. `uplinkDeviceId` is the only link from a client to the access point carrying it. | Verified (`Wireless client overview` / `Client overview`) |
| Core `unifi`'s in-memory client carries `ap_mac`, which is the same attribution by MAC and the fallback when the direct API path produced no row. | Verified (core `device_tracker.py` `CLIENT_CONNECTED_ATTRIBUTES`) |
| Clients that are NOT connected exist only in core `unifi`'s all-clients collection (`api.clients_all`, with `first_seen` and `last_seen`). Without the core integration loaded there is no absent-client list at all, and the panel says so rather than showing an empty one. | Verified (core `services.py` uses `hub.api.clients_all`) |
| `broadcastingDeviceFilter` is documented as "List of Access Point capable device IDs to which the WiFi broadcast applies", with variants `DEVICES` (`deviceIds`) and `DEVICE_TAGS` (`deviceTagIds`). Its absence means every AP broadcasts the SSID. There is no route to resolve a device tag, so a `DEVICE_TAGS` filter reports the tag count and claims nothing about coverage. | Verified (`Broadcasting device filter`) |
| The broadcast collection response carries `enabled`, `name`, `network`, `securityConfiguration.type`, `type` (`STANDARD` or `IOT_OPTIMIZED`), `broadcastingDeviceFilter`, and, on `STANDARD`, `broadcastingFrequenciesGHz`. `hideName`, `clientFilteringPolicy` and `blackoutScheduleConfiguration` appear only in the per-broadcast detail response, which is why the detail route is now called. | Verified (`Wifi broadcast overview` / `Wifi broadcast details`) |
| Security types are `OPEN`, `WPA2_PERSONAL`, `WPA3_PERSONAL`, `WPA2_WPA3_PERSONAL`, and the three enterprise twins. | Verified (`Wifi security configuration overview` discriminator) |
| A blackout schedule is reported as a day count, never evaluated against the current time; whether the SSID is off at this moment is not claimed. | Verified (code) |

### ACL rule schema (Network 10.4.57 OpenAPI)

| Fact | Verified |
| --- | --- |
| Each rule has `type` (IPV4 or MAC), `action` (ALLOW or BLOCK), `index`, and `metadata.origin` (USER_DEFINED for a rule the owner created, SYSTEM_DEFINED for a UniFi default, DERIVED for one the controller generated), surfaced as `custom`. | Verified |
| IPV4 rules only carry a top-level `protocolFilter` restricted to TCP and UDP. | Verified |
| `sourceFilter` and `destinationFilter` form a discriminated union on `type`. IPV4 rules use an "IP ACL rule endpoint": IP_ADDRESSES_OR_SUBNETS (`ipAddressesOrSubnets` plus `portFilter`), NETWORKS (`networkIds` plus `portFilter`), or PORTS (`portFilter` only). MAC rules use a "MAC ACL rule endpoint": MAC_ADDRESSES (`macAddresses` plus `prefixLength`). | Verified |
| A MAC rule carries no network in either filter; its scope comes from the rule-level `networkIdFilter` (one network per MAC rule), which `_normalize_acl_rule` resolves into the same `networks` list an IPV4 rule's filters populate. | Verified |
| Every ACL `portFilter` is a plain array of ints (1 to 65535), never a range or a string; `_port_list` still tolerates a string port or a `start-end` range defensively. | Verified |
| A filter that is not a dict (absent, or a legacy flat string) normalizes to an empty-but-shaped record. `_resolve_network_refs` maps id, name, or object references through the network map (id to "Name (VLAN x)"), falls back to the stringified reference, dedupes, and preserves order. | Verified (code) |

### Firewall Policy schema

| Fact | Verified |
| --- | --- |
| `action` is a typed ALLOW, BLOCK, or REJECT object; `index`; `ipProtocolScope` carries `ipVersion` (IPV4, IPV6, IPV4_AND_IPV6) and `protocolFilter`, which discriminates on NAMED_PROTOCOL (AH, DCCP, TCP, UDP, ICMP, and so on) or PRESET (TCP_UDP), with `name` the readable protocol string in either case (None means all protocols); `connectionStateFilter`; `loggingEnabled`; `schedule` (None means always active); `metadata.origin` surfaced as `custom`. | Verified |
| `source` and `destination` each carry a required `zoneId` plus an optional `trafficFilter`. | Verified |
| `allowReturnTraffic` is ALLOW-only and required whenever the action is ALLOW: whether UniFi auto-creates a derived policy on the mirrored zone pair, the reason a list often shows paired "X" and "X (Return)" entries; None for BLOCK and REJECT. | Verified (live controller response) |
| A port-matching entry is PORT_NUMBER or PORT_NUMBER_RANGE and is kept as a string because it can genuinely be a range. A port filter has the same shape standalone or nested inside a NETWORK, IP_ADDRESS, or similar filter: type PORTS carries explicit items; type TRAFFIC_MATCHING_LIST references a saved list the project does not resolve by name. | Verified |
| The primary MAC_ADDRESS filter carries `macAddresses` as a list, while a NETWORK, IP_ADDRESS, or IPV6_IID source filter may carry an extra single-MAC constraint object. | Verified |
| REGION, VPN_SERVER, SITE_TO_SITE_VPN_TUNNEL, and IPV6_IID nested field names. | Unverified (surfaced by type only) |
| `_fetch_firewall_zones` returns `[{id, name, networks}]`; `_port_in_dest_list` handles ACL ints and policy strings that may be a single number or a range. | Verified (code) |

### Protect 7.2.105

| Fact | Verified |
| --- | --- |
| `/cameras` is an unpaginated JSON array; Network-style offset/limit parameters must not be appended. | Verified |
| Events are exposed only as the WebSocket subscription `GET /subscribe/events`; there is no historical REST `/events`, `/detections`, or `/alarms`, so the snapshot makes no undocumented calls and `events_error` explains that while the loaded core unifiprotect integration supplies its in-memory buffer. | Verified |
| `isRecording` is a boolean on some firmwares and `recordingSettings.mode` ("always", "detections", "never") on others; each channel typically carries a name and/or width and height. | Unverified (backlog) |
| `licensePlate` can be a bare string or nested under `metadata`. The console deep link for a device is `{origin}/protect/dashboard/devices/{id}`. | Verified (code) |

### Client hardening

Redirects are never followed (a 3xx is an error, so `X-API-KEY` can never be carried to a redirect target; aiohttp strips only Authorization-family headers on cross-origin redirects), bodies are capped at 8 MB by both declared Content-Length and actual read, the whole Network overview runs under one 60-second budget (`_OVERVIEW_TIMEOUT_SECONDS`), and the configured host must be plain http or https with no userinfo (`_validate_host`) (work plan item 4.11). The Probe add-on's decoding of `/proc/net/tcp[6]` is the source of the HA server's own LAN IPs used by `_server_ip_addresses`.

## Threat Management on the gateway (verified 2026-09-10 over SSH)

The Integration API has no threat, IPS, IDS, alarm, event, or detection route:
all 44 paths of the Network 10.4.57 OpenAPI and every schema were searched for
those terms and none appears. Home Assistant core's `unifi` component reads
nothing IPS-related either. So the perimeter signal cannot come from the API
HA SOC already uses; it comes from the gateway itself, over the read-only
Device SSH path. Every fact below was read from one gateway: a UCG-Fiber on
UniFi OS 5.1.33 running Network 10.4.57, Suricata 8.

### Engine and configuration

| Fact | Verified |
| --- | --- |
| Suricata runs as `ips_8` from `/usr/share/ubios-udapi-server/ips_8/config/suricata_ubios_high.yaml`, includes `/run/ips/config/homenet.yaml`, `rules.yaml` and `iface.yaml`, and loads `/run/ips/rules/suricata.ui_rules` (36 MB, 37,218 signatures at the last reload) plus an empty `suricata.rules`. BusyBox `ps -C` prints nothing for it; `ps w` is the form that lists it. | Verified |
| The rule file uses no `classtype:` field, and Ubiquiti's curated set does not carry the ET `ATTACK_RESPONSE` category or the `testmyids.com` signature 2100498, so that classic test produces no alert. | Verified |
| `/run/ips/config/config.json` holds `alert.category`, `alert.signature_id`, `drop.category`, `drop.signature_id`, `whitelist`. `daemon_config.json` holds `block_category`, `block_sid`, `block_time` (seconds), `device_id`, `is_ssl_inspection_enabled`, `logging_threat_event`, `suricata_version`, and a `token` that must be redacted. A non-empty `block_category` is Prevent mode; categories only under `alert` is Detect; both empty is off. | Verified |
| `ip_reputation.json` holds `src_whitelist` and `dst_whitelist` (CIDR lists), and `threshold.config` repeats them as two `suppress gen_id 0, sig_id 0, track by_src|by_dst, ip [...]` lines. An address in those lists is never alerted on in either direction: the exemption is total, not per signature. On the verified gateway the Home Assistant server's own address was in both lists. | Verified |
| `homenet.yaml` defines `HOME_NET` as a bracketed comma list of IPv4 and IPv6 prefixes with `EXTERNAL_NET: "!$HOME_NET"`; `iface.yaml` lists the `pcap` interfaces (`br0`, `br10`, `br30`, `br50` here, one thread each, `bpf-filter: "not net 169.254.254.0/24"`). Traffic the gateway itself originates leaves on the WAN interface and is never inspected. | Verified |
| `/run/ips/rules/` also carries `tor.list` and `alien.list.gz` reputation lists with `.ts` refresh stamps, refreshed nightly. | Verified |

### Where alerts go, and where they do not

| Fact | Verified |
| --- | --- |
| The only enabled alert output is an `eve-log` of `filetype: ubnt-idsips-daemon` with `daemon-filename: /run/ips/eve_alert.json`, `types` alert (payload off, tagged-packets on), http and tls extended, and drop (`alerts: yes`, `flows: start`). `/run/ips/eve_alert.json` and `/run/ips/ubnt_idsips_daemon.sock` are Unix sockets, not files. There is no `eve.json` or `fast.log` to tail; `/var/log/suricata/suricata_8.log` is the engine log only. | Verified |
| Mongo on `127.0.0.1:27117` (`unifi-mongodb.service`) has `ace` and `ace_stat`. `ace.ipsalert` exists and holds zero rows; `ace.alarm` and `ace_stat.event`, where older controllers kept IPS detail, do not exist. `ace.alert` is the notification collection and is where threat and firewall blocks land. | Verified |
| `ace.alert` keys seen: `THREAT_BLOCKED_V3`, `THREAT_BLOCKED_KNOWN_SOURCE_CLIENT`, `THREAT_BLOCKED_KNOWN_SOURCE_AND_DESTINATION_CLIENTS` (Suricata blocks; the suffix says which endpoints resolved to known clients), and `TRAFFIC_BLOCKED_KNOWN_SOURCE_DEVICE` (a firewall policy hit; `parameters.TRIGGER.name` is the policy name). Also present and useful elsewhere: `ADMIN_ACCESS` (controller admin logins). | Verified |
| An alert row is `{_id, site_id, key, time (epoch ms, NumberLong), status, severity?, parameters, metadata}`. `parameters` carries `DEVICE` (the gateway), `SRC_IP` or `SRC_CLIENT` (`target_id` is an IP, or a MAC with `hostname` and `name`), `SRC_DEVICE` for an adopted device, `DST_IP`, `TRIGGER` for policy hits, and `INITIATOR_ID`. `severity` (`VERY_HIGH` seen) is present on threat rows. | Verified |
| `INITIATOR_ID.target_id` resolves to no document in any Mongo database or Postgres database on the gateway (`ace`, `ace_stat`, `ulp-go-syslog`, `unifi-core` and the rest were searched by id). The Suricata signature id, category and rule name are not persisted anywhere readable on this release; the UI renders them from the daemon. This is a limit, not a gap in the search. | Verified |
| Postgres 14 on `127.0.0.1:5432` holds `ulp-go-syslog` (`json_systemlog`: UniFi OS user sessions, API key add and remove, SSO binding) and `unifi-core` (`syslog_sender_settings`, `notifications`, `integration_keys`). Neither holds threat rows. | Verified |
| A Suricata alert for the workstation at 192.168.30.27 on a watched interface, not exempted, fetching a URL matched by no shipped signature produced no `ace.alert` row, as expected; a real `THREAT_BLOCKED_KNOWN_SOURCE_CLIENT` for the same client to an IPv6 destination was already present. | Verified |

### What HA SOC reads

- `ips_config` (allowlisted, verified): the six files under `/run/ips/config`, parsed by `unifi_ips.parse_ips_config` into mode, categories, exemptions, home networks and interfaces. The derived posture is kept under the store's `unifi_ssh.ips_posture` so the Network Security findings can use it between runs; the raw text is not.
- `ips_block_log` (allowlisted, unverified until its projected output has been seen): the newest 200 `*_BLOCKED*` rows of `ace.alert` via the gateway's own `mongo` shell, projected to `{id, key, time, severity, parameters}` as one JSON object per line.
- Not read: `ace.ipsalert` (empty on this release), the `daemon_config.json` token, anything under `/data`.
