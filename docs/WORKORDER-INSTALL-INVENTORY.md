# Work Order: Install Inventory & Provenance Reporting

**Repo:** `trooperthorn/ha_Int_soc` (`~/repos/ha_Int_soc`)
**Target module:** `custom_components/ha_soc/unused_installs.py` (extend; do not rewrite)
**Raised:** 2026-09-22, from a live audit of El Rancho Assist (HA 2026.9.3)
**Type:** Feature — new hygiene checks + a reporting surface
**Prerequisite:** Invoke the `ha-dev-current` skill before writing any code. All core/HACS API shapes must be looked up against the local clones, not recalled.

---

## 1. Why this exists

A manual audit of the live instance answered the question *"which custom integrations and cards are installed but unconfigured and unused?"* — and then *"when were they last updated, and were they installed by HACS or placed by hand?"*

Answering it took a websocket session, an SSH session to the HA host, and four rounds of cross-referencing. **The SOC integration already owns most of the primitives but cannot produce this report**, and three of the findings it structurally cannot see at all.

The audit removed 40 HACS repos and 4 hand-placed paths. The point of this work order is that the *next* audit should be a panel tab, not an afternoon.

---

## 2. What already exists (do not rebuild)

`unused_installs.py` (297 lines) ships four checks, all returning `HygieneResult` with the tri-state status, all wired into `health.py` (lines ~1728–1780):

| Function | Answers |
|---|---|
| `async_integrations_without_entry` | custom_components dirs with no entry, no YAML setup, and no loaded dependent |
| `async_entries_without_entities_or_devices` | loaded entries owning neither entity nor device |
| `async_hacs_not_loaded` | HACS rows HA never loads (integration domain not loaded; plugin with no `/hacsfiles/<repo>/` resource) |
| `async_unused_dashboard_resources` | resources on disk whose registered custom elements no dashboard's `type: custom:*` references |

Design rationale is in `docs/design.md` §288–293; boundary reasoning in `docs/security.md` and `docs/THREAT-MODEL.md` §51. Tests in `tests/test_unused_installs.py`.

**Respect the existing contract:** every helper reports only what it can prove, and an unreadable source degrades to `could_not_evaluate` rather than "nothing found". Every addition below inherits that rule.

---

## 3. Gaps, with evidence from the live instance

### G1 — No provenance dimension (HACS-managed vs. hand-placed)

Nothing distinguishes code HACS downloaded from code someone copied in. The audit found three hand-placed items that **no existing check would ever surface**, because `async_hacs_not_loaded` only iterates HACS's own rows:

- `/config/custom_components/airthings_ble/` — a re-domained private copy, `version: 0.1.0`, root-owned, mtime 2026-08-20
- `/config/www/community/frigate-hass-card/` — 39.1 MB orphan, mtime 2025-02-17
- `/config/www/homeseer-wd200-status-card.js` + a second copy under `www/community/` — 2023-era, unregistered

This is the highest-value gap. Hand-placed code is unsigned, un-updatable, invisible to HACS update checks, and is exactly what `docs/THREAT-MODEL.md` cares about. **A hand-placed integration that IS configured is equally invisible today** — provenance must be reported independently of whether the item is used.

Note `/config/www/community/android-tv-card/` is hand-placed *and* in active use (serves `custom:universal-remote-card`). Provenance is a property to report, not a finding to resolve.

### G2 — No staleness or version metadata

The report needs "when was this last updated". Nothing currently surfaces upstream last-update, installed vs. available version, or on-disk mtime. The audit needed all three: e.g. `victorsmartkill` last pushed 2025-03-31 with a folder untouched since 2025-01-03 (dead upstream), versus `irrigation-unlimited-card` claiming `2026.5.0` from a folder dating to 2023-05-05 (a stale download that needs reinstalling, not removing).

### G3 — Dangling resource registrations are not detected

Deleting `www/community/frigate-hass-card/` left its Lovelace resource registered, pointing at a now-missing file — a 404 on every dashboard load. `_resource_path()` already resolves the path; nothing checks that the target exists. This is the mirror image of the checks the module already does and is cheap to add.

### G4 — Two checks disagree, and the weaker one is not labelled as weaker

