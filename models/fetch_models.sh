#!/usr/bin/env bash
# Purpose: Download the model weights rpi-hub-assist needs onto a workstation.
# Unit:    n/a (workstation-only; never runs on the Pi)
# Phase:   6
#
# We never bundle weights in the repo (size + license clarity). This script
# downloads two files into ./payload/var/lib/rpi-hub/models/ with sha256
# verification, then prints the rsync command to push them to the Pi.
#
# Usage:
#   ./models/fetch_models.sh                # defaults: Qwen2.5-1.5B + bge-small
#   DEST=/mnt/sd/var/lib/rpi-hub/models ./models/fetch_models.sh
#
# To refresh: bump the URL + sha256 below, re-run.

set -euo pipefail

DEST="${DEST:-./payload/var/lib/rpi-hub/models}"

log() { printf '[fetch-models] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

require() { command -v "$1" >/dev/null || die "$1 required ($2)"; }
require curl     "install via apt/brew"
require sha256sum "install: coreutils"

mkdir -p "$DEST"

# Format: filename | url | sha256
declare -a MODELS=(
    "qwen2.5-1.5b-instruct-q4_k_m.gguf|https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf|6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
    "bge-small-en-v1.5-q8_0.gguf|https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q8_0.gguf|ec38e8da142596baa913124ae50550de284b6916bf59577ef2f0cb9660c2f514"
)

fetch_one() {
    local name="$1" url="$2" expected="$3"
    local out="$DEST/$name"

    if [[ -f "$out" && -n "$expected" ]]; then
        local actual
        actual=$(sha256sum "$out" | cut -d' ' -f1)
        if [[ "$actual" == "$expected" ]]; then
            log "cached $name"
            return 0
        fi
        log "stale  $name (refetching)"
        rm -f "$out"
    fi

    log "get    $name"
    # -C - resumes from $out.partial's current size if the previous run died
    # mid-stream. --retry-all-errors makes --retry catch "connection reset by
    # peer" (curl 56) too, not just connect-time failures. Mirrors the fix
    # ab8a014 made for content/fetch.sh after a ~2GB ifixit download was lost
    # to the same hang pattern.
    curl --fail --location --retry 5 --retry-delay 5 --retry-all-errors \
        -C - --progress-bar -o "$out.partial" "$url"

    local actual
    actual=$(sha256sum "$out.partial" | cut -d' ' -f1)
    if [[ -n "$expected" ]]; then
        if [[ "$actual" != "$expected" ]]; then
            rm -f "$out.partial"
            die "sha256 mismatch on $name (got $actual)"
        fi
        mv "$out.partial" "$out"
        log "ok     $name"
    else
        mv "$out.partial" "$out"
        log "ok     $name  sha256=$actual"
        log "       (paste back into this script to lock reproducibility)"
    fi
}

for entry in "${MODELS[@]}"; do
    IFS='|' read -r name url expected <<<"$entry"
    fetch_one "$name" "$url" "$expected"
done

log ""
log "done. Transfer to the Pi:"
log "  rsync -avh --progress $DEST/ pi@hub.local:/var/lib/rpi-hub/models/"
