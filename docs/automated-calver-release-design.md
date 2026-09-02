# Automated CalVer releases through protected branches

This design removes version-bump memory from developers and coding agents
without weakening protected-branch controls or making release artifacts diverge
from their tagged source.

## Outcome and invariant

Release-bearing changes follow this state machine:

```text
implementation merge
  -> existing release workflow validates main
  -> release-preparation workflow detects changes after the latest tag
  -> bot updates every version field in one pull request
  -> required checks pass and auto-merge completes
  -> existing release workflow tags, builds, attests, and publishes
```

The governing invariant is:

```text
tag version == source versions == package metadata == archive version
```

Do not calculate a version only inside an archive and do not let a publishing
job bypass the protected default branch. Both approaches destroy the useful
relationship between reviewed source, tag, and distributed bytes.

## Repository implementation

HA SOC uses `YYYY.MM.DD.N`, calculated in `America/Chicago`:

- `scripts/set_version.py` selects one greater than the highest tag sequence
  for the current local date and updates every shipped version field.
- `.github/workflows/prepare-release.yml` runs after a successful `Release`
  workflow on `main` and creates or refreshes `automation/calver-release`.
- `.github/workflows/release.yml` remains the only publisher.

Waiting for the existing Release workflow has two benefits: merged code is
validated before a version PR is proposed, and multiple rapid merges can be
coalesced. The preparation workflow also runs after publication; it then sees
that the latest tag contains all release-bearing paths and exits without
creating another PR.

The workflow has two explicit no-op states:

1. Current source version is ahead of the latest published release. A release
   is pending or failed, so another version must not be allocated.
2. No release-bearing path differs from the latest release tag.

The controlled branch is updated with `--force-with-lease`, never an
unconditional force push. This permits a later merge to refresh an existing
automation PR while refusing to overwrite an unexpected third-party update.

## One-time GitHub App configuration

GitHub suppresses or approval-gates workflow events created with the normal
`GITHUB_TOKEN`. Zero-touch protected-branch automation therefore uses a
short-lived GitHub App installation token.

Create a GitHub App dedicated to release preparation:

1. Disable webhooks unless they are needed elsewhere.
2. Grant repository **Contents: Read and write**.
3. Grant repository **Pull requests: Read and write**.
4. Install the App only in the repositories that use this design.
5. Add repository variable `RELEASE_AUTOMATION_CLIENT_ID` with the App client ID.
6. Add Actions secret `RELEASE_AUTOMATION_PRIVATE_KEY` with the App private key.

The workflow-level `GITHUB_TOKEN` remains read-only. The App token is created
only after the workflow proves a release PR is necessary, expires
automatically, and is scoped to the installed repository.

Auto-merge must be enabled for the repository. Branch protection may require
tests, security scans, signed commits, or other checks; the automation should
not be placed on a bypass list. If approving reviews are required, retain the
human approval rather than teaching the bot to approve its own change.

## Adapting the design to another repository

Parameterize these repository-specific elements:

| Element | HA SOC value | Adaptation point |
| --- | --- | --- |
| Calendar timezone | `America/Chicago` | Choose and document one IANA zone |
| Version format | `YYYY.MM.DD.N` | Replace parser and next-version function together |
| Release-bearing paths | `custom_components/ha_soc`, `ha_soc_probe` | Include only shipped product inputs |
| Version fields | Three HA SOC/Probe files | Centralize writes in one tested script |
| Publisher workflow | `Release` | Keep one authoritative tag/asset publisher |
| Automation branch | `automation/calver-release` | Reserve one bot-controlled branch |
| Merge method | Squash | Match repository history policy |

The version script should have pure functions for parsing and selecting the
next version, plus fixture-based tests proving every shipped identifier is
updated. Keep a separate release-time validator so a defect in the writer
cannot validate itself.

For SemVer repositories, the same orchestration applies but the selection
function should derive major/minor/patch intent from an explicit label,
conventional commits, or a maintained release manifest. Do not infer breaking
changes from arbitrary source diffs.

## Concurrency and recovery

- Serialize preparation runs per repository and do not cancel an in-progress
  run. A stable branch coalesces rapid implementation merges.
- If credentials are missing, fail before changing a branch and provide the
  configuration names in the error.
- If version-PR checks fail, fix the underlying defect; do not bypass them.
- If publication fails after the version PR merges, rerun or repair the
  publisher. Because source is ahead of the latest release, preparation will
  not allocate another version.
- If a draft release exists, the publisher may safely resume it. A published
  immutable release must never have its assets replaced.
- If an unexpected actor changes the controlled branch, `--force-with-lease`
  fails and requires investigation.

## Security boundaries

- Pin every action to an immutable commit SHA.
- Keep the event token read-only and minimize GitHub App permissions.
- Never execute pull-request code with a write token through
  `pull_request_target`.
- Never expose the App private key or generated token in logs or artifacts.
- Keep artifact building, SBOM generation, checksums, attestations, and final
  publication behind the same tests that protect ordinary merges.
- Treat CI success as repository qualification, not proof of a live deployment
  or successful HACS update on a specific Home Assistant instance.
