#!/usr/bin/env bash
# ==============================================================================
# Cut a consistent HA SOC release.
#
# The bug this exists to prevent: releasing by hand let the integration
# manifest version, the add-on version, and the git tags drift apart — and
# HACS installs from a *tag/Release* whose tree must match, so a mismatch
# shows up as "wrong version" or the dreaded
# "custom_components/None/manifest.json" (an unresolved domain).
#
# This script bumps EVERY version in lockstep, commits, tags with a name
# that exactly equals the manifest version (no "v" prefix, so CI's
# tag==manifest check is trivial), and pushes. Pushing the tag triggers
# .github/workflows/release.yml, which creates the GitHub Release HACS
# installs from.
#
# Usage:
#   scripts/release.sh                # auto: YYYY.MM.DD.N (today, next N)
#   scripts/release.sh 2026.08.24.1   # explicit version
#   scripts/release.sh --skip-tests   # skip the pytest gate (not advised)
#
# Calendar scheme: YYYY.MM.DD.V — the date plus a same-day revision counter
# starting at 1.
# ==============================================================================
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

SKIP_TESTS=0
VERSION=""
for arg in "$@"; do
    case "$arg" in
        --skip-tests) SKIP_TESTS=1 ;;
        -*) echo "Unknown option: $arg" >&2; exit 2 ;;
        *) VERSION="$arg" ;;
    esac
done

# --- Determine the new version -----------------------------------------------
if [ -z "${VERSION}" ]; then
    today="$(date +%Y.%m.%d)"
    # Highest existing same-day revision across tags (with or without a
    # leading v), default 0, then +1.
    highest="$(git tag -l "${today}.*" "v${today}.*" \
        | sed -E "s/^v//; s/^${today}\.//" \
        | grep -E '^[0-9]+$' | sort -n | tail -1 || true)"
    next=$(( ${highest:-0} + 1 ))
    VERSION="${today}.${next}"
fi

if ! echo "${VERSION}" | grep -qE '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$'; then
    echo "Version '${VERSION}' is not YYYY.MM.DD.N" >&2
    exit 2
fi

if git rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null; then
    echo "Tag ${VERSION} already exists — pick a higher revision." >&2
    exit 2
fi

echo "Releasing version: ${VERSION}"

# --- Bump every version in lockstep ------------------------------------------
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

# --- Validate before tagging (a red release is worse than a slow one) --------
if [ "${SKIP_TESTS}" -eq 0 ]; then
    if [ -x ".venv/bin/pytest" ]; then
        echo "Running backend tests…"
        .venv/bin/pytest tests/ -q
    else
        echo "note: .venv/bin/pytest not found — skipping tests (CI still validates)."
    fi
fi
python3 -m py_compile custom_components/ha_soc/*.py

# --- Commit, tag, push -------------------------------------------------------
branch="$(git rev-parse --abbrev-ref HEAD)"
git add custom_components/ha_soc/manifest.json ha_soc_probe/config.yaml \
    ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run
git commit -m "Release ${VERSION}"
git tag -a "${VERSION}" -m "HA SOC ${VERSION}"

echo "Pushing branch ${branch} and tag ${VERSION}…"
git push origin "${branch}"
git push origin "${VERSION}"

cat <<EOF

Done. Tag ${VERSION} pushed — the Release workflow will create the GitHub
Release HACS installs from.

FIRST TIME ONLY (clears the stale 'domain: None' HACS cache):
  In Home Assistant → HACS → HA SOC → three-dot menu → Remove, then
  re-add the custom repository. After that, new releases appear normally.

If the repo is private, HACS must be authenticated with a GitHub account
that can read it.
EOF
