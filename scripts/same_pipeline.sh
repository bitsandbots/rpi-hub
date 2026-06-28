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
RTLSDR_LOCK="${rpi_hub_RTLSDR_LOCK:-/run/rpi-hub/rtlsdr.lock}"

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

# Build the JSON body safely. multimon-ng output is RF-derived, so escape
# it through a JSON-aware encoder (jq when present) rather than a naive
# quote-substitution that mishandles backslashes/control chars.
emit_json() {
    if command -v jq >/dev/null; then
        jq -Rn --arg l "$1" '{line:$l}'
    else
        # Fallback: escape backslash THEN double-quote, and strip CRs.
        local s="${1//\\/\\\\}"; s="${s//\"/\\\"}"; s="${s//$'\r'/}"
        printf '{"line":"%s"}' "$s"
    fi
}

run_pipeline() {
    log "tuning rtl_fm to ${FREQ_HZ} Hz; decoding EAS via multimon-ng"
    # rtl_fm → multimon-ng → grep for ZCZC headers → POST each line.
    # We do not buffer aggressively: an alert is a single header burst
    # that needs to land on the landing page within seconds.
    rtl_fm -M fm -f "${FREQ_HZ}" -s 22050 -r 22050 -g 40 -l 0 - 2>/dev/null \
      | multimon-ng -a EAS -q -t raw - 2>/dev/null \
      | while IFS= read -r line; do
            case "$line" in
                *ZCZC-*)
                    log "alert: $line"
                    # 1s connect, 2s total — never block on a stuck listen.
                    curl --silent --max-time 2 --connect-timeout 1 \
                        --header 'Content-Type: application/json' \
                        --data-binary "$(emit_json "$line")" \
                        "${SERVICE_URL}/alerts/internal" >/dev/null || true
                    ;;
            esac
        done
}

# Single-dongle mutex: hold the shared RTL-SDR flock for the whole
# pipeline lifetime so the in-process Tuner (FM/GPS) and dump1090 cannot
# claim the dongle while SAME owns it. We hold the lock on fd 9 for the
# duration of run_pipeline; -n fails fast rather than queueing. If flock
# or the lock file is unavailable we still run (the install-time enable
# gate is the backstop).
if command -v flock >/dev/null 2>&1 && exec 9>"$RTLSDR_LOCK" 2>/dev/null; then
    if flock -n 9; then
        run_pipeline
    else
        log "RTL-SDR busy (held by Tuner or dump1090); SAME not starting"
        exit 0
    fi
else
    run_pipeline
fi
