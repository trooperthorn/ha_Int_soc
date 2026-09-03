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

