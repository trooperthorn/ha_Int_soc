# HA SOC versus stefgo/ha-crowdsec-integration: what is worth bringing over

Date: 2026-09-10. Scope: read-only comparison. Nothing was changed in
`~/repos/ha_Int_soc`. Scanner (`check_stale.py`) on ha_Int_soc: 0 findings at
commit fc5a1d7 (v2026.09.09.7).

Upstream reviewed: https://github.com/stefgo/ha-crowdsec-integration at 1.3.5
(2026-08-29), MIT, shallow clone in the session scratchpad. It is a
single-purpose integration: one config entry per CrowdSec Security Engine,
polling the Prometheus `/metrics` endpoint and the Local API (`/v1/alerts`,
`/v1/decisions`), 17 entities per instance, two Lovelace cards, three services,
one event. Roughly 4,500 lines of Python. HA SOC is roughly 22,700 lines across
40 modules with an 82-command WebSocket API and a sidebar panel.

## Bottom line

HA SOC has no perimeter signal at all today. Its only attacker-facing detection
(`brute_force_ip`) reads Home Assistant's own failed-login log, which is
IP-only and sees nothing that CrowdSec already stopped at the reverse proxy or
firewall. The single most valuable thing to take from the CrowdSec integration
is not its code but its data source: a CrowdSec connector in the Network
Security tab, built the way the Pi-hole connector already is, would give HA SOC
what it is structurally blind to. Five smaller patterns are worth borrowing on
their own. The cards, the localisation layer, and the release shape are not.

## What HA SOC already covers (no action)

| CrowdSec feature | HA SOC equivalent | Note |
| --- | --- | --- |
| `Status` problem flag with `reasons` attribute | Every health/hygiene check reports "could not evaluate" and carries evidence; posture terms are labeled provisional | Same honesty stance, already there |
| Repairs issues for truncation and missing key | `repairs.py` syncs admin-MFA, stale-token, vuln, and audit-chain-reset issues | HA SOC's issues are all `is_fixable=False`; see pattern 5 |
| `ip_ban` awareness | `health.py` check `http_hardening` flags `ip_ban_enabled: false` and a silenced ban logger | |
| Firewall write with confirmation | Probe iptables rules with a test window and revert; UniFi policy/ACL disable behind a separate write-scoped key, confirmed, audited, read back | HA SOC's write model is stricter and should be the template for any CrowdSec ban action |
| Diagnostics redaction | `diagnostics.py` | |
| `runtime_data`, `OptionsFlow` without `__init__` | Already current; CrowdSec still uses `add_update_listener` plus reload, which the skill says not to copy | |

## Candidates to bring over, ranked

### 1. CrowdSec connector as a Network Security source (high value, medium effort)

What it is upstream: `api.py` logs in at `/v1/watchers/login` with machine
credentials, holds the JWT, and per cycle runs three requests in parallel
through `asyncio.gather` so timeouts do not add up: Prometheus text from
`/metrics`, `/v1/alerts?since=…`, and `/v1/decisions?origins=…`. A fixed
`User-Agent` of the form `name/version` is required or the LAPI login answers
401 (as implemented in stefgo's `const.py`; unverified against CrowdSec docs).

What HA SOC would gain, mapped to its existing surfaces:

- Network Security tab: a CrowdSec section beside Pi-hole with reachability,
  active decisions (from the `cs_active_decisions` metric, which counts CAPI and
  blocklist decisions the list endpoint cannot), new bans and unique attackers
  in 24 h, top scenario, top country, top attacker.
- Two control-effectiveness findings that fit the advisory findings list and
  NIST SI-4: "no bouncer queries for N intervals, decisions are not being
  enforced" (from `cs_lapi_route_requests_total`) and "no log lines processed
  any more, CrowdSec is blind" (from `cs_parser_hits_total` going flat after
  traffic was seen). Parse error rate above a threshold is a third.
