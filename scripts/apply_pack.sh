#!/usr/bin/env bash
# Purpose: Apply a regional content pack to a built rpi-hub image.
# Unit:    n/a (workstation-side helper; install.sh --pack=<name> wraps it)
# Phase:   9B
#
# Reads packs/<name>/pack.yaml, fetches the listed ZIMs into
# ./payload/var/lib/kiwix, stages printable PDFs into the portal tree,
# and writes NOAA presets where Phase 8 expects them. Idempotent.

set -euo pipefail

PACK="${1:-general-purpose}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACK_DIR="$REPO_DIR/packs/$PACK"
DEST_KIWIX="${DEST_KIWIX:-$REPO_DIR/payload/var/lib/kiwix}"
DEST_PRINT="${DEST_PRINT:-$REPO_DIR/payload/var/www/rpi-hub-portal/print}"
DEST_PRESETS="${DEST_PRESETS:-$REPO_DIR/payload/var/lib/rpi-hub/listen}"

log() { printf '[apply-pack] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

require() { command -v "$1" >/dev/null || die "$1 required ($2)"; }
require yq "install via apt/brew (mikefarah Go yq)"

[[ -d "$PACK_DIR" ]] || die "pack not found: $PACK_DIR"
manifest="$PACK_DIR/pack.yaml"
[[ -f "$manifest" ]] || die "missing $manifest"

log "applying pack: $PACK"

# 1) Fetch ZIMs via the existing fetch script. The pack only names files;
#    fetch.sh reads URLs from content/manifest.yaml so a pack can refer
#    to any tier without duplicating URLs.
mapfile -t zim_names < <(yq -r '.zims[]' "$manifest")
log "zims: ${zim_names[*]}"
# fetch.sh fetches by tier; we always run the highest tier the pack pins.
tier=$(yq -r '.tier' "$manifest")
DEST="$DEST_KIWIX" "$REPO_DIR/content/fetch.sh" "$tier"

# 2) Stage printable PDFs. PDFs live in packs/<name>/print/ on the
#    workstation; we rsync the directory into the portal tree. The PDFs
#    themselves are built from sibling .html sources by
#    scripts/build_pack_pdfs.sh — fail loudly if a referenced PDF is
#    missing so the operator can run the builder before re-baking.
if [[ -d "$PACK_DIR/print" ]]; then
    n=$(yq -r '.print | length' "$manifest")
    missing=()
    for i in $(seq 0 $((n - 1))); do
        f=$(yq -r ".print[$i].file" "$manifest")
        [[ -f "$PACK_DIR/print/$f" ]] || missing+=("$f")
    done
    if (( ${#missing[@]} )); then
        log "missing PDFs: ${missing[*]}"
        die "run scripts/build_pack_pdfs.sh on the workstation first"
    fi
    mkdir -p "$DEST_PRINT"
    rsync -a --delete "$PACK_DIR/print/" "$DEST_PRINT/" 2>/dev/null \
        || cp -a "$PACK_DIR/print/." "$DEST_PRINT/"
    # Build a tiny index page (./print/index.html) listing each PDF and
    # its human-readable title. Phase 9.6 ships nginx routing for /print/.
    {
        printf '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        printf '<title>Print: %s</title>' "$(yq -r '.display_name' "$manifest")"
        printf '<link rel="stylesheet" href="/assets/css/rpi-hub.css"></head><body>'
        printf '<main><h1>Print cards — %s</h1><ul>' "$(yq -r '.display_name' "$manifest")"
        n=$(yq -r '.print | length' "$manifest")
        for i in $(seq 0 $((n - 1))); do
            file=$(yq -r ".print[$i].file" "$manifest")
            title=$(yq -r ".print[$i].title" "$manifest")
            printf '<li><a href="%s">%s</a></li>' "$file" "$title"
        done
        printf '</ul><p><a href="/">← Back to hub</a></p></main></body></html>'
    } >"$DEST_PRINT/index.html"
    log "staged print cards in $DEST_PRINT"
fi

# 3) NOAA presets. Phase 8 reads this YAML at install time; if Phase 8 is
#    not enabled the file is harmless.
if yq -e '.noaa' "$manifest" >/dev/null 2>&1; then
    mkdir -p "$DEST_PRESETS"
    yq -P '.noaa' "$manifest" >"$DEST_PRESETS/noaa-presets.yaml"
    log "wrote noaa presets to $DEST_PRESETS/noaa-presets.yaml"
fi

log "done. pack=$PACK applied to $DEST_KIWIX and $DEST_PRINT"
