#!/usr/bin/env bash
# Purpose: Cut a release — stamp CHANGELOG [Unreleased] with a version
#          and date, write VERSION, then print the commit + tag commands.
#          Does NOT execute git commit or git tag automatically — the
#          operator reviews the diff and runs the printed commands.
# Unit:    n/a (workstation-only release helper)
# Phase:   all (introduced v1.3.0-phase13)
#
# Usage:
#   ./scripts/release.sh v1.3.0-phase13
#
# What it does:
#   1. Validates: one semver arg, git working tree clean (no staged/unstaged changes).
#   2. Rewrites CHANGELOG.md: [Unreleased] → [<version>] — <YYYY-MM-DD>.
#      Opens a fresh [Unreleased] header above it.
#   3. Writes VERSION.
#   4. Prints the git commands to commit + tag; you run them.
#
# Why not auto-commit/tag: release commits and annotated tags should be
# operator-reviewed. This script makes the mechanical changes and shows
# you exactly what to run — no surprise git history.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()  { printf '[rpi-hub-release] %s\n' "$*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

# ── arg validation ─────────────────────────────────────────────────────────────

[[ $# -eq 1 ]] || die "Usage: $0 <version>  (e.g. v1.3.0-phase13)"
VERSION="$1"
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9] ]] \
    || die "Version must start with v<major>.<minor>.<patch> (got: $VERSION)"

TODAY="$(date +%Y-%m-%d)"

# ── git cleanliness check ──────────────────────────────────────────────────────

if ! git -C "${REPO_DIR}" diff --quiet HEAD 2>/dev/null; then
    die "Working tree has uncommitted changes. Commit or stash them first."
fi
if ! git -C "${REPO_DIR}" diff --cached --quiet 2>/dev/null; then
    die "Staged changes detected. Commit them first."
fi

log "Releasing ${VERSION} on ${TODAY}"

# ── CHANGELOG.md: promote [Unreleased] → [version] ───────────────────────────

CHANGELOG="${REPO_DIR}/CHANGELOG.md"
[[ -f "$CHANGELOG" ]] || die "CHANGELOG.md not found at ${CHANGELOG}"

# Check that [Unreleased] header exists and is not already this version.
grep -q '^\#\# \[Unreleased\]' "${CHANGELOG}" \
    || die "CHANGELOG.md has no '## [Unreleased]' section; nothing to release."
grep -q "^\#\# \[${VERSION}\]" "${CHANGELOG}" \
    && die "${VERSION} is already present in CHANGELOG.md."

# Insert a fresh [Unreleased] above the current one, then rename the current
# [Unreleased] → [version] — date.
python3 - "${CHANGELOG}" "${VERSION}" "${TODAY}" <<'EOF'
import sys, re

path, version, today = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()

# Replace the first occurrence of '## [Unreleased]' with both the new
# empty Unreleased header and the stamped version header.
stamped = f"## [Unreleased]\n\n## [{version}] — {today}"
text, n = re.subn(r'^## \[Unreleased\]', stamped, text, count=1, flags=re.MULTILINE)
if n != 1:
    print(f"ERROR: Could not find '## [Unreleased]' in {path}", file=sys.stderr)
    sys.exit(1)
open(path, 'w').write(text)
print(f"CHANGELOG.md: [Unreleased] → [{version}] — {today}")
EOF

# ── VERSION ───────────────────────────────────────────────────────────────────

printf '%s\n' "${VERSION}" > "${REPO_DIR}/VERSION"
log "VERSION written: ${VERSION}"

# ── summary + operator commands ───────────────────────────────────────────────

log ""
log "Files changed:"
log "  CHANGELOG.md  (Unreleased → ${VERSION})"
log "  VERSION       (→ ${VERSION})"
log ""
log "Review the diff, then run:"
log ""
log "  git add CHANGELOG.md VERSION"
log "  git commit -m \"chore(release): ${VERSION}\""
log "  git tag -a ${VERSION} -m \"Release ${VERSION}\""
log ""
log "To push (after review):"
log "  git push && git push origin ${VERSION}"
log ""
log "Done. Nothing was committed or tagged — review first."
