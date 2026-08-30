# Feasibility report: should HA SOC take over HACS's ingestion and upgrade role

Requested: research whether HA SOC should absorb HACS's job of installing and
upgrading Integrations, Themes, Templates, Dashboards, and Apps from GitHub,
on the premise that HACS carries an intrinsic security issue and HA SOC
should own that surface directly. This document is a report for discussion,
not a decision. Nothing in it has been implemented; no work plan item or
decisions-register entry has been created from it. It is grounded in a
direct source read of `hacs/integration` at commit `c462d30` (2026-08-30),
not general recollection of what HACS is "supposed to" do, plus a
correction pass done by re-reading the two riskiest code paths myself
rather than trusting a single source.

## 1. What HACS actually manages today

HACS supports exactly six categories, defined in
`custom_components/hacs/enums.py`: `integration`, `plugin`, `theme`,
`python_script`, `template`, `appdaemon`. Two of the user's five named
areas do not map onto HACS the way they sound like they should:

| User's term | What HACS actually has | Where it lives after install |
|---|---|---|
| Integrations | `integration` category, matches directly | `custom_components/<domain>` |
| Themes | `theme` category, matches directly | `themes/<name>.yaml`, hot reloaded |
| Templates | `template` category is a single custom Jinja **macro/filter file**, not a dashboard or scripting template | `custom_templates/`, hot reloaded |
| Dashboards | **Not a HACS category at all.** What HACS calls `plugin` is a Lovelace **frontend resource** (a JS module: a custom card, a more-info dialog) that augments an existing dashboard. HACS has no concept of installing or managing a dashboard's own configuration. | `www/community/<repo>`, auto-registered as a Lovelace resource |
| Apps | `appdaemon` category only. **NetDaemon is not a current HACS category** - the only trace of it in the source is a dead config key that is explicitly ignored (`base.py`: `if key in {"experimental", "netdaemon", ...}: continue`). NetDaemon app management was removed from HACS at some point and never came back. | `appdaemon/apps/<name>` |

Anything scoped as "take over Dashboards and Templates the way HACS does
them" is scoping against a feature that does not exist. The real surface
to reason about is: integrations, themes, one narrow Jinja-macro category,
Lovelace frontend-resource JS, and AppDaemon apps.

## 2. How HACS actually installs and updates content

Traced end to end in `repositories/base.py`, class `HacsRepository`:

- Metadata (release list, git tree, `hacs.json`/`manifest.json` content) is
  fetched over the GitHub REST API using an owner-supplied OAuth token
  obtained through GitHub's device flow against a hardcoded public OAuth
  App client ID (`config_flow.py`). The token is written into HA's own
  `.storage/core.config_entries` in plaintext, exactly where every other
  config entry's credentials already live - this part is not a HACS-specific
  weakness, it is how every Home Assistant integration stores a secret
  today (HA SOC's own SEC-1 work built a private, non-`.storage`-shared
  store specifically because this default is weak; HACS predates and does
  not use that pattern, but neither does most of the ecosystem).
- Content is written to disk one of three ways: a whole-repo zip download
  and `zipfile.ZipFile(...).extractall(...)`, a specific release-asset zip
  and `extractall(...)`, or a per-file download that writes each file to a
  path built directly from the GitHub tree entry's own path string.
- I read both write paths directly rather than taking a summary at face
  value. Neither one rejects a `../` path segment, an absolute path, or a
  symlink before writing:
  - `download_repository_zip` (`base.py:652-699`) rewrites each zip
    member's filename only by stripping the top-level directory GitHub's
    archive adds and the configured remote-content prefix, then calls
    `zip_file.extractall(self.content.path.local, extractable)` with no
    further check.
  - `dowload_repository_content` (`base.py:1249-1277`) builds
    `local_directory` from the tree entry's `full_path` with a substring
    `.replace()` call, then does
    `pathlib.Path(local_directory).mkdir(parents=True, exist_ok=True)`
    and writes the file, again with no `..`-rejection.
  - This is a narrow, not a wide-open, gap: the paths come from what
    GitHub's own API reports for a repository the operator explicitly
    chose to add, so the realistic attacker is a malicious or compromised
    repository owner, not a passive network attacker. But it is a real,
    unmitigated gap, of the same shape as classic zip-slip advisories
    found in many other tools, and it exists with zero defense-in-depth
    in a codebase that already has an `is_safe()` path helper - just one
    that is only ever used to protect *removal*, never installation
    (`utils/path.py`).
