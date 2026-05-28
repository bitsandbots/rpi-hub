#!/usr/bin/env bash
# Purpose: Compile every packs/<name>/print/*.html field-card source into
#          a PDF in the same directory. Workstation-side; depends on a
#          headless chromium / google-chrome / chromium-browser binary or
#          wkhtmltopdf as a fallback. Idempotent.
# Unit:    n/a (bake-time workstation helper; not on the Pi)
# Phase:   9B
#
# Why not on the Pi: the chromium dependency is heavy, the conversion is
# deterministic from the .html sources, and the project's offline-first
# stance keeps the device itself free of build tooling. Run this once on
# the workstation that bakes the image; apply_pack.sh then rsyncs the
# resulting PDFs into /var/www/rpi-pod-portal/print/ on the device.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKS_DIR="$REPO_DIR/packs"

log() { printf '[build-pack-pdfs] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

find_browser() {
  for cmd in google-chrome chromium chromium-browser chrome; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf '%s' "$cmd"
      return 0
    fi
  done
  return 1
}

BROWSER="$(find_browser || true)"
WKHTML="$(command -v wkhtmltopdf || true)"

if [[ -z "$BROWSER" && -z "$WKHTML" ]]; then
  die "no PDF renderer found. Install chromium (apt install chromium) or wkhtmltopdf."
fi

render_one() {
  local html="$1"
  local pdf="${html%.html}.pdf"

  # Skip if the PDF is newer than the source.
  if [[ -f "$pdf" && "$pdf" -nt "$html" ]]; then
    log "up-to-date: $pdf"
    return 0
  fi

  if [[ -n "$BROWSER" ]]; then
    "$BROWSER" \
      --headless=new \
      --disable-gpu \
      --no-sandbox \
      --no-pdf-header-footer \
      --print-to-pdf="$pdf" \
      --virtual-time-budget=2000 \
      "file://$html" >/dev/null 2>&1
  else
    "$WKHTML" --quiet --print-media-type "$html" "$pdf"
  fi

  [[ -s "$pdf" ]] || die "renderer produced empty PDF: $pdf"
  log "built: $pdf"
}

count=0
while IFS= read -r -d '' html; do
  render_one "$html"
  count=$((count + 1))
done < <(find "$PACKS_DIR" -mindepth 3 -maxdepth 3 -name '*.html' -path '*/print/*' -print0)

log "done. rendered $count card(s)."
