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
# Phase 5 scope (additive):
#   - Install python3-fastapi + python3-uvicorn (apt; no pip)
#   - Stage api/signal_status into /opt/signal/api/
#   - Write /etc/signal/version (consumed by the status probe)
#   - Install + enable signal-status.service (uvicorn on 127.0.0.1:8000)
#   - Render config/motd/signal.motd → /etc/motd
#
# Phase 6 scope (additive, Pi 5 only):
#   - Stage assistant/ into /opt/signal/assistant/
#   - Create /var/lib/signal/{index,models}/ as data dirs
#   - Install + enable signal-retrieve.service (uvicorn on 127.0.0.1:8100)
#   - Install + enable signal-assist.service   (uvicorn on 127.0.0.1:8200)
#   - Install signal-llama.service (stays inactive until a model is staged)
#   - Refresh nginx config (carries /api/ask + /api/retrieve blocks)
#   - Refresh portal tree (carries ask.html + assets/js/ask.js)
#   No model weights or index are pulled here — those come from
#   models/fetch_models.sh and indexer/build_index.py on a workstation.
#
# Phase 7 scope (additive, Pi 4/5):
#   - apt: python3-cryptography (Ed25519 signatures)
#   - Stage mesh/ into /opt/signal/mesh/
#   - Install + enable signal-mesh.service (uvicorn on 127.0.0.1:8500)
#   - StateDirectory creates /var/lib/signal/keys (0700) for the keypair;
#     ExecStartPre generates it on first boot
#   - Refresh nginx config (carries /api/mesh/ block)
#   - Refresh portal tree (carries peers.html + peers.js)
#   No LoRa or BATMAN-adv radio daemons here — those are sub-phases 7.1
#   and 7.3 and require physical adapters + region-specific config.
#
# Phase 8 scope (additive, Pi 4/5 for full; Zero 2 W: NOAA+FM only):
#   - apt: rtl-sdr, multimon-ng (+ dump1090-mutability on Pi 4/5)
#   - Stage listen/ into /opt/signal/listen/
#   - Stage scripts/same_pipeline.sh into /opt/signal/scripts/
#   - Install + enable signal-listen.service (uvicorn on 127.0.0.1:8300)
#   - Install signal-listen-same.service (rtl_fm | multimon-ng | curl;
#     stays inactive when rtl_fm is absent or no dongle is plugged in)
#   - Refresh nginx config (carries /api/listen/ block)
#   - Refresh portal tree (carries listen.html + listen.js)
#
# Phase 9 scope (additive):
#   - Stage notes/ into /opt/signal/notes/
#   - Install + enable signal-notes.service (uvicorn on 127.0.0.1:8400)
#   - Generate /etc/signal/notes-owner-token (one-time, 32 hex chars)
#   - Refresh nginx config (carries /api/notes + /print/ blocks)
#   - Refresh portal tree (carries board.html + board.js)
#   - --pack=<name> applies a regional content pack (zims + print PDFs)
#
# PHASE selects how far up the stack to go. Phases are cumulative: PHASE=9
# runs Phase 1 through Phase 9. (Phases 7 + 8 land later; the value 9
# here means "include the 9A notes board"; we skip Phase 7 + 8 cleanly.)
# Default is the highest phase shipped at this tag.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${PHASE:-7}"
COUNTRY="${SIGNAL_COUNTRY_CODE:-US}"
PACK=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pack=*) PACK="${1#--pack=}"; shift ;;
        --pack)   PACK="${2:-}"; shift 2 ;;
        --phase=*) PHASE="${1#--phase=}"; shift ;;
        --) shift; break ;;
        *) shift ;;
    esac
done

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

resolve_version() {
    # Priority: explicit VERSION file (set by release tagging) → git describe
    # → "dev". Echoes the resolved version on stdout.
    if [[ -s "${REPO_DIR}/VERSION" ]]; then
        head -n1 "${REPO_DIR}/VERSION" | tr -d '[:space:]'
        return
    fi
    if command -v git >/dev/null && [[ -d "${REPO_DIR}/.git" ]]; then
        git -C "${REPO_DIR}" describe --tags --always 2>/dev/null && return
    fi
    echo "dev"
}

