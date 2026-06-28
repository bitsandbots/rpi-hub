#!/usr/bin/env bash
# Purpose: Re-hash ZIM files on disk and compare against manifest.yaml.
# Unit:    n/a (run on demand — workstation or Pi)
# Phase:   3
#
# Use cases:
#   - Did the rsync / SD-card copy corrupt anything?
#   - Is the disk's contents what the manifest says it should be?
#
# Usage:
#   ./content/verify.sh                       # verifies /var/lib/kiwix
#   ./content/verify.sh ./payload/var/lib/kiwix
#
# Exit codes:
#   0 — all hashes matched (or matched + missing files but no mismatches)
#   1 — at least one file's hash did not match the manifest
#   2 — verification incomplete (one or more manifest entries had no sha256)

set -euo pipefail

DEST="${1:-/var/lib/kiwix}"
MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifest.yaml"

log() { printf '[verify] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 2; }

command -v yq >/dev/null         || die "yq required (Go version, mikefarah)"
command -v sha256sum >/dev/null  || die "sha256sum required"
[[ -f "$MANIFEST" ]]             || die "manifest not found at $MANIFEST"
[[ -d "$DEST" ]]                 || die "dest dir not found: $DEST"

count=$(yq '.zims | length' "$MANIFEST")

mismatch=0
unhashed=0
missing=0
ok=0

for i in $(seq 0 $((count - 1))); do
    name=$(yq -r ".zims[$i].name" "$MANIFEST")
    expected=$(yq -r ".zims[$i].sha256" "$MANIFEST")
    file="$DEST/$name"

    if [[ ! -f "$file" ]]; then
        printf 'MISSING   %s\n' "$name"
        missing=$((missing + 1))
        continue
    fi

    if [[ -z "$expected" || "$expected" == "null" ]]; then
        printf 'NO-HASH   %s (manifest has no sha256; cannot verify)\n' "$name"
        unhashed=$((unhashed + 1))
        continue
    fi

    actual=$(sha256sum "$file" | cut -d' ' -f1)
    if [[ "$actual" == "$expected" ]]; then
        printf 'OK        %s\n' "$name"
        ok=$((ok + 1))
    else
        printf 'MISMATCH  %s\n  expected %s\n  got      %s\n' "$name" "$expected" "$actual"
        mismatch=$((mismatch + 1))
    fi
done

printf '\nsummary: ok=%d mismatch=%d unhashed=%d missing=%d\n' \
    "$ok" "$mismatch" "$unhashed" "$missing"

if [[ $mismatch -gt 0 ]]; then
    exit 1
fi
if [[ $unhashed -gt 0 ]]; then
    exit 2
fi
exit 0
