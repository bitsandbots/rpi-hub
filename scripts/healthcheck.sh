#!/usr/bin/env bash
# SIGNAL — on-device smoke test.
#
# Checks every layer the hub depends on. Each check prints OK / WARN / FAIL
# and the script exits non-zero if any check failed. WARNings (e.g. empty
# library) still produce exit 0 — they're intentional states, not breakage.
#
# Drives `make smoke`. Safe to run on a live hub at any time; touches no
# state.

set -uo pipefail  # not -e: we want to keep going past individual failures

PASS=0
FAIL=0
WARN=0

green=$'\033[32m'; yellow=$'\033[33m'; red=$'\033[31m'; reset=$'\033[0m'
# Plain output if stdout isn't a TTY (e.g. CI, journald).
[[ -t 1 ]] || { green=""; yellow=""; red=""; reset=""; }

ok()   { printf '  %sOK%s    %s\n'   "$green"  "$reset" "$*"; PASS=$((PASS+1)); }
warn() { printf '  %sWARN%s  %s\n'   "$yellow" "$reset" "$*"; WARN=$((WARN+1)); }
fail() { printf '  %sFAIL%s  %s\n'   "$red"    "$reset" "$*"; FAIL=$((FAIL+1)); }

section() { printf '\n== %s ==\n' "$*"; }

check_unit() {
    local unit="$1"
    if systemctl is-active --quiet "$unit"; then
        ok "$unit is active"
    elif systemctl is-enabled --quiet "$unit" 2>/dev/null; then
        fail "$unit is enabled but not active"
    else
        warn "$unit is not enabled (expected for optional services)"
    fi
}

check_http() {
    local url="$1" expect="${2:-200}"
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "$url" || echo 000)"
    if [[ "$code" == "$expect" ]]; then
        ok "GET $url → $code"
    else
        fail "GET $url → $code (expected $expect)"
    fi
}

check_json() {
    local url="$1"
    local body
    body="$(curl -s --max-time 4 "$url" || true)"
    if [[ -z "$body" ]]; then
        fail "GET $url returned empty body"
        return
    fi
    if ! python3 -c "import json,sys; json.loads(sys.stdin.read())" <<<"$body" 2>/dev/null; then
        fail "GET $url did not return valid JSON"
        return
    fi
    ok "GET $url returned valid JSON ($(wc -c <<<"$body" | tr -d ' ') bytes)"
}

section "Phase 1: AP"
check_unit signal-ap.service
if iptables -C FORWARD -i wlan0 ! -o wlan0 -j DROP 2>/dev/null; then
    ok "iptables egress-block on wlan0 is in place"
else
    fail "iptables egress-block missing — clients could route off-network"
fi

section "Phase 2: Captive portal"
check_unit nginx.service
check_http "http://127.0.0.1/" 200
# Default_server should 302 anything that isn't hub.local.
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 -H 'Host: captive.apple.com' http://127.0.0.1/ || echo 000)"
if [[ "$code" == "302" ]]; then
    ok "captive probe Host: captive.apple.com → 302"
else
    fail "captive probe Host: captive.apple.com → $code (expected 302)"
fi

section "Phase 3: Library"
if compgen -G "/var/lib/kiwix/*.zim" >/dev/null; then
    check_unit signal-kiwix.service
    check_http "http://127.0.0.1/library/" 200
else
    warn "/var/lib/kiwix is empty — signal-kiwix intentionally inactive (run content/fetch.sh)"
fi

section "Phase 4: Frontend"
if [[ -f /var/www/signal-portal/index.html ]]; then
    ok "/var/www/signal-portal/index.html present"
else
    fail "/var/www/signal-portal/index.html missing — portal tree not deployed"
fi
if [[ -f /var/www/signal-portal/status.html ]]; then
    ok "/var/www/signal-portal/status.html present"
else
    fail "/var/www/signal-portal/status.html missing"
fi
if [[ -s /var/www/signal-portal/assets/fonts/exo2-700.woff2 ]]; then
    ok "brand fonts present"
else
    warn "brand fonts missing — run scripts/fetch_fonts.sh, page falls back to system fonts"
fi

section "Phase 5: Status API"
check_unit signal-status.service
check_http "http://127.0.0.1/api/status" 200
check_json "http://127.0.0.1/api/status"

section "Summary"
printf '  pass=%d  warn=%d  fail=%d\n' "$PASS" "$WARN" "$FAIL"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
