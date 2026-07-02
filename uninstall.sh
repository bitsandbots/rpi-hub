#!/usr/bin/env bash
# rpi-hub uninstaller — reverses install.sh through Phase 5.
#
# Idempotent. Leaves package binaries installed (apt removal is the user's
# call) but disables the service, unlinks configs, removes the dhcpcd block,
# and drops the iptables rule. Phase 4's static assets live under
# /var/www/rpi-hub-portal and are removed wholesale by remove_nginx_site.
# Phase 5's deployed code at /opt/rpi-hub and runtime state at /etc/rpi-hub
# are removed by remove_status.

set -euo pipefail

log() { printf '[rpi-hub-uninstall] %s\n' "$*" >&2; }

require_root() { [[ $EUID -eq 0 ]] || { log "must run as root"; exit 1; }; }

remove_dhcpcd_block() {
    local conf="/etc/dhcpcd.conf"
    [[ -f "$conf" ]] || return 0
    sed -i '/# >>> rpi-hub Phase 1 (wlan0 static) >>>/,/# <<< rpi-hub Phase 1 (wlan0 static) <<</d' "$conf"
}

drop_iptables() {
    while iptables -C FORWARD -i wlan0 ! -o wlan0 -j DROP 2>/dev/null; do
        iptables -D FORWARD -i wlan0 ! -o wlan0 -j DROP
    done
    if command -v netfilter-persistent >/dev/null; then
        netfilter-persistent save >/dev/null || true
    fi
}

remove_nginx_site() {
    rm -f /etc/nginx/sites-enabled/rpi-hub-portal
    rm -f /etc/nginx/sites-available/rpi-hub-portal
    rm -rf /var/www/rpi-hub-portal
    # Restore the stock default site if Debian's copy is still around.
    if [[ -f /etc/nginx/sites-available/default && ! -L /etc/nginx/sites-enabled/default ]]; then
        ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    fi
    if command -v nginx >/dev/null && nginx -t 2>/dev/null; then
        systemctl reload nginx.service 2>/dev/null || true
    fi
}

remove_kiwix() {
    systemctl disable --now rpi-hub-kiwix.service 2>/dev/null || true
    rm -f /etc/systemd/system/rpi-hub-kiwix.service
    # Intentionally leave /var/lib/kiwix and its ZIMs in place. Re-fetching
    # tens of GB of content is the kind of "destructive" the user has to
    # ask for explicitly — `rm -rf /var/lib/kiwix` is one extra command.
}

remove_assistant() {
    # Phase 6 units. Bring them down before /opt/rpi-hub goes away.
    for unit in rpi-hub-assist.service rpi-hub-llama.service rpi-hub-retrieve.service; do
        systemctl disable --now "$unit" 2>/dev/null || true
        rm -f "/etc/systemd/system/${unit}"
    done
    # Leave /var/lib/rpi-hub/{index,models}/ in place: re-downloading model
    # weights and rebuilding the index is expensive. `rm -rf /var/lib/rpi-hub`
    # is the user's call.
}

remove_mesh() {
    # Phase 7 + v1.1 radio data planes. Stop the units, drop the unit
    # files. The Ed25519 keypair at /var/lib/rpi-hub/keys is intentionally
    # preserved — a re-install keeps the node's identity stable, which is
    # what trusted peers rely on.
    for unit in rpi-hub-batman.service rpi-hub-reticulum.service rpi-hub-mesh.service rpi-hub-mesh-keygen.service; do
        systemctl disable --now "$unit" 2>/dev/null || true
        rm -f "/etc/systemd/system/${unit}"
    done
}

remove_listen() {
    # Phase 8. Two units, both bound to dongle hardware. We stop the
    # pipeline before the control plane so a final stop request can
    # reach the arbiter.
    for unit in rpi-hub-listen-same.service rpi-hub-listen.service; do
        systemctl disable --now "$unit" 2>/dev/null || true
        rm -f "/etc/systemd/system/${unit}"
    done
    # Leave /var/lib/rpi-hub/listen in place: pack-supplied NOAA presets
    # are useful again immediately on reinstall.

    # Phase 8.4 — undo dump1090-mutability enablement. The Debian
    # package itself stays installed (apt removal is the user's call);
    # we only revert our /etc/default override and disable the unit.
    systemctl disable --now dump1090-mutability.service 2>/dev/null || true
    if [[ -f /etc/default/dump1090-mutability ]] \
       && grep -q "rpi-hub" /etc/default/dump1090-mutability 2>/dev/null; then
        rm -f /etc/default/dump1090-mutability
    fi
    # Phase 8.4 polish — adsb-shield (opt-in position-rounder).
    systemctl disable --now rpi-hub-adsb-shield.timer 2>/dev/null || true
    rm -f /etc/systemd/system/rpi-hub-adsb-shield.service \
          /etc/systemd/system/rpi-hub-adsb-shield.timer \
          /etc/rpi-hub/adsb-precision \
          /run/dump1090-mutability/aircraft.shielded.json
}

remove_notes() {
    # Phase 9A. The board lives on tmpfs so there's no persistent state
    # to clean up beyond the service + token + print tree.
    systemctl disable --now rpi-hub-notes.service 2>/dev/null || true
    rm -f /etc/systemd/system/rpi-hub-notes.service
    rm -f /etc/rpi-hub/notes-owner-token /etc/rpi-hub/mesh-owner-token
    rm -rf /var/www/rpi-hub-portal/print
}

remove_status() {
    systemctl disable --now rpi-hub-status.service 2>/dev/null || true
    rm -f /etc/systemd/system/rpi-hub-status.service
    rm -rf /opt/rpi-hub
    rm -rf /etc/rpi-hub
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
    remove_mesh
    remove_listen
    remove_notes
    remove_assistant
    remove_status
    remove_kiwix
    remove_nginx_site

    systemctl disable --now rpi-hub-ap.service 2>/dev/null || true
    rm -f /etc/systemd/system/rpi-hub-ap.service
    systemctl daemon-reload

    rm -f /etc/hostapd/hostapd.conf
    rm -f /etc/dnsmasq.d/rpi-hub.conf
    rm -f /etc/sysctl.d/30-rpi-hub.conf

    remove_dhcpcd_block
    drop_iptables
    sysctl --system >/dev/null
    systemctl restart dhcpcd 2>/dev/null || true

    log "rpi-hub uninstalled. Packages (hostapd, dnsmasq, nginx, kiwix-tools, iptables-persistent, python3-fastapi, python3-uvicorn) left in place."
    log "Library content at /var/lib/kiwix/ preserved — delete manually if you want it gone."
}

main "$@"
