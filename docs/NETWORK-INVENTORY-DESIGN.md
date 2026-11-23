# Network inventory, presence and network health: design

Status: written 2026-11-22 against `main` at release v2026.11.22.2. Phases 1
to 4 are built (see the "What phase N built" sections below) and have not run
against a live Supervisor or a real Probe; phases 5 to 10 are design only. This document owns
the network inventory surface: what a device record is, how identity survives an address
change, which changes raise a detection, what the network health rules look
for, and what the feature can never claim. Dated decisions taken while
building it belong in `decisions.md` under a new "Network inventory" heading.

The feature list comes from a comparison with Vedetta 1.0.1
(`github.com/Sived80/vedetta`, MIT), a Home Assistant app that discovers and
names LAN devices. Only Vedetta's documentation and file tree were read for
that comparison, not its source. No Vedetta code is proposed for reuse here;
the mechanisms below are designed for HA SOC's existing Probe and store.

## Why

HA SOC already collects most of the raw data a device inventory needs and then
discards it. Three facts about `main` today, each read from the source:

1. The Probe's netscan runs a cycle every 300 seconds when enabled
   (`ha_soc_probe_netscan/run`, `POLL_INTERVAL_SECONDS`) and posts every host
   it saw. `probe.py` hands that to `store.async_set_netscan_result`, which
   replaces the previous cycle. One cycle is kept. There is no device record,
   no first-seen time, and no history.
2. None of the 11 rules in `detections.py` reads `netscan_result`. A device
   that joins the LAN, a port that opens on a camera, and a certificate that
   changes on the NAS all pass without a record.
3. HA SOC fires no events on the Home Assistant bus (no `bus.async_fire` call
   exists in the integration), so an automation cannot react to anything the
   console knows.

The control this closes is NIST SP 800-53 CM-8 (system component inventory)
and CM-8(3) (automated detection of unauthorized components), with SI-4 for
the change and health rules. The control matrix in
`NIST-SOC2-CONTROL-MATRIX.md` gains those rows when phase 1 ships, not before.

## A defect found while writing this

The Probe's TLS read does not return what its schema promises. `_read_tls_cert`
in `ha_soc_probe/rootfs/usr/lib/ha_soc/netscan.py` sets
`verify_mode = ssl.CERT_NONE` and then calls `ssl_object.getpeercert()`. With
verification off, Python returns an empty dict from that call. This was
checked on 2026-11-22 with Python 3.14.7 against a public HTTPS host: the dict
form was `{}` and `getpeercert(binary_form=True)` returned 1002 bytes of DER.
The function then takes its "no leaf certificate" branch, so `subject`,
`issuer`, `not_after` and `self_signed` are `None` for every host on a real
scan. `tests/test_netscan.py` passes because it supplies those fields in a
fixture; it does not exercise the handshake.

Not verified: the Probe's own Python version on the built image, and a live
scan result from the owner's install. One look at the Scanner tab's netscan
table settles it: if any row shows a certificate subject, this section is
wrong.

Phases 2 and 3 depend on certificate data, so the fix is part of phase 2.

Fixed 2026-11-23 in phase 2: the Probe now calls
`getpeercert(binary_form=True)`. `tests/test_inventory_changes.py` runs the
Probe's own `_read_tls_cert` against a TLS server on loopback and checks the
fingerprint, so the handshake is exercised. Still not verified: a scan from
the built Probe image on the owner's install.

## Goals and non-goals

Goals:

- A persistent record per network device that survives an IP change, with
  first seen, last seen, every name and its source, and the owner's verdict.
- Detections for a device nobody has acknowledged, and for a change on a
  device somebody has.
- Findings for exposure the scan already sees: cleartext management services
  and certificates near expiry.
- Presence history and opt-in "gone" and "back" alerts for devices the owner
  marks as watched.
- Network health rules for conditions that repeat: duplicate addresses, group
  drops, steady restarts, a slower gateway.
- Names and vendors from sources Home Assistant already holds, with the source
  shown beside every value.
- Coverage of routed networks the owner adds by hand.
- Bus events, count sensors and blueprints so automations can act.
- Inventory export, masked diagnostics, and a replay test corpus.

Non-goals, each with the reason:

- No nmap, arp-scan, scapy or any bundled scanner. `security.md` ("Netscan
  capability") already rejected them; this design keeps to TCP connect and
  `/proc` reads.
- No login to any device and no credential test. Device SSH remains the only
  path that authenticates to a device, with its own allowlist.
- No weighted device-type recognition engine. Vedetta's is its core product
  (signature catalogs, brand tables, a dozen name sources). HA SOC needs to
  know whether a device is acknowledged, not whether it is a thermostat. A
  coarse kind is taken from the Home Assistant device registry when the MAC
  matches, and nothing is guessed otherwise.
- No MQTT publishing of devices into Home Assistant. It would create entities
  whose attributes carry MAC and IP, which decision D-19 rules out.
- No brand logos, tile view, or second UI idiom. The feature lives in the
  existing panel tables.
- No automatic merge of two device records. See "Identity".

## Constraints this design inherits

- **The Probe's network posture.** `apparmor.txt` grants `capability net_raw`
  for iptables, but its network rules list only `inet tcp`, `inet6 tcp`,
  `inet udp`, `inet6 udp` and `netlink raw`. A raw ICMP socket or a packet
  socket is therefore outside the profile as written. Whether AppArmor denies
  it in practice on the built image is not verified here. No phase below needs
  one.
- **The scan result is a reconnaissance asset.** `THREAT-MODEL.md` makes
  `ws_netscan_status` owner-only for that reason. Every inventory command
  inherits the owner-only tier, whatever `access_level` says.
- **Entity attributes have no per-user ACL** (D-19). Sensors expose counts
  only. No MAC, IP or hostname appears in any entity state or attribute.
- **Flash writes are budgeted** (decisions of 2026-10-08, OPT-3 and OPT-7).
  Inventory and history get their own Store file with a delayed save, the way
  the syslog ring did, and are measured the same way before shipping.
- **Probe input is hostile until validated.** Every new field the Probe
  reports gets a bounded schema in `netscan.py` before it reaches the store,
  as every current field has.
- **Unknown is not zero.** A network that was not scanned reads "not scanned".
  A device with no presence signal reads "unknown", never "offline".

## Architecture

```
Probe netscan cycle (existing)        Home Assistant sources (existing)
  hosts: ip, mac, vendor, ports         UniFi clients (unifi.py)
        |                               device registry MAC connections
        v                               core DHCP discovery
probe.py ingest_probe_result            router device trackers
        |                                         |
        +-------------------+---------------------+
                            v
                  inventory.py  (new)
                  merge observations into device records
                            |
        +-------------------+--------------------+
        v                   v                    v
  inventory store     change events        presence segments
  (own Store file)    (bounded ring)       (per device, bounded)
        |                   |                    |
        v                   v                    v
  detections.py       health.py            network_health.py (new)
  new rules           new checks           repeat-condition rules
        |                   |                    |
        +-------------------+--------------------+
                            v
        panel (Assets > Network devices), audit, SIEM export,
        Repairs, bus events, count sensors
```

New integration modules:

- `inventory.py`: the device record, the identity rules, the observation
  merge, and the owner actions (acknowledge, ignore, watch, label, merge).
- `network_health.py`: the repeat-condition rules of phase 5.
- `oui.py` and a generated data file: vendor lookup on the integration side
  (phase 7).

Changed modules: `probe.py` (call the merge after storing the cycle),
`netscan.py` (schema additions), `detections.py` (new rule ids and threshold
specs), `health.py` (new checks), `store.py` (second Store file),
`websocket_api.py` (owner-only commands), `diagnostics.py` (redaction),
`sensor.py` (counts). The Probe changes in phases 2, 4, 6 and 8 only.

### Where a signal lands

HA SOC has two finding shapes and this design uses both, by this rule: an
**event** that happened at a moment becomes a detection, and a **condition**
that persists until fixed becomes a health finding mirrored to Repairs.

| Signal | Shape | Default severity |
| --- | --- | --- |
| Unacknowledged device appeared | detection `network_device_new` | medium |
| New open port on an acknowledged device | detection `network_port_opened` | medium |
| TLS certificate changed on an acknowledged device | detection `network_cert_changed` | medium |
| Acknowledged MAC seen with a different vendor-visible profile | detection `network_identity_shift` | high |
| Duplicate address | detection `network_duplicate_address` | high |
| Unexpected DHCP server (phase 6) | detection `network_rogue_dhcp` | high |
| Watched device gone, and back | detection `network_device_down` | low |
| Cleartext management service | health finding | by service |
| Certificate expired or near expiry | health finding | by days left |
| Devices dropping together, steady restarts, slower gateway | health finding | low |

`detections.py` describes itself as an engine "over the HA SOC audit log", and
`_upsert_detection` takes a `user_id`. Network detections have no user. They
reuse the row shape with `user_id=None` and the device id as `subject`, so the
existing open, acknowledge and resolve workflow, the SIEM export and the
Overview tiles work unchanged. Whether network detections may add points to
the posture score is an open decision (see the end).

## Data model

One record per device, in a new Store file `ha_soc.inventory` (private,
atomic writes, saved on a 300 second delay and on stop):

```json
{
  "id": "d_7k2m9x",
  "identity": "mac",
  "macs": ["aa:bb:cc:12:34:56"],
  "mac_kind": "global",
  "addresses": [{"network": "192.168.10.0/24", "ip": "192.168.10.42", "since": "..."}],
  "names": [{"value": "nas", "source": "dhcp", "ts": "..."}],
  "label": null,
  "vendor": {"value": "Synology", "source": "oui"},
  "first_seen": "...",
  "last_seen": "...",
  "verdict": "unacknowledged",
  "watched": false,
  "sources": ["probe_arp", "probe_tcp", "unifi"],
  "ports": {"443": {"service": "tls", "confidence": "high", "cert_sha256": "...", "first_seen": "..."}},
  "baseline": true
}
```

`verdict` is one of `unacknowledged`, `acknowledged`, `ignored`. `baseline` is
true for devices recorded during the learning window (below). The example
values are invented.

Bounds, fixed in code and not owner-tunable, so a hostile LAN cannot grow the
file without limit:

- 4,096 device records, matching the Probe's `MAX_TOTAL_HOSTS`.
- 8 names, 4 addresses and 64 ports per device.
- 2,000 change events in a ring.
- Presence segments for 30 days by default (tunable 7 to 90), merged so a
  device online all day costs one segment.

A device that stays unseen past the retention window and was never
acknowledged is pruned. An acknowledged or labeled device is never pruned
automatically, because losing the owner's verdict silently would turn a known
device back into an alert.

### Identity

The rule is MAC first, which is also what `config_ledger.py` chose for UniFi
devices.

1. **Globally administered MAC**: the MAC is the identity. A new IP for the
   same MAC is an address change on the same record.
2. **Locally administered MAC** (bit 1 of the first octet set, which is what
   phones use for private addresses): the MAC is still the key, the record is
   marked `mac_kind: "local"`, and the panel says "randomized address" where
   the vendor would be. Such a device rotating its MAC produces a new record.
3. **No MAC** (a host on a routed network, where the MAC does not cross the
   router): the key is network plus IP, the record is marked
   `identity: "address"`, and the panel labels it "address-keyed, weak
   identity". If a MAC later arrives for that address from UniFi or a router
   tracker, the record is re-keyed to the MAC.

Vedetta merges two phone records automatically when exactly two share a
distinctive name and were never online together for more than 30 minutes.
This design does not. In a security tool, a name is attacker-controlled: a
device that announces itself as an acknowledged phone's hostname would inherit
that phone's verdict. Instead the panel offers a **suggested merge** under
the same conditions, the owner confirms it, the action is audited, and the
merged record keeps the older record's history. Merging never happens without
that click.

### Learning window

On first enable, and after an owner-triggered "reset inventory", every device
seen during the first 24 hours (tunable 1 to 168) is recorded with
`baseline: true` and raises no detection. They still start `unacknowledged`,
and the panel shows the count to review. The posture term for unacknowledged
devices reads "provisional" during the window, following the existing
provisional-grade convention.

## Phases

Each phase ships on its own and is useful without the next. Phases 1 and 3
need no Probe change.

### Phase 1: inventory and new-device detection

Integration only. After `store.async_set_netscan_result`, `probe.py` calls
`inventory.async_merge_cycle(hosts, observed_at)`.

- Each host with a MAC is matched to a record or creates one. Hosts without a
  MAC on the Probe's own subnet are held for one more cycle before a record is
  created, because the ARP table is read before the sweep today and a host
  that answered TCP may simply not be resolved yet.
- UniFi clients (`unifi.py` `_normalize_client` already yields name, IP, MAC
  and VLAN) are merged as a second source. A device known to UniFi but never
  seen by the Probe is still a record, marked "seen by UniFi only, not
  probed". This is the equivalent of Vedetta's "networks seen by Home
  Assistant", using the controller data HA SOC already reads.
- Home Assistant's device registry is matched by MAC connection
  (`CONNECTION_NETWORK_MAC` in `helpers/device_registry.py`). A match adds the
  registry name and a "known to Home Assistant" chip that links to the device
  page. It does not acknowledge the device unless the owner turns on
  "acknowledge devices Home Assistant already manages" in Settings (off by
  default; the registry says a device was configured, not that it is still
  the same hardware).
- Detection `network_device_new` opens for a record created outside the
  learning window. Subject is the device id. Acknowledging the device resolves
  it; ignoring the device resolves it and suppresses the device from counts.
- Flood control: more than 10 new devices in an hour (tunable 3 to 100)
  collapse into one detection, `network_device_burst`, at high severity,
  listing the count and the first ten. An attacker rotating MACs cannot fill
  the detection table, and a burst is itself the more interesting signal.

Panel: a new tab "Network devices" in the Assets workspace, owner-only. A
sortable table (label or best name, vendor, addresses, first seen, last seen,
sources, verdict), a filter for unacknowledged, and row actions Acknowledge,
Ignore, Label, Watch. Every action is audited with the device id and the
acting user.

#### What phase 1 built

Built 2026-11-22: `inventory.py`, the `network_device_new` and
`network_device_burst` rules in `detections.py`, the merge call in
`probe.py`, three owner-only commands (`ha_soc/inventory/list`,
`set_verdict`, `set_label`), the "Network Devices" tab under Assets, and
`tests/test_inventory.py`. It differs from the text above in these ways, each
deliberate:

- **UniFi clients were not merged in the first build.** Added 2026-11-23:
  `merge_unifi_clients` creates a record for a client the Probe never saw
  (shown as "seen by UniFi only, not probed") and adds the controller's name,
  VLAN and SSID to one it did. The merge runs when a UniFi snapshot is taken,
  which is every six hours and whenever a tab that reads it is opened, not
  every cycle. See `decisions.md`.
- **Detections carry the device id and nothing else about the device.** The
  inventory is owner-only, while detection rows follow the panel's access
  level. A MAC, address or name in a detection would hand the inventory to
  every administrator once the owner opens the panel to them. The owner reads
  the device in the Network Devices tab by its id.
- **The burst rule keeps the first devices of the hour and collapses the
  rest.** With the threshold at 10, the ten oldest new devices in an hour get
  their own detection and the eleventh onward share one
  `network_device_burst` row. The split is by first-seen time with the id as
  tie-break, so it is the same on every pass.
- **A detection is raised only for a device first seen in the last 24 hours.**
  Without that bound, a detection the owner resolved without acknowledging
  the device would reopen after evidence retention pruned it.
- **Addresses carry no `network` field.** The Probe does not report which
  subnet a host was found on. The field arrives with phase 8.
- **The list command is not audited.** Decision D-14 audits mutations and
  privileged reads, not panel refreshes. Verdict and label changes are
  audited; a verdict change flushes immediately.
- **Not built:** Watch, suggested merge, reset inventory, and the
  "acknowledge devices Home Assistant already manages" setting. The inventory
  has no switch of its own: it records whenever the netscan reports.

Not verified: the tab in a running panel (the bundle builds, nothing more),
a merge of a real Probe cycle, and the size of `ha_soc.inventory` on disk.

### Phase 2: change detection and the certificate fix

Probe: `_read_tls_cert` calls `getpeercert(binary_form=True)`, reports
`sha256` of the DER, and reports the DER itself (base64, capped at 8 KiB) the
first time it sees a fingerprint. A small cache file under `/data` records
which fingerprints were already delivered and is cleared when the poll
response's generation changes or the owner requests a rescan, so a reinstall
of the integration gets every certificate again. `capabilities` gains
`tls_der: true` so the integration can tell an old Probe from a host without
TLS.

Integration: the DER is parsed with `cryptography` for subject, issuer,
validity and self-signed status. `cryptography` is not declared in
`manifest.json` today; it arrives through `asyncssh`. Whether to declare it
directly, as a range because Core constrains it, is a small decision to
record. Parsing happens in the executor, on bounded input, with every failure
mapped to "certificate unreadable" rather than an exception.

Rules, all on acknowledged devices only (an unacknowledged device already has
an open detection):

- `network_port_opened`: a port in the configured list is open that was not
  open in any of the device's previous 3 cycles in which the device was seen.
- `network_cert_changed`: the fingerprint on a port changed. Suppressed when
  the new certificate has the same subject and issuer and the old one was
  within 30 days of expiry, which is what a routine renewal looks like; the
  renewal is still written to the change ring.
- `network_identity_shift`: an acknowledged MAC shows a different set of open
  ports and a different certificate at once, or is present at two addresses
  in one cycle. This is the residual control for MAC spoofing, and it is weak:
  see "Threat model additions".

A port that closes is written to the change ring and raises nothing.

#### What phase 2 built

Built 2026-11-23: the certificate fix in the Probe's `netscan.py` and its run
script, `parse_certificate` and the schema keys in the integration's
`netscan.py`, certificate storage and change events in `inventory.py`, one
rule method for the three detections in `detections.py`, the ports,
certificates and recent changes in the Network Devices tab, and
`tests/test_inventory_changes.py`. The wire format is in `protocol.md`,
"Netscan certificate delivery". It differs from the text above in these ways:

- **No cache file on the Probe.** The integration lists the fingerprints it
  holds in the poll response and the Probe sends DER for the rest. A
  reinstall needs no invalidation rule. See `decisions.md`.
- **The capability is negotiated the other way round as well.** The Probe
  sends the new keys only to an integration that offers the list, because an
  older integration rejects them and would lose the whole report.
- **"Previous 3 cycles" is one constant used four ways.** A port is closed
  after more than 3 of the device's cycles shut; a port is newly opened when
  it appears for the first time or after being closed; a device's first 3
  cycles and a port's first 3 cycles in the scan list report nothing. A
  record stored by phase 1 has no cycle counters and so settles for 3 cycles
  after the update before it can alert.
- **A renewal is judged on parsed fields.** Same subject and issuer, both
  certificates readable, and the old one within 30 days of expiry or past it.
  A device can therefore pass a swapped certificate as a renewal by copying
  the subject and issuer of a certificate that is about to expire; the
  renewal is still in the change list in the panel.
- **An identity shift replaces the changes that make it up.** When ports and
  a certificate change in one cycle, or one MAC answers at two addresses,
  one `network_identity_shift` is raised and the separate port and
  certificate events are recorded without their own detection.
- **Two addresses are reported once per new address.** A device that always
  answers at two addresses (a second address on one interface, or a router
  answering ARP for other hosts) is learned during its first 3 cycles and
  raises nothing. Later, only an address not seen alongside the others
  before raises a shift. A router that answers ARP for many changing
  addresses will still be noisy; that is not handled.
- **The detections carry the device id, the time and the shift reason only**,
  for the reason given under phase 1.
- **`self_signed` means subject equals issuer.** The signature is not
  verified.
- **The stored netscan result changed shape.** TLS entries now carry
  `sha256`, and `not_after` is an ISO 8601 time where the old code would have
  sent OpenSSL's text form (it never did, because of the defect). The Scanner
  tab shows the string as given.
- **The Probe no longer prints the host list to its log**, only the count.

Not verified: a cycle from the built Probe image, the run script's `jq`
branch against a real poll response (the script was not executed), the new
table column in a running panel, and how many certificates a real network
presents against the 512 and 1,024 bounds.

### Phase 3: exposure findings from data already collected

Integration only (certificate checks need phase 2).

- `network_cleartext_service`: telnet is high; FTP and VNC are medium; a
  plain HTTP banner on a device that also serves the same host on 443 is
  informational. Severity is per service and listed in `operations.md`. The
  finding names the device and port and carries the same dismiss workflow as
  every other misconfiguration finding.
- `network_cert_expiry`: expired is medium, 14 days or less is low, 30 days
  or less is informational. A self-signed certificate is information only and
  never a finding by itself, which is the position `security.md` already
  takes.

Vedetta lists both as planned, not built. They are here because HA SOC already
holds the data.

#### What phase 3 built

Built 2026-11-23: `cleartext_exposures` and `certificate_expiries` in
`inventory.py`, the two checks in `health.py` that turn their rows into
misconfiguration findings on the five-minute sweep, and
`tests/test_inventory_exposure.py`. The per-check notes are in
`operations.md`. It differs from the text above in these ways:

- **A service is also recognized by its registered port.** The Probe reads
  without sending, so most Telnet servers match no banner signature. A
  finding made from the port number alone says so in its summary.
- **HTTP is one informational row for all devices**, not one per device, and
  it is judged by the ports being open, not by a banner. Whether port 80
  only redirects is not tested.
- **The finding carries the device id, port and service or expiry date.** The
  owner looks the device up by id in the Network Devices tab. No panel work
  was needed: the findings appear in the existing misconfiguration table and
  in Repairs.
- **Ignored devices are skipped**, and a finding resolves when the port
  closes or the device is ignored.
- **At most 100 findings per check per pass.** Rows past the cap are not
  reported and nothing says the cap was hit.
- **The default scan list limits what can be found.** It contains 23 but not
  21 or 5900, and TLS is attempted on eight fixed ports only, so FTP and VNC are
  seen only if the owner adds their ports, and a certificate on any other
  port is never seen.

Not verified: the findings in a running panel and in Repairs, and how many
informational HTTP rows a real network produces.

### Phase 4: presence history, latency, and gone/back alerts

Probe, three changes to the cycle, none needing a new privilege:

1. A refused connection is evidence of presence. `_probe_one` treats
   `ConnectionRefusedError` like a timeout today. It will report the host as
   `responded: true` with no open port.
2. The ARP table is read a second time after the sweep, with the flags
   column. The sweep's own connection attempts make the kernel resolve every
   on-link target, so an entry with the complete flag (0x2) after the sweep
   means the host answered ARP during this cycle. This yields roughly what an
   ARP sweep would, with no raw socket. Not verified: the kernel's neighbour
   cache timing on HAOS, and whether a stale entry can keep the complete flag
   across a full 300 second cycle. A test on the owner's network with a device
   unplugged mid-run settles it.
3. The connect time of the first completed or refused connection per host is
   reported as `rtt_ms`. It is a TCP round trip, not an ICMP one, and the
   panel labels it so.

Integration: a device is **present** in a cycle when it has a post-sweep
complete ARP entry, a completed or refused connection, or a UniFi client
record whose last-seen is inside the cycle. Presence is kept as merged
segments. A device with no possible signal (address-keyed on an unreachable
network) reads "unknown".

Alerts are opt-in per device through the Watch action:

- Down after 3 consecutive cycles without presence (tunable 2 to 24, so 10
  minutes to 2 hours at the current cadence).
- Back on the first cycle with presence, and only if a down was raised.
- Devices with a locally administered MAC cannot be watched, because a phone
  leaving the house is not an outage.
- A Probe that stops reporting is not a network of devices going down. When
  `probe_addon_not_reporting` is open, presence evaluation pauses and no down
  is raised.

#### What phase 4 built

Built 2026-11-23: the three Probe changes (refused connection as an answer,
second ARP read, `rtt_ms`), presence segments and the down and back events in
`inventory.py`, the `network_device_down` detection and its `down_cycles`
threshold, the owner-only `ha_soc/inventory/set_watch` command, the Watch
button and a presence line in the Network Devices tab, and
`tests/test_inventory_presence.py`. The wire format is in `protocol.md`,
"Netscan presence". It differs from the text above in these ways:

- **The second ARP read waits 9 seconds.** Without a wait, an address the
  sweep touched in its last seconds still shows its old entry. The wait is
  derived from Linux's default neighbour timers and was not checked on HAOS.
  The design's test, a device unplugged mid-run on the owner's network, is
  still the way to settle it.
- **UniFi is not a presence signal.** The controller's client list arrives
  every six hours, so it cannot place a device in a cycle. A device only the
  controller reports reads "presence unknown" and cannot be reported down.
- **The pause during a Probe outage needs no check of its own.** Presence is
  judged when a cycle arrives, so a Probe that stops reporting judges
  nothing. A cycle that arrives with no presence signal from any device is
  also skipped, which covers the Probe's host losing its network.
- **Back closes the down detection** instead of raising a second one.
- **Presence is judged for every probed device, alerts only for watched
  ones.** The tab shows "answering", "no answer for N scans" or "not
  answering since" for all of them.
- **The tab sends the last 24 hours of segments**, not 30 days, and shows a
  status line, not the 12-hour strip the Vedetta comparison describes. The
  file keeps 30 days, at most 512 segments per device.
- **Only the last `rtt_ms` is kept.** Phase 5's gateway rule needs a history,
  which it will have to add for the gateway alone.
- **Retention is fixed at 30 days**, not tunable from 7 to 90.

Not verified: any of this against a real network. In particular the ARP
flag behaviour after the wait, the size of `ha_soc.inventory` with 30 days
of segments, and the Watch button in a running panel.

### Phase 5: network health rules

`network_health.py`, evaluated after each merged cycle. The starting
thresholds are Vedetta's published ones (`docs/NETWORK_DOCTOR.md`), declared
in `THRESHOLD_SPECS` form so the Settings tab can tune them and reset them.

| Rule | Opens when | Starting thresholds |
| --- | --- | --- |
| Duplicate address | two MACs hold one IP at once, or alternate at it | both seen for 5 minutes, or 3 alternations in an hour |
| Drop together | many devices lose presence in one cycle | at least 5 devices and at least 1 in 10 |
| Steady restarts | one device drops repeatedly at a regular interval | 5 drops in a day, 2 minutes to 6 hours apart |
| Slower gateway | the gateway's `rtt_ms` rises against its own baseline | last 15 minutes at least 3 times and 3 ms slower than the previous 6 hours |

At a 300 second cadence the 2 minute lower bound for restarts cannot be
observed; the effective floor is one cycle, and the Settings text says so.

Duplicate address is a detection, because it is also what ARP spoofing looks
like from the outside. The other three are health findings at low severity.
A rule opens only when its condition holds on two evaluations (one for drop
together) and closes after three clean ones. Devices with locally
administered MACs are excluded from restart and drop counts.

The Probe sees duplicate addresses only as far as `/proc/net/arp` shows them,
which is one MAC per IP at a time, so the alternation form is the one it can
catch. UniFi client data can show the simultaneous form. The finding states
which source saw it.

### Phase 6: network roles

- **Gateway**: the Probe reads the default route from `/proc/net/route`
  (inside the existing `/proc/net` grant) and reports the next hop. The
  inventory tags that device.
- **DNS and DHCP servers as configured**: from UniFi's network configuration
  where a controller is connected. For installs without one, the Supervisor's
  network information may carry the host's gateway and nameservers; that
  endpoint and its field names are not verified in this document and belong in
  `protocol.md` before code depends on them.
- **Double NAT and CGNAT**: flagged when UniFi's derived WAN address is in a
  private range or in 100.64.0.0/10 (`risk.py` already classifies global
  addresses). No external "what is my IP" service is ever called. Without a
  controller this reads "not available", not "no".
- **Unexpected DHCP server**: the only way to see a second server is to ask.
  The Probe would broadcast one DHCPDISCOVER per cycle from UDP port 68 and
  list every server that offers, never completing a lease. UDP is inside the
  AppArmor profile and `net_bind_service` is granted. Not verified: whether
  port 68 is free on the HAOS host under host networking. This sub-feature is
  off by default with its own setting, because it is the one place this design
  transmits something other than a TCP connection. A responder that is not in
  the owner-accepted list opens `network_rogue_dhcp`.

### Phase 7: names and vendors

Names come from sources Home Assistant already holds. Nothing new listens on
the network.

| Source | How it is read | Status |
| --- | --- | --- |
| Owner's label | set in the panel | never overwritten |
| Device registry name | MAC connection match | API verified in the core clone |
| UniFi client name | `unifi.py` | already built |
| DHCP hostname | `dhcp.async_discovered_service_info(hass)` | verified in core 2026.11.0; returns MAC without colons, lowercase |
| Router device tracker `host_name` | state attributes of router-sourced trackers | not verified; `device_tracker` is not in the local core clone |
| Certificate subject | phase 2 | depends on the fix |
| mDNS name | core's shared zeroconf instance | not designed yet; which call reads the cache without adding queries is unverified |

The table order is the precedence. The panel shows the winning name with its
source, and the device detail lists every name seen with its source and time.
`dhcp` must be added to `after_dependencies` in `manifest.json`. The two
`_internal` helpers in `dhcp/helpers.py` are not used; their names say what
they are.

Vendor: the Probe's `oui_prefixes.py` is, in its own words, static and
non-exhaustive. Vendor lookup moves to the integration, against a table
generated at release time from the IEEE registry and shipped inside the
integration zip, with the registry date recorded beside it. The Probe's table
is then retired and the Probe stops sending `vendor`. Size and format of the
generated table are to be measured; Vedetta ships the raw registry at about
1.9 MB, which is too large to add to the HACS download as plain text without
checking. A locally administered MAC gets no vendor lookup.

### Phase 8: routed networks

The Probe sweeps only the subnets of its own interfaces
(`_local_ipv4_networks`). This phase lets the owner add up to 8 further IPv4
networks, each from /22 to /30, in Settings.

- **Try before add**: one bounded sweep of the candidate network, results
  shown, nothing saved until the owner confirms. The trial and the add are
  audited.
- Added networks ride the existing `poll_netscan_config` response with the
  same generation token. The Probe's `MAX_TOTAL_HOSTS` cap still applies
  across all networks.
- Networks the Probe refuses regardless of configuration: loopback,
  link-local, multicast, public ranges, and the Supervisor's own Docker
  bridges. The refusal list is enforced in the Probe, not only in the
  integration, so a bad poll response cannot widen the scan.
- Devices there are address-keyed until UniFi or a tracker supplies the MAC.
  Reading the router's ARP table over SNMP, which is how Vedetta gets MACs
  without a controller, is deferred: the Probe hosts an SNMP agent, not a
  client, and a stored community string is a new secret to design for.
- A network that is paused, removed, or unreachable reads "not scanned".

### Phase 9: Home Assistant surface

- **Events**, off by default, one switch in Settings:
  `ha_soc_network_device_new`, `ha_soc_network_device_down`,
  `ha_soc_network_device_back`. The payload is the device id, the owner's
  label if one is set, and for "back" the minutes away. MAC and IP are
  included only when a second switch is on. Subscribing to an event type
  outside Core's allowlist requires an admin connection
  (`websocket_api/commands.py`, `handle_subscribe_events`), but an automation
  trigger has no such check, so the default payload is the minimal one.
- **Sensors**: devices known, unacknowledged, watched and offline. Counts
  only, no attributes.
- **Notifications**: alerts reach a phone through an automation on the events
  above, shipped as two blueprints under `blueprints/automation/ha_soc/`
  (new device, watched device offline). HA SOC does not call `notify`
  services itself, which keeps recipient configuration in one place the owner
  already knows.
- **Repairs**: health findings from phases 3 and 5 mirror through the existing
  path in `health.py`.

### Phase 10: export, redaction, translations, tests

- **Inventory export**: CSV and JSON from the panel, owner-only, recorded in
  the audit chain as a privileged read like the existing ones.
- **Diagnostics**: `diagnostics.py` must never emit the inventory in clear.
  Device count, source coverage, rule states and store sizes are included;
  MACs, addresses, names and certificate subjects are replaced by stable
  per-download pseudonyms so two lines about one device still correlate. A
  test asserts that no MAC or private address pattern survives in the output.
- **Translations**: Vedetta ships five locales; HA SOC ships
  `translations/en.json` only. How much panel text lives in TypeScript rather
  than in translation files was not checked for this document, so this item
  starts with that audit, and new inventory strings go into translation files
  from the first commit either way.
- **Replay corpus**: Vedetta tests against recorded real networks and a
  simulated LAN. The equivalent here is a set of scenario files under
  `tests/fixtures/netscan_scenarios/`, each a sequence of cycles with the
  expected records, detections and findings: a device joining, a DHCP
  renumbering, a rotating phone, a certificate renewal, a Probe outage, a
  MAC-rotation flood. The inventory engine is a pure function of
  (previous state, cycle, clock), which is what makes replay possible, and
  the design should keep it that way.
- **Carried from the comparison, outside this feature**: an OpenSSF Scorecard
  workflow, and signed Probe images, which `backlog.md` already lists as
  deferred.

## Access control and audit

Every `ha_soc/inventory/*` and `ha_soc/network_health/*` WebSocket command is
owner-only, enforced server-side per command. Mutations (acknowledge, ignore,
label, watch, merge, add or remove a network, reset inventory, accept a DHCP
server) are audited with the acting user and the device or network id.
Export and the device detail read are audited as privileged reads. Reset
inventory states what it deletes before the owner confirms, and it cannot be
undone.

## Threat model additions

These rows were added to `THREAT-MODEL.md` on 2026-11-23, with the residual
gaps as they stand after phase 2.

- **A LAN device controls its own MAC, hostname, banner and certificate.**
  Every such string is length-bounded at ingest and rendered as text. None is
  used in an access decision.
- **MAC spoofing inherits a verdict.** A device that clones an acknowledged
  MAC is, to this inventory, the acknowledged device. `network_identity_shift`
  catches the clumsy cases only. The panel and `security.md` must say plainly
  that "acknowledged" means "the owner recognized this MAC once", not "this
  device is authenticated". 802.1X is the real control and is out of scope.
- **Alert flooding by MAC rotation.** Bounded by the burst rule and the
  record cap; when the cap is hit the oldest unacknowledged, never-labeled
  records are pruned first and a finding says the cap was reached.
- **A compromised Probe fabricates or hides devices.** The Probe is already
  trusted for listening ports and firewall state; this widens what it can lie
  about, not who can speak for it. UniFi as an independent second source
  limits it where a controller exists: a device the controller sees and the
  Probe never does is shown as such.
- **The inventory file is a map of the house.** Private Store file, owner-only
  commands, redacted diagnostics, minimal event payloads, and no entity
  attributes.

## Feature coverage against Vedetta

| Vedetta feature | Here |
| --- | --- |
| Device record that follows the device, not the address | Data model, phase 1 |
| Private-MAC phones recognized and merged | Recognized (phase 1); merge is owner-confirmed only |
| New-device event | Phase 1 detection, phase 9 event |
| 30 days of presence, last 12 hours at a glance | Phase 4 |
| Gone and back alerts to a phone | Phases 4 and 9, through a blueprint |
| Port change alerts against a baseline | Phase 2 |
| Network doctor (four rules) | Phase 5 |
| Gateway, DHCP, DNS, double NAT, public IP | Phase 6; public IP only from the controller |
| Names from many sources, source shown | Phase 7, fewer sources |
| Passive mDNS and DHCP listener | Phase 7, by reading Core's own listeners |
| Full vendor registry | Phase 7 |
| Networks behind the router | Phase 8 |
| Devices seen by Home Assistant, never probed | Phase 1 (UniFi), phase 7 (trackers) |
| Inventory export | Phase 10 |
| Masked export for bug reports | Phase 10 (diagnostics) |
| Five languages | Phase 10, starting with an audit |
| Simulated LAN and replayed exports in tests | Phase 10 (scenario replay) |
| Signed images, Scorecard | Phase 10, outside this feature |
| Three scan levels, deep scan with nmap | Not adopted: no bundled scanner |
| Weighted type recognition, signatures, brand logos | Not adopted |
| MQTT sharing of devices | Not adopted: conflicts with D-19 |
| Wake-on-LAN, tile and list views | Not adopted |
| Planned in Vedetta: cleartext services, certificate expiry | Phase 3 |
| Planned in Vedetta: second DHCP server | Phase 6 |
| Planned in Vedetta: UPnP/IGD exposed ports | Not in this design; needs an SSDP exchange the Probe does not have |

## Open decisions for the owner

1. Do network detections add points to the posture score? Recommended: an
   "unacknowledged devices" term and a "duplicate address" term, both shown
   with their points like every other factor, and nothing from presence.
2. Should a device known to the Home Assistant registry be acknowledged
   automatically? Recommended: no, behind a setting.
3. Is the DHCPDISCOVER probe acceptable at all, given that everything else is
   TCP connect and `/proc` reads? Recommended: build it last and off by
   default.
4. Does `cryptography` get declared in `manifest.json`, or does certificate
   parsing stay dependent on `asyncssh` bringing it in?
5. Is 300 seconds the right cadence once presence depends on it? A shorter
   cycle sharpens down detection and multiplies connection attempts on the
   LAN.
6. Tab placement: "Network devices" under Assets as proposed, or folded into
   the existing Network tab, which today is UniFi-only.

## Verification list

Facts this design depends on that were not verified while writing it:

- The Probe's Python version on the built image, and a live confirmation of
  the empty certificate fields.
- AppArmor's actual treatment of raw sockets under the current profile.
- Neighbour cache behaviour on HAOS: whether the post-sweep complete flag is a
  reliable per-cycle presence signal.
- Whether a refused connection surfaces as `ConnectionRefusedError` for every
  target the Probe reaches, including hosts behind a routing hop that drops
  instead of rejecting.
- The Supervisor network information endpoint and its fields.
- UDP port 68 availability on the host under host networking.
- Router device tracker attribute names (`ip`, `mac`, `host_name`) and source
  type in core 2026.11.
- A zeroconf read path that adds no queries of its own.
- The size of a compact generated OUI table, and of the inventory Store at
  100, 500 and 4,096 devices with 30 days of segments.
- How much panel text is outside `translations/`.
- Everything about Vedetta beyond its documentation: its source was not read.