- Beyond structural checks (does `manifest.json`/`hacs.json` parse against
  a schema, does the expected directory exist in the tree), **there is no
  checksum verification, no signature verification, and no code-content
  scanning anywhere in the install path.** Content is trusted exactly as
  much as the GitHub API response is trusted.

## 3. The trust model: only the curated list gets any review, and that review never runs on the user's own instance

This is the actual shape of "the intrinsic security issue," stated
precisely rather than as a vibe:

- HACS ships a full compliance-check suite (`validate/*.py`: license
  presence, issues enabled, brand assets, README images, non-archived,
  schema completeness). It gates entry into the **curated default list**
  only.
- That suite is wired behind `if not self.hacs.system.action: return`
  (`validate/manager.py:59-60`), and `system.action` is only ever set
  `True` inside the standalone `hacs/action` CI tool that repository
  maintainers run against pull requests to the separate `hacs/default`
  repository. **This validator never executes inside a running Home
  Assistant instance.** An end user's HACS install performs none of it,
  for anything.
- When a user adds a **custom repository** (the "add any GitHub URL"
  workflow, the one an attacker-recommended or typosquatted repo would
  actually go through), the only checks that run are structural: does the
  expected directory exist, does the manifest parse, is it not
  `home-assistant/core` or an add-ons repo. No license check, no
  "has issues enabled" check, no content review of any kind applies to a
  custom repository, ever.
- The default-list data itself (which repos are "vetted," their
  description/stars/domain) is fetched from a separate CDN,
  `data-v2.hacs.xyz`, generated by infrastructure entirely outside this
  repository. There is also a reactive, after-the-fact "removed
  repository" blocklist pulled from the same CDN for repos HACS
  maintainers later flag as malicious or archived - useful, but it is a
  cleanup mechanism, not a gate.
- At update time, the only human-reviewable material is the GitHub
  release's own free-text body, concatenated across every release between
  installed and latest (`update.py:93-135`). There is no file diff, no
  changed-file list, and no code-level review surface anywhere in the
  update flow. A repository with no tagged releases (branch-tracking
  install) shows no release notes at all.
- Two categories auto-activate with **zero confirmation step**: theme and
  template installs immediately call
  `frontend.reload_themes`/`homeassistant.reload_custom_templates`, and a
  plugin install automatically creates or updates a **Lovelace resource
  entry** pointing at the newly-downloaded JS
  (`repositories/plugin.py:193-221`) - meaning a compromised "plugin"
  repository gets its JavaScript wired directly into the admin's dashboard
  the moment install finishes, with no restart and no separate approval
  gate. Integration installs are the one category with real friction: a
  config-flow integration hot-loads without restart, but anything else
  (a non-config-flow integration, or *any* update to an already-installed
  integration) sets `pending_restart = True` and opens a nagging repair
  issue - friction, not a review gate.
- HACS documents none of this as risk. A full-repo `grep -rin "security"`
  found no matches in any product code or doc in this checkout; there is
  no `SECURITY.md`. There is no current published GHSA advisory against
  `hacs/integration`. There is a 2021 Home-Assistant-coordinated
  disclosure describing a directory-traversal flaw reachable through an
  unauthenticated webview in HACS at the time, since resolved; it is
  historical evidence that this class of bug has happened in this project
  before, not evidence of an open vulnerability today.

None of this is a HACS-specific moral failing. It is the predictable shape
of "let an end user point a package manager at any GitHub repository and
auto-install what it finds," which is close to what `pip install` from an
arbitrary index, or a browser extension store with no review queue, looks
like structurally. The severity comes from where it lands: Home Assistant
integrations run in-process with the same privilege as HA core itself, no
sandbox, exactly the point HA SOC's own Integration Security tab already
states about *every* integration regardless of source.

## 4. What taking this over would actually require

Not "write a downloader." A functionally equivalent replacement needs, at
minimum:

- A GitHub OAuth App registration (own client ID) and a device-flow (or
  PAT) auth implementation, plus REST client code for repos, releases, git
  trees, and content, with the same rate-limit-aware disable/re-enable
  behavior HACS already has to avoid burning the owner's quota.
