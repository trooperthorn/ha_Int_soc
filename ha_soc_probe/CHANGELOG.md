# Changelog

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
