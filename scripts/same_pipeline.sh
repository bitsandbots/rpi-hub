#!/usr/bin/env bash
# Purpose: SAME alert decoder pipeline. Tunes the dongle to the first
#          NOAA WX preset, demodulates with rtl_fm, decodes EAS headers
#          with multimon-ng, and POSTs each parsed line to rpi-hub-listen.
# Unit:    rpi-hub-listen-same.service
# Phase:   8 (sub-phase 8.2)
#
# Why a script and not a child of rpi-hub-listen: rtl_fm + multimon-ng are
# the audio pipeline, and they should be supervised by systemd directly
# so a SIGTERM cleanly drains both. The Python service is the control
# plane; this is the data plane.

set -euo pipefail

FREQ_HZ="${rpi_hub_SAME_FREQ_HZ:-162400000}"
SERVICE_URL="${rpi_hub_LISTEN_URL:-http://127.0.0.1:8300}"

log() { printf '[same-pipeline] %s\n' "$*" >&2; }

if ! command -v rtl_fm >/dev/null; then
    log "rtl_fm not installed; pipeline cannot start"
    exit 1
fi
if ! command -v multimon-ng >/dev/null; then
    log "multimon-ng not installed; pipeline cannot start"
    exit 1
fi
if ! command -v curl >/dev/null; then
    log "curl not installed; pipeline cannot start"
    exit 1
fi

log "tuning rtl_fm to ${FREQ_HZ} Hz; decoding EAS via multimon-ng"

# rtl_fm → multimon-ng → grep for ZCZC headers → POST each line.
# We do not buffer aggressively: an alert is a single header burst that
# needs to land on the landing page within seconds.
rtl_fm -M fm -f "${FREQ_HZ}" -s 22050 -r 22050 -g 40 -l 0 - 2>/dev/null \
  | multimon-ng -a EAS -q -t raw - 2>/dev/null \
  | while IFS= read -r line; do
        case "$line" in
            *ZCZC-*)
                log "alert: $line"
                # 1s connect, 2s total — never block the pipeline on a
                # stuck rpi-hub-listen.
                curl --silent --max-time 2 --connect-timeout 1 \
                    --header 'Content-Type: application/json' \
                    --data-binary "$(printf '{"line":"%s"}' "${line//\"/\\\"}")" \
                    "${SERVICE_URL}/alerts/internal" >/dev/null || true
                ;;
        esac
    done