- Settings: host, machine ID, password, optional bouncer key, verify SSL, into
  the existing `secrets_store` the way `pihole_api_key` is held. HA SOC is
  `single_config_entry`, so CrowdSec's multi-instance picker does not apply;
  one engine per install is enough for the household case.
- Posture: an "edge enforcement" term that is provisional until the connector
  has read real data once, in line with the existing rule.

Effort notes: the Prometheus text parser (`metrics.py`, 170 lines), the counter
rate tracker (`rates.py`, 111 lines) and the alert summariser (`alerts.py`)
are deliberately free of Home Assistant imports and unit-tested without the
harness. That split is worth keeping: put them under a `crowdsec/` helper
package with plain pytest coverage, and keep only the coordinator-side glue in
the module that touches `hass`. Do not copy the `PERCENTAGE` unit from
`sensor.py`; it is deprecated since 2026.7 in favour of `UnitOfRatio`.

Threat-model line to add: a new outbound LAN connection to the CrowdSec LAPI
and metrics port, credentials at rest in the secrets store, and the LAPI
password being able to create alerts (so a compromised HA SOC could ban
addresses). That last point argues for machine credentials only when the ban
action is enabled, and the read-only bouncer key otherwise; upstream treats the
bouncer key as a fallback, HA SOC should treat it as the default.

### 2. Cross-boundary detection rule (high value, low effort once 1 exists)

HA SOC's `brute_force_ip` rule windows `login_fail` audit events per IP.
CrowdSec's alert list carries the attacker IP, scenario, country and AS name.
Two new detection rules follow directly:

- `edge_attacker_reached_ha`: an IP with a CrowdSec alert in the last 24 h
  also appears in HA SOC's `login_fail` or `new_ip_login` audit records. This
  is the "the perimeter saw them and they still got to the login form" signal,
  and it is the one a household owner actually needs to act on.
- `ha_attacker_unknown_to_edge`: an IP that trips `brute_force_ip` has no
  CrowdSec decision. Either CrowdSec is not watching the path Home Assistant is
  exposed on, or the bouncer is not enforcing; both are configuration gaps.

Both rules use the existing threshold store, `_upsert_detection`, hour
buckets, and risk factors, so the code is a few dozen lines each plus tests in
`test_detections_rules.py`.

### 3. IP lookup and gated ban/unban as panel actions (medium value, medium effort)

Upstream's lookup asks `/v1/decisions?ip=<x>&contains=true`, which is what
finds a covering range from a blocklist; the table cannot show that. In HA SOC
the natural home is the detection detail: a detection subject that is an IP
gets a "Check at edge" action returning blocked or not, the covering range, the
decisions in force with origin, and the 24 h alert history.

Ban and unban should follow HA SOC's existing suggestion write-back model, not
upstream's: off by default, separate credential, confirmation with the reason
typed, audit record flushed immediately, and a read-back that re-asks the LAPI
rather than trusting the delete count (upstream does the read-back part well
and explains why: after an unban a covering range can still be in force).
Upstream's delete guard is worth keeping exactly: refuse to delete when every
decision for the address is CAPI or blocklist origin, because a local delete
would be undone on the next pull.

Input validation to reuse: `validation.py` normalises addresses through
`ipaddress` and refuses the `d` unit in durations because Go durations have no
day unit. HA SOC's `firewall.py` already has `_valid_source` doing the address
half; the duration rule is new.

### 4. Detection events on the bus with burst control (medium value, low effort)

HA SOC fires no events at all (`bus.async_fire` appears nowhere in the
integration). Upstream fires `crowdsec_new_ban` per new alert with three rules
that transfer directly: silent on the first cycle after start so the backlog is
not dumped, capped at 25 per cycle with the remainder deferred to later cycles
rather than dropped, and a documented digest pattern in
`examples/ios_push_badge.yaml` (trigger-based template sensor as a buffer, one
summarised push after 45 s of quiet, a flush event to reset).