phase5() {
    log "Phase 5 — Status API + polish"

    # FastAPI/uvicorn come from apt — much faster on a Pi than pip wheels,
    # and pinned by the OS release. Our app is intentionally written to
    # the lowest-common-denominator API surface (Bookworm ships FastAPI
    # 0.92 + pydantic 1.10; that's fine for one read-only endpoint).
    apt_install python3-fastapi python3-uvicorn python3-pydantic

    # Stage the API package under /opt/signal/api so PYTHONPATH in the
    # systemd unit can find it. We avoid /usr/lib/python3.11/site-packages
    # so apt-managed paths stay clean.
    install -d -m 0755 /opt/signal/api
    install_tree "${REPO_DIR}/api" /opt/signal/api
    # Scripts directory: the MOTD references /opt/signal/scripts/*.sh.
    install -d -m 0755 /opt/signal/scripts
    install_tree "${REPO_DIR}/scripts" /opt/signal/scripts

    # /etc/signal is the runtime config dir. Currently just holds VERSION;
    # Phase 7+ will park the mesh keypair here under 0600.
    install -d -m 0755 /etc/signal
    local version
    version="$(resolve_version)"
    printf '%s\n' "${version}" >/etc/signal/version
    chmod 0644 /etc/signal/version
    log "version pinned to ${version}"

    # MOTD: substitute {{VERSION}} + {{MESH_FP}}, drop into /etc/motd.
    # PAM reads /etc/motd on shell login. Mesh fingerprint comes from the
    # public key on disk (read directly to avoid waiting on the unit to
    # bind during phase5 — phase7 will have written the key by the time
    # we're here on a v1.0 install, or the placeholder stays until next run).
    local motd_tmp mesh_fp
    motd_tmp="$(mktemp)"
    if [[ -s /var/lib/signal/keys/ed25519.pub ]]; then
        mesh_fp="$(python3 -c "
import base64, hashlib, sys
pub = open('/var/lib/signal/keys/ed25519.pub','rb').read()
h = hashlib.sha256(pub).digest()[:15]
b = base64.b32encode(h).decode('ascii').rstrip('=')
print('-'.join(b[i:i+4] for i in range(0, len(b), 4)))
" 2>/dev/null)"
    fi
    mesh_fp="${mesh_fp:-(not yet generated — run phase 7)}"
    sed -e "s|{{VERSION}}|${version}|g" \
        -e "s|{{MESH_FP}}|${mesh_fp}|g" \
        "${REPO_DIR}/config/motd/signal.motd" >"${motd_tmp}"
    install -m 0644 "${motd_tmp}" /etc/motd
    rm -f "${motd_tmp}"

    # Service unit. After install + enable, restart unconditionally so a
    # re-run picks up code changes.
    install -m 0644 "${REPO_DIR}/systemd/signal-status.service" \
        /etc/systemd/system/signal-status.service
    systemctl daemon-reload
    systemctl enable signal-status.service
    systemctl restart signal-status.service

    # Smoke test: give uvicorn ~3s to bind, then probe /api/status. Failure
    # here is non-fatal (install completed; the user can investigate via
    # journalctl) but loud.
    local i probe_ok=0
    for i in 1 2 3 4 5 6; do
        if curl --silent --fail --max-time 1 \
            http://127.0.0.1:8000/status >/dev/null 2>&1; then
            probe_ok=1
            break
        fi
        sleep 0.5
    done
    if [[ $probe_ok -eq 1 ]]; then
        log "signal-status responded on 127.0.0.1:8000 ✓"
    else
        log "warning: signal-status did not respond within 3s"
        log "         check 'journalctl -u signal-status' for details"
    fi

    log "Phase 5 complete. http://hub.local/api/status now lights up status.html."
}

