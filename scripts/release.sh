#!/usr/bin/env bash
# Prepare and auto-merge a lockstep HA SOC release pull request; the merge to main triggers release.yml.
# Usage: scripts/release.sh [vYYYY.MM.DD.N] [--skip-tests]; see docs/operations.md.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ -n "$(git status --porcelain)" ]; then
    echo "The working tree must be clean before preparing a release." >&2
    exit 2
fi

SKIP_TESTS=0
VERSION=""
for arg in "$@"; do
    case "$arg" in
        --skip-tests) SKIP_TESTS=1 ;;
        -*) echo "Unknown option: $arg" >&2; exit 2 ;;
        *) VERSION="$arg" ;;
    esac
done

if [ -z "${VERSION}" ]; then
    today="$(date +%Y.%m.%d)"
    # Highest same-day revision across tags AND the manifest, so a bumped-but-untagged manifest never versions backwards.
    manifest_ver="$(python3 -c "import json;print(json.load(open('custom_components/ha_soc/manifest.json'))['version'])")"
    manifest_rev=""
    case "${manifest_ver}" in
        "${today}."*) manifest_rev="${manifest_ver##*.}" ;;
    esac
    highest="$( { git tag -l "${today}.*" "v${today}.*" \
                    | sed -E "s/^v//; s/^${today}\.//"; echo "${manifest_rev}"; } \
        | grep -E '^[0-9]+$' | sort -n | tail -1 || true)"
    next=$(( ${highest:-0} + 1 ))
    VERSION="${today}.${next}"
fi

# Internal work uses the bare number; the v prefix is re-added exactly once, on the tag.
VERSION="${VERSION#v}"

if ! echo "${VERSION}" | grep -qE '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$'; then
    echo "Version '${VERSION}' is not vYYYY.MM.DD.N (or bare YYYY.MM.DD.N)" >&2
    exit 2
fi

if git rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null \
    || git rev-parse -q --verify "refs/tags/v${VERSION}" >/dev/null; then
    echo "Tag ${VERSION} (or v${VERSION}) already exists - pick a higher revision." >&2
    exit 2
fi

echo "Releasing version: v${VERSION}"

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "${branch}" = "main" ]; then
    branch="release/v${VERSION}"
    git switch -c "${branch}"
fi

python3 - "$VERSION" <<'PY'
import re, sys, pathlib

version = sys.argv[1]

edits = [
    # (path, regex, replacement)
    ("custom_components/ha_soc/manifest.json",
     r'("version"\s*:\s*")[^"]*(")', rf'\g<1>{version}\g<2>'),
    ("ha_soc_probe/config.yaml",
     r'(^version:\s*")[^"]*(")', rf'\g<1>{version}\g<2>'),
    ("ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run",
     r'(SCANNER_VERSION=")[^"]*(")', rf'\g<1>{version}\g<2>'),
]

for path, pattern, repl in edits:
    p = pathlib.Path(path)
    text = p.read_text()
    new, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if n != 1:
        sys.exit(f"Could not update version in {path} (matched {n} times)")
    p.write_text(new)
    print(f"  updated {path}")
PY

if [ "${SKIP_TESTS}" -eq 0 ]; then
    if [ -x ".venv/bin/pytest" ]; then
        echo "Running backend tests…"
        .venv/bin/pytest tests/ -q
    else
        echo "note: .venv/bin/pytest not found — skipping tests (CI still validates)."
    fi
fi
python3 -m py_compile custom_components/ha_soc/*.py

git add custom_components/ha_soc/manifest.json ha_soc_probe/config.yaml \
    ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run
git commit -m "Release ${VERSION}"
echo "Pushing release branch ${branch}…"
git push --set-upstream origin "${branch}"

if ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
    echo "gh is not authenticated; open a pull request for ${branch}." >&2
    exit 1
fi

pr_url="$(gh pr create \
    --base main \
    --head "${branch}" \
    --title "Release v${VERSION}" \
    --body "Automated lockstep version update for v${VERSION}. Required checks must pass before merge and publication.")"
gh pr merge "${pr_url}" --auto --squash --delete-branch

cat <<EOF

Done. ${pr_url} will merge after required checks pass. The main-branch Release
workflow then publishes v${VERSION}; no manual tag or Release creation is needed.

FIRST TIME ONLY (clears the stale 'domain: None' HACS cache):
  In Home Assistant → HACS → HA SOC → three-dot menu → Remove, then
  re-add the custom repository. After that, new releases appear normally.

If the repo is private, HACS must be authenticated with a GitHub account
that can read it.
EOF
