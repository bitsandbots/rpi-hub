#!/usr/bin/env bash
# SIGNAL uninstaller — reverses install.sh through Phase 5.
#
# Idempotent. Leaves package binaries installed (apt removal is the user's
# call) but disables the service, unlinks configs, removes the dhcpcd block,
# and drops the iptables rule. Phase 4's static assets live under
# /var/www/signal-portal and are removed wholesale by remove_nginx_site.
# Phase 5's deployed code at /opt/signal and runtime state at /etc/signal
# are removed by remove_status.

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

remove_assistant() {
    # Phase 6 units. Bring them down before /opt/signal goes away.
    for unit in signal-assist.service signal-llama.service signal-retrieve.service; do
        systemctl disable --now "$unit" 2>/dev/null || true
        rm -f "/etc/systemd/system/${unit}"
    done
    # Leave /var/lib/signal/{index,models}/ in place: re-downloading model
    # weights and rebuilding the index is expensive. `rm -rf /var/lib/signal`
    # is the user's call.
}

remove_notes() {
    # Phase 9A. The board lives on tmpfs so there's no persistent state
    # to clean up beyond the service + token + print tree.
    systemctl disable --now signal-notes.service 2>/dev/null || true
    rm -f /etc/systemd/system/signal-notes.service
    rm -f /etc/signal/notes-owner-token
    rm -rf /var/www/signal-portal/print
}

remove_status() {
    systemctl disable --now signal-status.service 2>/dev/null || true
    rm -f /etc/systemd/system/signal-status.service
    rm -rf /opt/signal
    rm -rf /etc/signal
    # Restore the Debian default MOTD if our copy is still in place.
    # Bookworm's stock /etc/motd is empty; just blanking the file is safe.
    if [[ -f /etc/motd ]] && grep -q "OFFLINE INFOHUB" /etc/motd 2>/dev/null; then
        : >/etc/motd
    fi
}

main() {
    require_root

    # Tear down in reverse phase order. The status API and Kiwix are the
    # user-visible services; bring them down before the AP layer so a
    # watcher sees the outage propagate top-down.
    remove_notes
    remove_assistant
    remove_status
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

    log "SIGNAL uninstalled. Packages (hostapd, dnsmasq, nginx, kiwix-tools, iptables-persistent, python3-fastapi, python3-uvicorn) left in place."
    log "Library content at /var/lib/kiwix/ preserved — delete manually if you want it gone."
}

main "$@"
