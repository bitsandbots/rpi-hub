#!/usr/bin/env bash
# SIGNAL uninstaller — reverses install.sh through Phase 3.
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

remove_nginx_site() {
    rm -f /etc/nginx/sites-enabled/signal-portal
    rm -f /etc/nginx/sites-available/signal-portal
    rm -rf /var/www/signal-portal
    # Restore the stock default site if Debian's copy is still around.
    if [[ -f /etc/nginx/sites-available/default && ! -L /etc/nginx/sites-enabled/default ]]; then
        ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    fi
    if command -v nginx >/dev/null && nginx -t 2>/dev/null; then
        systemctl reload nginx.service 2>/dev/null || true
    fi
}

remove_kiwix() {
    systemctl disable --now signal-kiwix.service 2>/dev/null || true
    rm -f /etc/systemd/system/signal-kiwix.service
    # Intentionally leave /var/lib/kiwix and its ZIMs in place. Re-fetching
    # tens of GB of content is the kind of "destructive" the user has to
    # ask for explicitly — `rm -rf /var/lib/kiwix` is one extra command.
}

main() {
    require_root

    # Tear down in reverse phase order. Kiwix and nginx are the user-visible
    # services; bring them down before the AP layer so a watcher sees the
    # outage propagate top-down.
    remove_kiwix
    remove_nginx_site

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

    log "SIGNAL uninstalled. Packages (hostapd, dnsmasq, nginx, kiwix-tools, iptables-persistent) left in place."
    log "Library content at /var/lib/kiwix/ preserved — delete manually if you want it gone."
}

main "$@"
