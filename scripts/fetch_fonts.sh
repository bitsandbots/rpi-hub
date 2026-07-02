#!/usr/bin/env bash
# rpi-hub — workstation-side font fetcher.
#
# Downloads the woff2 files that web/portal/assets/css/rpi-hub.css references:
#   exo2-700.woff2, jakarta-400.woff2, jakarta-700.woff2, plexmono-400.woff2
# into www/portal/assets/fonts/ so the bake step picks them up.
#
# Runs on a workstation with internet. The Pi never reaches out. This is the
# same pattern as content/fetch.sh: the device is air-gapped at runtime; only
# the build/bake step touches the network.
#
# Source: jsDelivr-hosted @fontsource packages. Those packages re-host the
# upstream OFL/SIL builds as woff2 with no foundry-side rewrites, which is
# what we want for an offline mirror. Major-version pin in URLs is stable.
#
# Licensing (all SIL OFL 1.1, compatible with MIT):
#   Exo 2             — Natanael Gama / NDISCOVER
#   Plus Jakarta Sans — Gumpita Rahayu / Tokotype
#   IBM Plex Mono     — IBM Design
# Each license is preserved alongside the fonts as OFL.txt files; the script
# fetches a single shared OFL.txt that applies to all three families.
#
# Idempotent: existing files with a matching sha256 (when pinned) are kept.
# Pin hashes after a first known-good run by editing FONT_HASHES below.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${REPO_DIR}/www/portal/assets/fonts"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

FONTSOURCE_VER="5"  # pin to major; minor/patch resolved by jsDelivr

declare -A FONT_URLS=(
    [exo2-700.woff2]="https://cdn.jsdelivr.net/npm/@fontsource/exo-2@${FONTSOURCE_VER}/files/exo-2-latin-700-normal.woff2"
    [jakarta-400.woff2]="https://cdn.jsdelivr.net/npm/@fontsource/plus-jakarta-sans@${FONTSOURCE_VER}/files/plus-jakarta-sans-latin-400-normal.woff2"
    [jakarta-700.woff2]="https://cdn.jsdelivr.net/npm/@fontsource/plus-jakarta-sans@${FONTSOURCE_VER}/files/plus-jakarta-sans-latin-700-normal.woff2"
    [plexmono-400.woff2]="https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@${FONTSOURCE_VER}/files/ibm-plex-mono-latin-400-normal.woff2"
)

# Pinned sha256s. Fill in after a successful fetch on a trusted machine and
# commit the populated table for reproducible bakes. Empty = skip verify.
declare -A FONT_HASHES=(
    [exo2-700.woff2]=""
    [jakarta-400.woff2]=""
    [jakarta-700.woff2]=""
    [plexmono-400.woff2]=""
)

OFL_URL="https://cdn.jsdelivr.net/npm/@fontsource/exo-2@${FONTSOURCE_VER}/LICENSE"

log() { printf '[rpi-hub-fonts] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "missing tool: $1"; }
need curl
need sha256sum

mkdir -p "${DEST_DIR}"

fetch_one() {
    local name="$1" url="$2" want="$3"
    local target="${DEST_DIR}/${name}"
    local staging="${TMP_DIR}/${name}"

    if [[ -f "${target}" && -n "${want}" ]]; then
        local have
        have="$(sha256sum "${target}" | awk '{print $1}')"
        if [[ "${have}" == "${want}" ]]; then
            log "skip ${name} (sha256 match)"
            return 0
        fi
    fi

    log "fetch ${name}"
    curl --fail --silent --show-error --location \
        --connect-timeout 10 --max-time 60 \
        -o "${staging}" "${url}"

    if [[ -n "${want}" ]]; then
        local have
        have="$(sha256sum "${staging}" | awk '{print $1}')"
        if [[ "${have}" != "${want}" ]]; then
            die "${name} sha256 mismatch — expected ${want}, got ${have}"
        fi
    else
        log "  sha256: $(sha256sum "${staging}" | awk '{print $1}')  # pin me"
    fi

    install -m 0644 "${staging}" "${target}"
}

fetch_license() {
    local target="${DEST_DIR}/OFL.txt"
    [[ -f "${target}" ]] && return 0
    log "fetch OFL.txt"
    curl --fail --silent --show-error --location \
        --connect-timeout 10 --max-time 30 \
        -o "${target}" "${OFL_URL}"
}

main() {
    log "destination: ${DEST_DIR}"
    for name in "${!FONT_URLS[@]}"; do
        fetch_one "${name}" "${FONT_URLS[$name]}" "${FONT_HASHES[$name]}"
    done
    fetch_license
    log "done — ${#FONT_URLS[@]} files installed into www/portal/assets/fonts/"
    log "next: commit the populated hash table back into this script for reproducible bakes."
}

main "$@"