For HA SOC: `ha_soc_detection_opened` with `rule_id`, `subject`, `severity`,
`detection_id`, and the same cap and first-run silence, plus a shipped
`examples/detection_digest.yaml`. This is the missing bridge between HA SOC's
detections and the companion app, and it is cheap.

### 5. Fixable Repairs flow that asks for a credential (low value, low effort)

Every HA SOC issue is `is_fixable=False`. Upstream's `repairs.py` is a
90-line `RepairsFlow` that asks for a bouncer key, tries it against the
instance, stores it on the entry and reloads. HA SOC has at least two issues
where the fix is "enter one credential": a Pi-hole key that stopped working
and, after item 1, a CrowdSec credential. The `async_create_fix_flow` entry
point and the confirm step with `description_placeholders` for the error
detail are the parts to copy. Verified in the core clone at 2026.9.1:
`RepairsFlow` and `async_create_fix_flow` are in
`homeassistant/components/repairs/models.py`.

### 6. Window splitting for an API that truncates instead of paginating (pattern only)

`timewindow.py` halves a query window when the LAPI returns exactly `limit`
rows, up to four levels, and raises a Repairs issue when still truncated.
HA SOC's audit query already takes a limit and the UniFi API paginates, so
there is no immediate use. Note it in `docs/design.md` as the answer if the
CrowdSec alert query is added, since `/v1/alerts` has no pagination.

## Not worth bringing over

- The two Lovelace cards. HA SOC is a panel with its own WebSocket API and
  Overview tiles; a card would be a second frontend to keep in step with the
  2026.4 to 2026.8 `ha-*` component churn. The table behaviours (search across
  fields, chips, sort with unknowns last) already exist in HA SOC's sortable
  tables.
- German and English localisation in the card (`localize.ts`); HA SOC ships
  `translations/en.json` only and has no localisation layer to extend.
- `add_update_listener` plus `async_reload_entry` for options changes; the
  skill's contract says use `OptionsFlowWithReload` or, as HA SOC does, an
  explicit scheduled reload.
- Release shape: tag-push release, semver, CHANGELOG-driven notes, Python 3.13
  CI, floor `homeassistant: 2025.2.0`. HA SOC's merge-to-main CalVer flow with
  `.release.json`, SBOM and attestations is the house baseline and stricter.
  The weekly scheduled `validate.yml` run is already in HA SOC.
- `builddeploy.sh` with rsync to a live instance from `.env`; HA SOC deploys
  through HACS releases and the dev loop is the test suite.

## Licensing and provenance

Both repositories are MIT. Copying code verbatim requires keeping stefgo's
copyright notice with it, which conflicts with the house rule of no attribution
footers in committed files. Recommendation: re-implement against the endpoint
contract (the endpoints, parameters and quirks listed under item 1 and 3 are
the contract), keep the HA-free module split as a design choice, and record
the source of the design in `docs/decisions.md` with a dated entry that names
the upstream repository. That is a design credit, not a license notice, and it
matches how the Spook-inspired sweep is already credited in the README.

Facts taken from stefgo's code and not verified against CrowdSec's own
documentation this session: the `name/version` User-Agent requirement, the
`/v1/decisions` 404 on some versions, the `origins` filter being ignored on
some versions, and `contains=true` semantics. Verify against
https://docs.crowdsec.net (LAPI OpenAPI) before building item 1. Per house
rule, no issue or pull request is to be opened on stefgo's repository.

## Suggested order if this is taken up

1. Item 1 connector, read-only, bouncer key by default, three findings, posture
   term. One PR, HA-free parsers with plain pytest, coordinator glue with the
   harness.
2. Item 4 events and digest example. Independent of item 1; can land first.
3. Item 2 detection rules. Depends on item 1.
4. Item 5 fixable repair for the Pi-hole and CrowdSec credentials.
5. Item 3 lookup, then ban/unban behind the write-back gate, last.