- Category-aware download/extraction logic for at least integration,
  theme, template, plugin, and appdaemon (five of HACS's six categories
  are in the user's four named areas already), each with its own
  remote-path convention, local-install-path convention, and
  post-install activation call (reload, restart repair issue, or Lovelace
  resource registration).
- A curated, reviewed default catalog, or an explicit decision to skip
  curation entirely and only support "arbitrary custom repo" - which
  removes the one piece of the ecosystem that currently gets any human
  review at all, making the replacement categorically less vetted than
  what exists today unless HA SOC also stands up its own review pipeline
  and hosting for it (HACS's curation runs external CI against a separate
  `hacs/default` repository - infrastructure this project does not have
  and a new commitment to maintain indefinitely).
- A management UI: search/browse, install/update dialogs, a release-notes
  viewer, per-repository state. HACS's own backend (everything measured
  in section 6 below) does not include this - it lives in a completely
  separate frontend package (`hacs/frontend`), not part of the 7.7K-line
  figure at all.
- An update entity or equivalent per installed item, wired into HA's
  `update.*` platform the same way, if the intent is to keep the same
  user experience (dashboard update notifications, `update.install`
  service compatibility with existing automations).
- Migration handling for every existing HACS user: their installed
  integrations/themes/plugins currently carry HACS-specific installed
  state (`installed_commit`, `installed_version`) that a replacement would
  need to read and take ownership of, or every existing install becomes
  untracked the day HA SOC "takes over."
- A very concrete bootstrap problem: **HA SOC itself is currently
  distributed through HACS** (README's Installation section documents
  the HACS custom-repository path as the primary install route). A tool
  cannot be the thing that installs itself before it exists on the
  system; some other install path (manual copy, or continuing to rely on
  HACS/HA's built-in "Custom repository") has to remain the bootstrap
  method regardless of what this project decides here.

### Size, for calibration

`custom_components/hacs/` is 59 Python files, roughly 7,700 lines,
plus 11 JSON/PNG/JS asset files. That is the **backend only** - it excludes
the separate frontend SPA, the separate curated-catalog repository and its
CI, and the separate CI action package. For comparison, HA SOC's entire
existing backend across all 30 modules (audit, permissions, risk scoring,
detections, scanner, firewall, integration security, and everything else
built across sprints 0-4 this year) is in a similar order of magnitude.
Taking over HACS's role is not an incremental feature; it is comparable in
raw scope to everything HA SOC has built so far, for a domain (arbitrary
code ingestion and execution) this project has so far deliberately stayed
out of.

## 5. Why a full takeover does not actually solve the stated problem

The "intrinsic security issue" is that Home Assistant integrations, theme
files that can carry Jinja, custom Lovelace JS, and AppDaemon apps all run
with full in-process privilege and no sandbox, combined with a discovery
and install mechanism that lets an end user point at any GitHub repository
with only structural (not content) validation. Moving the download and
extraction code from one custom integration (HACS) to another custom
integration (HA SOC) changes who wrote the code that writes the files. It
does not change:

- That Home Assistant has no sandbox for third-party code - that is a
  Home Assistant Core limitation, not a HACS one, and no custom
  integration (including HA SOC) can fix it from outside core.
- That "arbitrary GitHub repo, chosen by the owner" is still the actual
  supply-chain trust boundary. Unless HA SOC also builds and maintains a
  reviewed catalog (a real, ongoing commitment, not a one-time feature),
  a HA-SOC-run installer for a `custom_repo`-equivalent workflow has
  exactly the same trust boundary HACS has today.
- That a **newly written** zip/tarball extraction and per-file download
  engine is, if anything, *more* likely to contain the exact zip-slip
  class of gap identified in section 2 than to avoid it - HACS is a
  mature, widely deployed project (tens of thousands of installs) that
  still has this gap unaddressed after years of development. HA SOC
  writing its own version from scratch does not start from a safer
  position; it starts from zero production hardening on a brand new
  code path with real write access to the config directory.

Put simply: this would trade "an existing, widely used tool with a known,
narrow, documented gap" for "a new, unproven code path doing the same
risky thing, now maintained by this project indefinitely, with the same
underlying trust boundary." That is a worse risk profile during the
transition, and it does not reach parity with the honesty standard this
project has held itself to everywhere else (integration_security.py's
entire premise is "we measure provenance, we never claim safety, we never
increase our own privilege beyond what's needed" - taking over live code
deployment onto the user's system is a direct reversal of that stance,
requiring exactly the write-scope credentials and file-system trust this
project has so far avoided needing anywhere).

## 6. Options

| | What it is | New privilege HA SOC would need | Effort | Actually closes the stated gap? |
|---|---|---|---|---|
| **A. Full takeover** | Replace HACS: own download/extraction engine, own curated catalog + CI, own management UI, own update entities | Write access to `custom_components/`, `themes/`, `www/`, `appdaemon/apps/`; a GitHub OAuth App; ongoing catalog curation | Very high - comparable to HA SOC's entire existing backend, plus a frontend SPA and standing catalog infrastructure this project does not have today | No - inherits the same trust boundary, adds a new immature code path in the one place (file writes from network content) HACS already has a known gap |
| **B. Diff-on-update surfacing** | Before a HACS update is applied, fetch the changed-file list/diff between installed and candidate commit via the GitHub API and show it in HA SOC (something HACS itself does not do at all today - only release-note prose exists) | None beyond what `github_provenance.py` already has: read-only GitHub API calls with the existing owner-scoped token | Low-medium - reuses the existing rate-limit-aware, slug-validated GitHub client wholesale | Meaningfully raises the bar on the one blind spot (invisible code changes on update) without taking on any write-path risk |
| **C. Pre-add/pre-install scan gate** | Owner pastes a candidate `owner/repo` into HA SOC before adding it to HACS (or before approving an update); HA SOC fetches the file listing/content read-only via GitHub's API and runs the existing AST scanner (`scanner.py`'s rules: TLS-verification-disabled, shell-injection risk, eval/exec use, insecure deserialization, hardcoded credentials, sensitive-data logging, and the foreign-data-access rules) against it, reporting findings before the owner clicks install in HACS's own UI | None beyond existing read-only GitHub access; no file-system writes into `custom_components/` etc. at all | Low-medium - reuses 100% of existing scanner and GitHub-client infrastructure; the only new work is fetching remote file content instead of scanning local disk | Directly answers "is this new thing risky before I let HACS install it," using the project's own existing detection rules, with zero new write privilege |
| **D. Status quo** | Keep `integration_security.py` exactly as it is: observe HACS's tier/origin data after the fact | None | None | No change; the current tab already reports tier and flags a custom-repo origin, it just does so after install, not before |

