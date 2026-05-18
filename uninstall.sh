#!/usr/bin/env bash
# SIGNAL uninstaller — reverses install.sh for Phase 1.
#
# Idempotent. Leaves package binaries installed (apt removal is the user's
# call) but disables the service, unlinks configs, removes the dhcpcd block,
# and drops the iptables rule.

set -euo pipefail

log() { printf '[signal-uninstall] %s\n' "$*" >&2; }

require_root() { [[ $EUID -eq 0 ]] || { log "must run as root"; exit 1; }; }

remove_dhcpcd_block() {
    local conf="/etc/dhcpcd.conf"
    [[ -f "$conf" ]] || return 0
    sed -i '/# >>> SIGNAL Phase 1 (wlan0 static) >>>/,/# <<< SIGNAL Phase 1 (wlan0 static) <<</d' "$conf"
}

drop_iptables() {
    while iptables -C FORWARD -i wlan0 ! -o wlan0 -j DROP 2>/dev/null; do
        iptables -D FORWARD -i wlan0 ! -o wlan0 -j DROP
    done
    command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null || true
}

main() {
    require_root
    systemctl disable --now signal-ap.service 2>/dev/null || true
    rm -f /etc/systemd/system/signal-ap.service
    systemctl daemon-reload

    rm -f /etc/hostapd/hostapd.conf
    rm -f /etc/dnsmasq.d/signal.conf
    rm -f /etc/sysctl.d/30-signal.conf

    remove_dhcpcd_block
    drop_iptables
    sysctl --system >/dev/null
    systemctl restart dhcpcd 2>/dev/null || true

    log "SIGNAL Phase 1 uninstalled. Packages (hostapd, dnsmasq, iptables-persistent) left in place."
}

main "$@"
