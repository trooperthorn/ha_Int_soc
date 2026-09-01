# HA SOC CEF 0 Schema

HA SOC can export finalized audit-chain records as a CEF 0 payload inside an
RFC 5424 message. Select **RFC 5424 + CEF 0** under **Settings > SIEM / Syslog
Export**. The payload selector is independent of UDP, TCP, or TLS transport.

## Header

```text
CEF:0|Home Assistant|HA SOC|<integration-version>|ha_soc.<category>|<event-name>|<severity>|
```

- The integration version comes from `manifest.json` through Home Assistant's
  integration loader.
- The event class ID is stable for a category and never contains an audit
  sequence or user-supplied detail.
- Known categories have fixed event names. Unknown future categories use a
  sanitized deterministic fallback and are still exported.
- CEF severity is an independent 0-10 value; it does not reuse the RFC 5424 PRI
  severity number.

## Extensions

| CEF key | HA SOC source | Notes |
|---|---|---|
| `rt`, `start` | `ts` | Epoch milliseconds. |
| `cat` | `category` | Original HA SOC category. |
| `act` | `domain.service` | Present for service-related events. A `service_call` is an attempted call, not a confirmed result. |
| `outcome` | category | `success` for `login_ok`; `failure` for `login_fail` and `probe_auth_rejected`. |
| `src` | `ip` | Valid IPv4 only in CEF 0. |
| `c6a1`, `c6a1Label` | `ip` | Valid IPv6, labeled `Source IPv6`. |
| `suid` | `user_id` | Acting/source user ID; not represented as a username. |
| `duid` | `detail.target_user_id` | Target user ID for lifecycle events. |
| `duser` | `attempted_user` or `detail.target_name` | Target/attempted username when Home Assistant supplies one. |
| `cn1`, `cn1Label` | `seq` | Audit sequence, labeled `Audit Sequence`. |
| `cs1`, `cs1Label` | `hash` | Current audit hash. |
| `cs2`, `cs2Label` | `prev_hash` | Previous audit hash. |
| `cs3`, `cs3Label` | `context_id` | Home Assistant context ID. |
| `cs4`, `cs4Label` | `context_parent_id` | Parent context ID. |
| `cs5`, `cs5Label` | `entity_ids` | Canonical compact JSON array. |
| `msg` | `detail` | Canonical compact JSON after the audit logger's secret redaction. |

The RFC 5424 structured-data element continues to contain `seq`, `hash`, and
`category`. Chain fields are duplicated in CEF because a SIEM connector may
ignore RFC 5424 structured data.

## Severity policy

| CEF value | Categories |
|---:|---|
| 10 | `audit_chain_reset` |
| 9 | `probe_auth_rejected` |
| 7 | `login_fail`, `user_removed`, `user_deactivated`, `firewall_pending_discarded` |
| 5 | known security/configuration changes, privileged reads, token creation, watchdog and detection-status events |
| 3 | `login_ok`, `service_call`, `session_seen` |
| 4 | unknown/unclassified future categories |

## Encoding and bounds

- The message is UTF-8.
- CEF header backslashes and pipes are escaped.
- CEF extension backslashes and equals signs are escaped; CR/LF are encoded as
  `\r` and `\n`.
- Control characters cannot create a new header or extension field.
- CEF field limits are applied without splitting an escape sequence.
- An oversized `msg` becomes a structured truncation summary.
- The final message retains the exporter's 32 KiB cap without byte-slicing
  UTF-8 or CEF.

The field and escaping rules follow the
[ArcSight CEF implementation standard](https://www.microfocus.com/documentation/arcsight/arcsight-smartconnectors-8.3/cef-implementation-standard/Content/CEF/Chapter%201%20What%20is%20CEF.htm)
and its
[extension dictionary](https://www.microfocus.com/documentation/arcsight/arcsight-smartconnectors-8.3/cef-implementation-standard/Content/CEF/Chapter%202%20ArcSight%20Extension.htm).

## SolarWinds SEM validation boundary

CEF conformance does not prove that a product-specific SolarWinds SEM connector
normalizes HA SOC fields. Validate raw receipt and normalized parsing
separately, use a dedicated local facility, and retain an exported sample for a
SolarWinds New Connector Request if the events arrive as unmatched data.
