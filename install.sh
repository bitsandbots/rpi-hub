#!/usr/bin/env bash
# SIGNAL installer — Phase 1 (Bare AP).
#
# Idempotent: re-running should be a no-op if everything is already in place.
# Re-runs upgrade configs from the repo in-place; service is restarted only
# if a config actually changed.
#
# Phase 1 scope:
#   - Install hostapd, dnsmasq, iptables-persistent
#   - Link repo configs into /etc
#   - Pin wlan0 to 192.168.4.1 via dhcpcd
#   - Apply sysctl (ip_forward=0)
#   - Apply iptables FORWARD drop on wlan0 cross-interface traffic
#   - Enable signal-ap.service
#
# Phases 2+ will append their own steps below the Phase 1 block, gated by
# the PHASE env var (default: all phases that have shipped at this tag).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${PHASE:-1}"
COUNTRY="${SIGNAL_COUNTRY_CODE:-US}"

log() { printf '[signal-install] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

require_root() {
    [[ $EUID -eq 0 ]] || die "must run as root (try: sudo $0)"
}

require_bookworm() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        if [[ "${VERSION_CODENAME:-}" != "bookworm" ]]; then
            log "warning: tested on Raspberry Pi OS Lite Bookworm; found ${VERSION_CODENAME:-unknown}"
        fi
    fi
}

apt_install() {
    log "installing packages: $*"
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@"
}

# Copy if source differs from destination. Returns 0 if a copy happened.
install_config() {
    local src="$1" dst="$2"
    install -d "$(dirname "$dst")"
    if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
        return 1
    fi
    install -m 0644 "$src" "$dst"
    log "installed $dst"
    return 0
}

ensure_dhcpcd_block() {
    local marker_begin="# >>> SIGNAL Phase 1 (wlan0 static) >>>"
    local marker_end="# <<< SIGNAL Phase 1 (wlan0 static) <<<"
    local conf="/etc/dhcpcd.conf"
    [[ -f "$conf" ]] || die "$conf not found; is this Raspberry Pi OS?"

    if grep -qF "$marker_begin" "$conf"; then
        return 0
    fi

    {
        printf '\n%s\n' "$marker_begin"
        cat "${REPO_DIR}/config/dhcpcd/signal.conf"
        printf '%s\n' "$marker_end"
    } >>"$conf"
    log "appended SIGNAL block to $conf"
}

ensure_hostapd_default() {
    local default="/etc/default/hostapd"
    install -d "$(dirname "$default")"
    if ! grep -q '^DAEMON_CONF="/etc/hostapd/hostapd.conf"' "$default" 2>/dev/null; then
        printf 'DAEMON_CONF="/etc/hostapd/hostapd.conf"\n' >"$default"
        log "wrote $default"
    fi
}

apply_country_code() {
    local conf="/etc/hostapd/hostapd.conf"
    sed -i "s/^country_code=.*/country_code=${COUNTRY}/" "$conf"
}

apply_iptables() {
    # Drop any packet that arrived on wlan0 and would be forwarded out
    # anywhere else. -C checks existence; -I inserts if missing.
    if ! iptables -C FORWARD -i wlan0 ! -o wlan0 -j DROP 2>/dev/null; then
        iptables -I FORWARD 1 -i wlan0 ! -o wlan0 -j DROP
        log "applied iptables FORWARD drop"
    fi
    netfilter-persistent save >/dev/null
}

apply_sysctl() {
    install_config "${REPO_DIR}/config/sysctl/signal.conf" /etc/sysctl.d/30-signal.conf || true
    sysctl --system >/dev/null
}

install_unit() {
    install -m 0644 "${REPO_DIR}/systemd/signal-ap.service" /etc/systemd/system/signal-ap.service
    systemctl daemon-reload
    systemctl enable signal-ap.service
}

phase1() {
    log "Phase 1 — Bare AP"
    require_bookworm

    # Stop conflicting services before reconfiguring.
    systemctl stop hostapd dnsmasq 2>/dev/null || true
    systemctl unmask hostapd 2>/dev/null || true

    apt_install hostapd dnsmasq iptables iptables-persistent netfilter-persistent

    install_config "${REPO_DIR}/config/hostapd/hostapd.conf"  /etc/hostapd/hostapd.conf  || true
    install_config "${REPO_DIR}/config/dnsmasq/signal.conf"   /etc/dnsmasq.d/signal.conf || true
    apply_country_code
    ensure_hostapd_default
    ensure_dhcpcd_block
    apply_sysctl
    apply_iptables
    install_unit

    systemctl restart dhcpcd
    systemctl start signal-ap.service

    log "Phase 1 complete. Look for SSID 'SIGNAL_INFOHUB'."
    log "Status: systemctl status signal-ap"
}

main() {
    require_root
    case "$PHASE" in
        1) phase1 ;;
        *) die "PHASE=$PHASE not implemented yet (this tag ships Phase 1)" ;;
    esac
}

main "$@"