`async_hacs_not_loaded` decides a plugin is unused by testing for a `/hacsfiles/<repo_name>/` resource marker. That only proves a resource entry exists — not that any dashboard uses it. `async_unused_dashboard_resources` does the real element-level test.

The audit hit this hard: matching by repo folder name produced false positives on `Helios` (`helios.js` → `custom:helios-card`), `ha-sankey-chart` (→ `custom:sankey-chart`), `lovelace-horizon-card` (→ `custom:horizon-card`), `lovelace-layout-card` (→ `custom:grid-layout`), `lovelace-mushroom` (→ `custom:mushroom-*`), `ha_card_windrose` (→ `custom:windrose-card`), and every other repo whose folder name differs from its element name. It also misses `card_mod`, which is used via a `card_mod:` config key rather than a `custom:` type at all (84 occurrences on this instance), and `kiosk-mode`, used via a `kiosk_mode:` key.

**Required:** the element-level result is authoritative. Where the two disagree, report the element-level verdict and suppress the name-based one. Add the `card_mod:` / `kiosk_mode:` key-usage exception so config-key-consumed bundles are never reported unused.

### G5 — Duplicate and shadowing installs are invisible

Two live cases: `solaredgeoptimizers` is installed from **two** HACS repos (`AndrewTapp/` and `ProudElm/`) writing the same `custom_components/` folder — whichever downloaded last wins. And `custom:music-flow-card` was registered by two different bundles (`ha_card_music` and `homeii-music-flow`), a live element-name collision whose winner depends on resource load order.

Both are correctness hazards, not merely tidiness.

### G6 — No disk footprint

A 39 MB orphan sat unnoticed. Size per item makes the report actionable and ranks cleanup value.

### G7 — There is no report, only findings

The existing checks emit health findings. What was actually needed was an **inventory**: every custom integration and dashboard element, one row each, with provenance, version, staleness, usage state, path, and size — including the healthy rows. A findings list cannot answer "show me everything and let me decide."

---

## 4. Scope

### 4.1 New/changed checks in `unused_installs.py`

1. `async_untracked_installs(hass)` — walk `custom_components/` and `www/` (incl. `www/community/`), subtract everything HACS claims, report the remainder with full path, mtime, and size. Must handle the loose-file case (`homeseer-wd200-status-card.js` sitting directly in `www/` and again in `www/community/`), not just directories. Degrade to `could_not_evaluate` when the HACS row set is unreadable — otherwise every HACS item would be misreported as hand-placed.
2. `async_dangling_resources(hass)` — registered resources resolving to a path that does not exist on disk. Reuse `_resource_path()`; keep the existing realpath anchoring.
3. `async_duplicate_installs(hass)` — (a) two HACS repos claiming one local path; (b) one custom element name registered by more than one bundle. Reuse `_defined_elements_sync()` for (b).
4. Extend `async_hacs_not_loaded` per G4: suppress plugin findings contradicted by the element-level check, and exempt bundles consumed via config keys.

### 4.2 Metadata enrichment

Add to every row, where determinable: `local_path`, `installed_version`, `available_version`, `last_updated` (upstream), `disk_mtime`, `size_bytes`, `provenance` (`hacs` | `manual` | `unknown`), `usage` (`configured` | `loaded_only` | `unused` | `undeterminable`).

Each is best-effort and independently degradable — a missing `last_updated` must not drop the row.

### 4.3 Reporting surface

- A websocket command in `websocket_api.py` returning the full inventory (every row, not only findings), following the existing command shape and permission gate.
- A panel view rendering it as a sortable table with provenance and staleness chips, consistent with the HACS owner-chip work in #123.
- CSV/JSON export through the existing report path (`docs/reports/`), so an audit can be diffed against the previous one.

### 4.4 Tests — `tests/test_unused_installs.py`

Extend, don't fork. Cover at minimum: hand-placed dir; hand-placed loose file at both `www/` and `www/community/`; hand-placed-but-used (the `android-tv-card` shape) reported as provenance only, never as a finding; HACS-unreadable → `could_not_evaluate` for untracked; dangling resource; two repos → one path; one element → two bundles; folder-name/element-name mismatch suppression (the `Helios`/`sankey`/`horizon`/`layout`/`mushroom` shapes); `card_mod:` and `kiosk_mode:` key usage exemptions; missing-metadata rows surviving enrichment.

### 4.5 Docs

