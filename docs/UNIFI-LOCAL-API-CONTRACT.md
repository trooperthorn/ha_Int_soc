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
`firewall/policies`. The implementation no longer probes undocumented legacy
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
