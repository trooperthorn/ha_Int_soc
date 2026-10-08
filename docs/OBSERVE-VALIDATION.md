# Observe validation record for the OTLP mapper

This record states how the golden files in `tests/fixtures/observe_otlp/` were checked against the receiving side, and what the check proved. The mapper is `custom_components/ha_soc/otlp_mapper.py`; the contract is Observe's own code and `docs/DATA-API-DESIGN.md` section 3.4 in the Observe repository.

## What was run

- Date: 2026-10-07.
- Observe checkout: `ipMontior` at commit `c4bb7e1`, read only. Nothing in it was changed and no byte code was written there.
- Method: a throwaway script outside both repositories imported Observe's own `observe.otlp.normalize`, `observe.otlp.wire`, `observe.otlp.encode` and the FastAPI application from `observe.web`, with a temporary SQLite database. The `argon2` module is not installed on the build host and is not used by the ingest routes, so the script replaced it with an empty stand-in. No network host was contacted and no Home Assistant instance was involved.
- Input: `tests/fixtures/observe_otlp/metrics.json` and `logs.json`, sent with a host-bound ingest key for the host `haos-lab`, which equals the resource `host.name`.

## Repeat run after the mapping fixes

- Date: 2026-10-07. Observe checkout `ipMontior` at commit `732b7db`, read only, with byte code writing turned off.
- Method: a throwaway script outside both repositories imported `observe.otlp.normalize` and ran `normalize_metrics` and `normalize_logs` on the regenerated golden files with the bound host `haos-lab`. The ingest routes were not repeated; the mapper change does not touch the envelope.
- Result: 38 samples and 5 events accepted, 0 rejected. The three ESPHome fixture rows arrive as one `observe.ha.integration.errors` sample (24), the dry-run bundle produces no event, and the watchdog event's dedup key is the episode start.
- The throwaway script was not kept, so this is an attestation like the first run.

## Repeat run after the payload value fixes

- Date: 2026-10-07. Observe checkout `ipMontior` at commit `5279692`, read only, with byte code writing turned off.
- Method: a throwaway script outside both repositories imported `observe.otlp.normalize` and ran `normalize_metrics` and `normalize_logs` on the regenerated golden files with the bound host `haos-lab`. The ingest routes were not repeated; the change does not touch the envelope.
- Result: 43 samples and 5 events accepted, 0 rejected. The new series are `observe.ha.repair.domain_issues`, `observe.ha.supervisor.unhealthy_reason` and `observe.ha.push.rows_dropped`; the three ESPHome fixture rows arrive as one `observe.ha.integration.errors` sample of 12.
- The throwaway script was not kept, so this is an attestation like the earlier runs.

## Availability and identity fields

- Date: 2026-10-07. Not run against Observe in this slice: no Observe checkout was executed. The golden files were regenerated with `os.type`, `observe.agent.sent_at` and `observe.source.available`, and `tests/test_otlp_mapper.py` repeats the reading rules of `observe/otlp/normalize.py` for them (a string `os.type` becomes the platform, `service.version` the agent version, an `intValue` send time between 0 and 253402300800, a source point with the attribute `observe.source` and the reason on the first). Repeat the run above against the then-current Observe checkout and add a dated row.

## Provenance

The throwaway script and its output were not kept, so the results below are an attestation by the person who ran it, not an artifact this repository can replay. Nothing here can be re-checked without the Observe checkout at `c4bb7e1`. The limit checks in `tests/test_otlp_mapper.py` are the part verified on every run. An UPDATE_GOLDEN run fails on purpose after writing the files, so it can never pass in CI by accident.

## Results

| Check | Result |
|---|---|
| `normalize_metrics` on the metrics golden file | 37 samples accepted, 0 rejected, no reject reasons |
| `normalize_logs` on the logs golden file | 5 events accepted, 0 rejected |
| Samples and events as stored | 37 rows in `samples`, 5 rows in `host_events` after the posts below |
| `POST /v1/metrics` and `POST /v1/logs`, JSON with gzip and an `Idempotency-Key` | 200 with an empty body (no partial success) |
| The same request replayed with the same key | 200 with an empty body (recognised before decoding) |
| The same request as protobuf (Observe's encoder, then its decoder) | 200, no partial success |
| A resource whose `host.name` is another host | 403, key bound to another host (nothing stored) |
| Gzip inflate guard and JSON depth guard (`inflate`, `too_deep`) | both pass on the golden files |
| Host name comparison | case-insensitive, so the key host may be written `HAOS-Lab` |

Event kinds seen by the normaliser: `observe.ha.watchdog.breach` (warning, source `watchdog`) and `observe.ha.crash` (critical, warning and info by classification, source `crash_forensics`, with `observe.boot_id` set to the bundle id).

## Limits repeated in the test suite

`tests/test_otlp_mapper.py` repeats the limits of Observe's normaliser so a drift in the mapper fails here without needing the Observe source: metric names match `^[a-z][a-z0-9_.]{0,127}$`, units match its character set, at most 32 point attributes and 64 resource attributes, attribute values at most 1,024 characters, at most 5,000 points and 500 log records per request, and a body of at most 1 MiB (checked plain and gzipped) for an install with 80 add-ons, 300 breach detections, 300 crash bundles, 400 integrations and 400 repair domains. The mapper caps row counts so a request stays inside those limits whatever the install size.

## Repeating the check

Run the golden tests with `UPDATE_GOLDEN=1` only after an intended mapping change, review the fixture diff, and repeat the run above against the then-current Observe checkout. Add a dated row to this file.