Update `docs/design.md` §288–293 (the four-helper description is now wrong), `docs/security.md` (see §5 below), `docs/THREAT-MODEL.md` §51 (the local-read list grows), and `docs/ENTITY-MAP.md` if entities are added.

---

## 5. Verified reference data — resolves an open item in `docs/security.md`

`docs/security.md` §347 records that the HACS attribute names are unverified. **They were verified live on 2026-09-22** against HACS on HA 2026.9.3, via `hacs/repositories/list` over the websocket API. Every installed row carried:

```
authors, available_version, installed_version, config_flow, can_download,
category, country, custom, description, domain, downloads, file_name,
full_name, hide, homeassistant, id, installed, last_updated, local_path,
name, new, pending_upgrade, stars, state, status, topics
```

Field notes from the live data:

- `local_path` is a **full absolute path** (`/config/custom_components/measureit`, `/config/www/community/button-card`) — authoritative for provenance matching; prefer it over deriving a path from `full_name`.
- `last_updated` is an ISO-8601 Z timestamp of the **upstream repo**, not the install date. Use `disk_mtime` for install recency; they diverge widely and the divergence is itself signal (see G2).
- `category` observed: `integration`, `plugin`, `theme`. Themes were **not** classifiable in the audit — theme usage lives in per-user frontend settings. Either solve it or declare it `undeterminable`; do not report themes as unused.
- `installed_version` vs `available_version` mismatch is a real state (`homekit_controller_pro` showed `v2026.08.20.00` installed against `v2026.08.20` available — a CalVer tag-shape mismatch, not a true upgrade).
- `domain` is populated for integrations, `file_name` for plugins.

This is a websocket-surface confirmation; the module reads the same data via `hacs.repositories.list_all` in-process. **Confirm the in-process attribute names still map 1:1 before removing the caveat from `security.md`** — the `getattr`-with-defaults pattern and the `could_not_evaluate` degradation stay regardless.

---

## 6. Constraints

- **No new egress.** Every check is a local read. Nothing leaves the instance; nothing is written. The `rm` operations in the audit were manual and stay manual — this work order adds *visibility only*, no remediation actions.
- **Keep the realpath anchoring.** `_defined_elements_sync()`'s base-directory check and the 8 MB read cap are load-bearing; new filesystem walkers must adopt the same rails.
- **Widening the walk widens the trust boundary.** Walking all of `www/` (not just `www/community/`) is new surface — update `THREAT-MODEL.md` §51 and justify it in `security.md`.
- **Performance.** A `du`-style size walk over `www/` can be expensive (39 MB in one card folder; thousands of files). Size must be lazy, capped, or executor-offloaded — never on the event loop.
- **Root-owned files.** HA runs as root in Supervised; the audit's non-root SSH user could not delete them. Reads are fine, but do not assume write access anywhere.
- No upstream contributions — findings against HACS or core stay as documented follow-ups.

---

## 7. Acceptance criteria

The feature is done when, against a live instance, a single panel view reproduces the audit this work order came from:

1. Lists every custom integration and dashboard element with provenance, version, upstream last-update, disk mtime, size, path, and usage state.
2. Flags all three hand-placed items the audit found by hand — including one that is in active use, reported as provenance rather than as a finding.
3. Flags a dangling resource registration.
4. Flags the duplicate-repo and duplicate-element cases.
5. Produces **zero** false "unused" verdicts across the instance's live card set — specifically none for `Helios`, `ha-sankey-chart`, `lovelace-horizon-card`, `lovelace-layout-card`, `lovelace-mushroom`, `ha_card_windrose`, `ha_card-mod`, or `kiosk-mode`.
6. Degrades visibly to `could_not_evaluate` — never to a clean bill of health — when HACS, Lovelace, or the filesystem cannot be read.
7. Exports a diffable report.

---

## 8. Out of scope

- Remediation (uninstall/delete) from the panel. Visibility first; destructive actions are a separate work order with its own confirmation design.
- Theme usage attribution, unless a clean per-user frontend-settings read exists.
- Anything touching HACS's own storage. Read-only, always.

---

## 9. Process

Branch, PR against `main`, CI green, then the CalVer release PR **merges last** with auto-merge disabled. Standard HA SOC baseline applies. Record any unproven assumption in `docs/security.md`'s Unverified list rather than asserting it.