## 7. Recommendation

Do not pursue full takeover (A). It is the largest possible scope
increase this project has taken on, requires HA SOC to hold exactly the
write-scope credentials and file-system trust its own design philosophy
has avoided everywhere else, does not remove the actual trust boundary
(arbitrary GitHub repository, chosen by the owner) that causes the
concern, and very plausibly introduces a *less* hardened version of the
one concrete gap identified (zip-slip-class path handling) than the
mature tool it would replace.

Pursue C first: a pre-install/pre-update **scan gate** that reuses the
existing scanner and GitHub-provenance infrastructure wholesale, adds no
new write privilege, and gives the owner a real answer - specific rule
findings, not a vibe - before HACS ever touches disk. Layer B on top once
C exists: the same read-only GitHub access already fetches commits/trees,
so a changed-file diff for a pending update is a natural extension, and it
closes HACS's most concrete honesty gap (an update's real content change
is currently invisible; only release-note prose is shown).

If the owner still wants to discuss A after this, the concrete
prerequisite work is section 4's list; it should be scoped as its own
multi-sprint initiative with an explicit decision to accept an interim
period during which the new download/extraction path is *less* battle
tested than the tool it replaces, not folded into an existing sprint.

## 8. Open questions, for discussion (nothing here is decided)

- If C is pursued: does the owner want scan-before-add to be a hard gate
  (HACS install blocked until scanned) or an advisory step (scan runs,
  reports, owner still clicks install in HACS regardless)? A hard gate
  needs a way to intercept HACS's own `hacs/repositories/add` websocket
  call, which HACS does not expose a hook for today - the realistic
  version is advisory: HA SOC surfaces "scan this before you add it" as
  its own explicit action the owner takes first, not an interception of
  HACS's own flow.
- If B is pursued: should the diff be a raw unified diff, or a
  higher-level "files added/removed/changed" list plus a re-run of the
  scanner against only the changed files? The latter reuses the scanner
  a second time for a genuinely new purpose (delta scanning) rather than
  just displaying GitHub's diff API output verbatim.
- Should either C or B extend beyond `integration` category content to
  `plugin` (frontend JS) as well, given section 3's finding that a plugin
  install auto-registers as a live Lovelace resource with zero
  confirmation step - arguably the single highest-consequence gap
  identified, since it puts arbitrary JS in the admin's own dashboard
  context automatically. Scanning JS content for the equivalent of
  `scanner.py`'s rules is a different job than scanning Python AST and
  would need its own rule set, not a reuse of the existing one.
- Is there owner appetite for filing any of section 2/3's findings
  (specifically the missing zip-slip hardening) as a private GitHub
  security advisory against `hacs/integration` itself, given no current
  advisory covers it? That is independent of anything HA SOC does, and
  arguably the highest-leverage, lowest-effort action available: it fixes
  the gap for every HACS user, not just this instance.
