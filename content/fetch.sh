#!/usr/bin/env bash
# Purpose: Download the ZIM payload listed in content/manifest.yaml.
# Unit:    n/a (workstation-only; this never runs on the Pi)
# Phase:   3
#
# Why a workstation: Wikipedia (no-images) alone is ~50 GB. The Pi's
# storage and its disconnected runtime are not the right place to fetch.
# Transfer the resulting directory to the Pi via rsync, USB stick, or
# pre-imaging the SD card.
#
# Usage:
#   ./content/fetch.sh                 # tier=core, dest=<repo>/payload/var/lib/kiwix
#   ./content/fetch.sh minimal         # smaller subset for Pi Zero builds
#   DEST=/mnt/sd/var/lib/kiwix ./content/fetch.sh full
#
# Dependencies: yq (Go version), curl, sha256sum.

set -euo pipefail

TIER="${1:-core}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${DEST:-$REPO_DIR/payload/var/lib/kiwix}"
MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifest.yaml"

log() { printf '[fetch] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

require() {
    command -v "$1" >/dev/null || die "$1 is required ($2)"
}

require yq      "install: brew install yq | apt-get install yq | go install github.com/mikefarah/yq/v4@latest"
require curl    "install: apt-get install curl | brew install curl"
require sha256sum "install: coreutils"

[[ -f "$MANIFEST" ]] || die "manifest not found at $MANIFEST"
[[ "$TIER" =~ ^(minimal|core|full)$ ]] || die "tier must be minimal|core|full (got: $TIER)"

mkdir -p "$DEST"
log "tier=$TIER  dest=$DEST"

# tier filter — fetch entries whose tier is at or below the requested tier.
tier_includes() {
    local entry="$1"
    case "$TIER" in
        full)
            return 0
            ;;
        core)
            [[ "$entry" != "full" ]]
            ;;
        minimal)
            [[ "$entry" == "minimal" ]]
            ;;
    esac
}

count=$(yq '.zims | length' "$MANIFEST")
[[ "$count" =~ ^[0-9]+$ ]] || die "manifest parse failed; is yq the Go version (mikefarah)?"

fetched=0
skipped=0
hashed=0

for i in $(seq 0 $((count - 1))); do
    name=$(yq -r ".zims[$i].name" "$MANIFEST")
    url=$(yq -r ".zims[$i].url" "$MANIFEST")
    expected=$(yq -r ".zims[$i].sha256" "$MANIFEST")
    entry_tier=$(yq -r ".zims[$i].tier" "$MANIFEST")

    if ! tier_includes "$entry_tier"; then
        log "skip   $name (tier=$entry_tier, requested=$TIER)"
        skipped=$((skipped + 1))
        continue
    fi

    out="$DEST/$name"

    # If the file is already present and matches the pinned hash, do nothing.
    if [[ -f "$out" && -n "$expected" && "$expected" != "null" ]]; then
        actual=$(sha256sum "$out" | cut -d' ' -f1)
        if [[ "$actual" == "$expected" ]]; then
            log "cached $name"
            continue
        fi
        log "stale  $name (hash mismatch; refetching)"
        rm -f "$out"
    fi

    log "get    $name"
    log "       $url"
    # -C - resumes from $out.partial's current size if the previous run died
    # mid-stream. --retry-all-errors makes --retry catch "connection reset by
    # peer" (curl 56) too, not just connect-time failures. Together they keep
    # an 8 GB Wiktionary download robust to flaky links.
    curl --fail --location --retry 5 --retry-delay 5 --retry-all-errors \
        -C - --progress-bar -o "$out.partial" "$url"

    actual=$(sha256sum "$out.partial" | cut -d' ' -f1)
    if [[ -n "$expected" && "$expected" != "null" ]]; then
        if [[ "$actual" != "$expected" ]]; then
            rm -f "$out.partial"
            die "sha256 mismatch on $name (got $actual, expected $expected)"
        fi
        mv "$out.partial" "$out"
        log "ok     $name"
        fetched=$((fetched + 1))
    else
        mv "$out.partial" "$out"
        log "ok     $name  sha256=$actual"
        log "       (paste into manifest.yaml to lock reproducibility)"
        fetched=$((fetched + 1))
        hashed=$((hashed + 1))
    fi
done

log ""
log "done. fetched=$fetched skipped=$skipped unverified=$hashed"
log ""
log "Transfer to the Pi:"
log "  rsync -avh --progress $DEST/ pi@hub.local:/var/lib/kiwix/"
log "or copy onto the SD card before flashing."