phase6() {
    log "Phase 6 — RAG assistant (Pi 5 only)"

    # We do not block on hardware detection here — the unit guards
    # themselves are ConditionPathExists on model files. On a Zero 2 W
    # the user simply never stages weights and the Ask tile stays hidden.

    # Stage the assistant package alongside the api/ tree from Phase 5.
    install -d -m 0755 /opt/signal/assistant
    install_tree "${REPO_DIR}/assistant" /opt/signal/assistant

    # Runtime data dirs. These hold prebuilt index + downloaded weights;
    # both are produced on a workstation and rsynced over.
    install -d -m 0755 /var/lib/signal/index
    install -d -m 0755 /var/lib/signal/models

    # Refresh portal so ask.html + ask.js land alongside the existing tree.
    install_tree "${REPO_DIR}/www/portal" /var/www/signal-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    systemctl reload nginx.service 2>/dev/null || systemctl start nginx.service

    # Install all three units. Each one carries its own Condition guard so
    # they stay inactive until their respective data appears.
    for unit in signal-retrieve.service signal-assist.service signal-llama.service; do
        install -m 0644 "${REPO_DIR}/systemd/${unit}" "/etc/systemd/system/${unit}"
    done
    systemctl daemon-reload
    systemctl enable signal-retrieve.service signal-assist.service signal-llama.service

    # Start whatever is ready. If the index is missing the unit stays
    # inactive; we surface that to the user rather than letting it look
    # like a failure.
    if [[ -s /var/lib/signal/index/chunks.sqlite ]]; then
        systemctl restart signal-retrieve.service
        log "signal-retrieve started (index present)"
    else
        log "no index at /var/lib/signal/index — run indexer/build_index.py on a workstation."
    fi
    if [[ -s /var/lib/signal/models/qwen2.5-1.5b-instruct-q4_k_m.gguf ]]; then
        systemctl restart signal-llama.service signal-assist.service
        log "signal-assist started (model present)"
    else
        log "no model weights at /var/lib/signal/models — run models/fetch_models.sh on a workstation."
    fi

    log "Phase 6 complete. http://hub.local/ask.html lights up when both units are running."
}

phase7() {
    log "Phase 7 — Mesh control plane"

    # python3-cryptography is the Ed25519 dep. Bookworm ships it under
    # apt so we avoid pip. Without it the service falls back to a stub
    # signature path; we log loudly in that case.
    apt_install python3-cryptography

    install -d -m 0755 /opt/signal/mesh
    install_tree "${REPO_DIR}/mesh" /opt/signal/mesh

    # Refresh portal (peers.html + peers.js) and nginx route.
    install_tree "${REPO_DIR}/www/portal" /var/www/signal-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    systemctl reload nginx.service 2>/dev/null || systemctl start nginx.service

    install -m 0644 "${REPO_DIR}/systemd/signal-mesh.service" \
        /etc/systemd/system/signal-mesh.service
    systemctl daemon-reload
    systemctl enable signal-mesh.service
    systemctl restart signal-mesh.service

    # Surface the local fingerprint right after start so the operator
    # can confirm the keypair landed.
    sleep 1
    if fp=$(curl --silent --max-time 1 http://127.0.0.1:8500/identity 2>/dev/null \
              | python3 -c "import json,sys;print(json.load(sys.stdin).get('fingerprint',''))" 2>/dev/null); then
        if [[ -n "$fp" ]]; then
            log "mesh fingerprint: $fp"
        fi
    fi

    log "Phase 7 complete. http://hub.local/peers.html shows the peer list."
}

phase8() {
    log "Phase 8 — RTL-SDR Listen"

    # rtl-sdr ships /usr/bin/rtl_fm + /usr/bin/rtl_test; multimon-ng
    # decodes SAME / APRS / POCSAG. dump1090-mutability is the ADS-B
    # decoder for sub-phase 8.4 — apt-install it conditionally because
    # not every Bookworm mirror carries it.
    apt_install rtl-sdr multimon-ng
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        dump1090-mutability 2>/dev/null \
        || log "dump1090-mutability not available; ADS-B (sub-phase 8.4) will be skipped"

    install -d -m 0755 /opt/signal/listen
    install_tree "${REPO_DIR}/listen" /opt/signal/listen
    install -d -m 0755 /opt/signal/scripts
    install -m 0755 "${REPO_DIR}/scripts/same_pipeline.sh" /opt/signal/scripts/same_pipeline.sh

    install -d -m 0755 /var/lib/signal/listen

    # Refresh portal (listen.html + listen.js) and nginx route.
    install_tree "${REPO_DIR}/www/portal" /var/www/signal-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    systemctl reload nginx.service 2>/dev/null || systemctl start nginx.service

    install -m 0644 "${REPO_DIR}/systemd/signal-listen.service" \
        /etc/systemd/system/signal-listen.service
    install -m 0644 "${REPO_DIR}/systemd/signal-listen-same.service" \
        /etc/systemd/system/signal-listen-same.service
    systemctl daemon-reload
    systemctl enable signal-listen.service signal-listen-same.service
    systemctl restart signal-listen.service

    # SAME pipeline starts only if the rtl_fm binary is present (a
    # ConditionPathExists= guard inside the unit handles missing
    # dongles cleanly).
    if command -v rtl_fm >/dev/null; then
        systemctl restart signal-listen-same.service 2>/dev/null \
            || log "signal-listen-same did not start (no dongle?); check journalctl"
    fi

    log "Phase 8 complete. http://hub.local/listen.html lights up when the service is reachable."
}

