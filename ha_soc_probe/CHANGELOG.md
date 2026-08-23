# Changelog

## 2026.08.23.4

- Security: both add-on services now send a per-install secret (generated
  once and stored in the add-on's own `/data`) on every call into Home
  Assistant. HA SOC pins the first secret it sees and rejects any later
  ingest/poll call that can't present it, so a forged local service call
  can no longer spoof a port report or a firewall test outcome. No key
  management for you — the secret is created and shared between the two
  services automatically.
- Firewall: a rule that fails to apply now aborts the whole apply and
  restores the pre-test ruleset immediately (rather than leaving a
  partially-applied set live), and the failure is reported back to HA SOC.
- Hardening notes added to the port-scanner service documenting the
  recommended non-root privilege drop (left un-applied pending validation
  against a real Supervisor) and a base-image digest pin.

## 2026.08.23.3

- Added: optional host firewall read/write, gated behind a new `NET_ADMIN`
  capability this add-on now requests in `config.yaml` (a documented -1 on
  the Supervisor security rating — see the HA SOC integration's README).
  A new, second background service polls HA SOC every ~5s for a proposed
  ruleset, applies it to a dedicated `HA_SOC_RULES` iptables chain this
  add-on owns outright (never the raw `INPUT` chain, never anything Docker
  itself manages), and arms a fully local, self-contained revert timer the
  moment it applies anything — a plain backgrounded `sleep` in this same
  process, not a callback that depends on the network path it just changed
  still working. A ruleset backup (`iptables-save`) is taken before every
  apply; an unconfirmed test is restored automatically once its window
  elapses, and if this add-on itself crashes or restarts mid-test, the
  next startup finds the unresolved test and restores it immediately
  rather than trusting a timer that died with the old process.
- Changed: `iptables` and `iproute2` are now installed in the add-on image
  (previously `iproute2`'s presence was merely assumed).

## 2026.08.23.2

- Added: each reported open port now includes its bind address (e.g.
  `192.168.10.5`, or `0.0.0.0` for "every interface") and, for an IPv4
  address, a best-effort match against the host's real network interfaces
  (`eth0.10`, etc.) — real, not guessed, since this add-on already shares
  the host's network namespace. Meant for installs segmenting VLANs: a
  service listening on `(all interfaces)` is reachable from every VLAN,
  not just the one it's meant for. IPv6 bind addresses are reported as
  `null` rather than risk decoding them incorrectly — see run.sh's
  comments for why.

## 2026.08.23.1

- Changed: version numbering switched from pre-1.0 semver (`0.1.x`) to
  calendar versioning, `YYYY.MM.DD.V` — the release date plus a same-day
  revision counter starting at 1 (e.g. the first release on August 23,
  2026 is `2026.08.23.1`; a second release that same day would be
  `2026.08.23.2`). Matches the HA SOC integration's own version scheme so
  the add-on and the integration it reports to always carry a directly
  comparable, unambiguous release identifier — no more guessing whether
  `0.1.1` is newer or older than whatever the integration itself is on.

## 0.1.1

- Fixed: a rejected report (commonly a few seconds/minutes of HTTP 400
  right after Home Assistant Core itself restarts, while the HA SOC
  integration is still loading) no longer waits out the full
  `scan_interval_hours` (up to 24h) before trying again. It now holds in a
  short, capped-exponential retry loop (30s up to 5min) instead, and logs
  a clear, repeating "Holding — ..." warning while it does — so a
  half-connected setup is visible in the add-on's own log rather than
  just going quiet for hours. The HA SOC integration also now raises a
  Repairs issue if the add-on stays installed and running without ever
  successfully reporting for more than 30 minutes.

## 0.1.0

- Initial release. Reports the host's real listening TCP ports to the
  HA SOC integration on a configurable interval. Port + protocol only —
  no process-name attribution (see DOCS.md for why).
