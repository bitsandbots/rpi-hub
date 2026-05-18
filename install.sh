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
# Phase 2 scope (additive):
#   - Install nginx
#   - Link the signal-portal site config + landing page into /etc and /var/www
#   - Drop the stock nginx default site so it can't shadow us
#   - Reload nginx (validated with nginx -t first)
#
# Phase 3 scope (additive):
#   - Install kiwix-tools
#   - Create /var/lib/kiwix as the ZIM payload directory
#   - Install signal-kiwix.service (stays inactive until ZIMs appear)
#
# Phase 4 scope (additive):
#   - Re-sync the portal tree (new assets/ + status.html)
#   - Re-install the nginx config (now carries /assets/ + /api/ blocks)
#   - Reload nginx (validated)
#   - No new packages, no new services
#
# PHASE selects how far up the stack to go. Phases are cumulative: PHASE=4
# runs Phase 1, Phase 2, Phase 3, then Phase 4. Default is the highest phase
# shipped at this tag.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${PHASE:-4}"
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
    local dnsmasq_changed=0
    install_config "${REPO_DIR}/config/dnsmasq/signal.conf"   /etc/dnsmasq.d/signal.conf && dnsmasq_changed=1
    apply_country_code
    ensure_hostapd_default
    ensure_dhcpcd_block
    apply_sysctl
    apply_iptables
    install_unit

    systemctl restart dhcpcd
    systemctl start signal-ap.service
    # If dnsmasq config changed (e.g. Phase 2 wildcard line), reload so the
    # new rules are live without bouncing hostapd.
    [[ $dnsmasq_changed -eq 1 ]] && systemctl reload dnsmasq 2>/dev/null || true

    log "Phase 1 complete. Look for SSID 'SIGNAL_INFOHUB'."
    log "Status: systemctl status signal-ap"
}

# Sync a directory tree using rsync semantics (idempotent, mode-aware).
install_tree() {
    local src="$1" dst="$2"
    install -d "$dst"
    # cp -ru would skip files with newer mtimes on disk; we always want repo
    # to win, so use rsync if available, otherwise fall back to cp -a.
    if command -v rsync >/dev/null; then
        rsync -a --delete "${src}/" "${dst}/"
    else
        rm -rf "${dst:?}/"*
        cp -a "${src}/." "${dst}/"
    fi
}

ensure_nginx_site() {
    local available="/etc/nginx/sites-available/signal-portal"
    local enabled="/etc/nginx/sites-enabled/signal-portal"
    install -m 0644 "${REPO_DIR}/config/nginx/signal-portal.conf" "$available"
    [[ -L "$enabled" ]] || ln -s "$available" "$enabled"
    # Stock nginx ships a default_server that would shadow ours.
    rm -f /etc/nginx/sites-enabled/default
}

phase2() {
    log "Phase 2 — Captive portal"

    apt_install nginx

    ensure_nginx_site
    install_tree "${REPO_DIR}/www/portal" /var/www/signal-portal

    # Validate before reload so a typo doesn't take the AP offline.
    if ! nginx -t 2>/dev/null; then
        nginx -t  # re-run without quiet so the error reaches the log
        die "nginx config did not validate; aborting"
    fi
    systemctl enable nginx.service
    systemctl reload nginx.service 2>/dev/null || systemctl start nginx.service

    log "Phase 2 complete. Connect a client and the captive sheet should open."
}

phase3() {
    log "Phase 3 — Kiwix content layer"

    apt_install kiwix-tools

    install -d -m 0755 /var/lib/kiwix

    install -m 0644 "${REPO_DIR}/systemd/signal-kiwix.service" /etc/systemd/system/signal-kiwix.service
    systemctl daemon-reload
    systemctl enable signal-kiwix.service

    # Start now if any ZIMs are present; otherwise the ConditionPathExistsGlob
    # in the unit keeps it inactive. Either way, surface the state.
    if compgen -G "/var/lib/kiwix/*.zim" >/dev/null; then
        systemctl restart signal-kiwix.service
        log "signal-kiwix started; library available at http://hub.local/library/"
    else
        log "/var/lib/kiwix is empty — signal-kiwix stays inactive."
        log "Run content/fetch.sh on a workstation, then rsync into /var/lib/kiwix/."
    fi

    log "Phase 3 complete."
}

phase4() {
    log "Phase 4 — Frontend (CoreConduit landing + status page)"

    # Everything Phase 4 ships is static: an updated nginx config (carries
    # /assets/ + /api/ blocks), a richer www/portal/ tree (assets/css,
    # assets/js, assets/fonts, status.html), and the rewritten index.html.
    #
    # phase2() already installed nginx and synced the portal tree from
    # ${REPO_DIR}/www/portal. Re-running those two helpers here is the
    # cleanest way to pick up the new files: install_tree is rsync-based so
    # this is a near-no-op when nothing changed.
    ensure_nginx_site
    install_tree "${REPO_DIR}/www/portal" /var/www/signal-portal

    if ! nginx -t 2>/dev/null; then
        nginx -t  # re-run loud so the error reaches the log
        die "nginx config did not validate; aborting"
    fi
    systemctl reload nginx.service 2>/dev/null || systemctl start nginx.service

    if [[ ! -s /var/www/signal-portal/assets/fonts/exo2-700.woff2 ]]; then
        log "note: brand fonts are missing — page falls back to system fonts."
        log "      run scripts/fetch_fonts.sh on a workstation, re-bake the image."
    fi

    log "Phase 4 complete. Open http://hub.local/ on a connected client."
}

main() {
    require_root
    case "$PHASE" in
        1) phase1 ;;
        2) phase1; phase2 ;;
        3) phase1; phase2; phase3 ;;
        4) phase1; phase2; phase3; phase4 ;;
        *) die "PHASE=$PHASE not implemented yet (this tag ships Phase 4)" ;;
    esac
}

main "$@"