ensure_owner_token() {
    # Generate a 32-hex-char token if one is not already on disk. The
    # token gates DELETE /api/notes/{id} and POST /api/notes/wipe — the
    # owner shells into the device to read it.
    local token_file="/etc/signal/notes-owner-token"
    install -d -m 0755 /etc/signal
    if [[ ! -s "$token_file" ]]; then
        # /dev/urandom + tr is universal; openssl/uuidgen aren't always
        # in Bookworm minimal images.
        tr -dc 'a-f0-9' </dev/urandom | head -c 32 >"$token_file"
        chmod 0600 "$token_file"
        log "generated owner token at $token_file (cat it as root)"
    fi
}

phase9() {
    log "Phase 9 — Notes board + regional packs"

    # Notes board service code.
    install -d -m 0755 /opt/signal/notes
    install_tree "${REPO_DIR}/notes" /opt/signal/notes

    # Owner-moderation token. One-time generation; never overwritten.
    ensure_owner_token

    # Refresh portal so board.html + board.js are served.
    install_tree "${REPO_DIR}/www/portal" /var/www/signal-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    systemctl reload nginx.service 2>/dev/null || systemctl start nginx.service

    # Service unit. The unit creates /run/signal-notes (tmpfs) via
    # RuntimeDirectory= so we don't touch fstab.
    install -m 0644 "${REPO_DIR}/systemd/signal-notes.service" \
        /etc/systemd/system/signal-notes.service
    systemctl daemon-reload
    systemctl enable signal-notes.service
    systemctl restart signal-notes.service

    # Optional pack application. The workstation produces the PDFs +
    # writes the print/ tree; we just install them here. The user passes
    # --pack=<name> the same way they passed PHASE=N.
    if [[ -n "$PACK" ]]; then
        local pack_print_src="${REPO_DIR}/packs/${PACK}/print"
        if [[ -d "$pack_print_src" ]]; then
            install_tree "$pack_print_src" /var/www/signal-portal/print
            log "applied pack=$PACK print cards"
        else
            log "pack=$PACK has no print/ directory; skipping print install"
        fi
    fi

    log "Phase 9 complete. http://hub.local/board.html serves the board."
    log "Owner token: cat /etc/signal/notes-owner-token (root only)"
}

main() {
    require_root
    case "$PHASE" in
        1) phase1 ;;
        2) phase1; phase2 ;;
        3) phase1; phase2; phase3 ;;
        4) phase1; phase2; phase3; phase4 ;;
        5) phase1; phase2; phase3; phase4; phase5 ;;
        6) phase1; phase2; phase3; phase4; phase5; phase6 ;;
        # Phase 9 ships before Phase 8 per approved sequencing (9 → 8 → 7).
        # PHASE=9 includes Phase 9 but not 8; PHASE=8 chains 9 first.
        9) phase1; phase2; phase3; phase4; phase5; phase6; phase9 ;;
        8) phase1; phase2; phase3; phase4; phase5; phase6; phase9; phase8 ;;
        7|all) phase1; phase2; phase3; phase4; phase5; phase6; phase9; phase8; phase7 ;;
        *) die "PHASE=$PHASE not implemented (1..9 or 'all'; this tag ships all phases)" ;;
    esac
}

main "$@"
