#!/usr/bin/env bash
# rpi-POD installer — Phase 1 (Bare AP).
#
# Idempotent: re-running should be a no-op if everything is already in place.
# Re-runs upgrade configs from the repo in-place; service is restarted only
# if a config actually changed.
#
# Phase 1 scope:
#   - Install hostapd, dnsmasq, iptables-persistent
#   - Link repo configs into /etc
#   - Pin wlan0 to 192.168.4.1 (dhcpcd on Bookworm; NM unmanaged on Trixie+)
#   - Apply sysctl (ip_forward=0)
#   - Apply iptables FORWARD drop on wlan0 cross-interface traffic
#   - Enable rpi-pod-ap.service
#
# Phase 2 scope (additive):
#   - Install nginx
#   - Link the rpi-pod-portal site config + landing page into /etc and /var/www
#   - Drop the stock nginx default site so it can't shadow us
#   - Reload nginx (validated with nginx -t first)
#
# Phase 3 scope (additive):
#   - Install kiwix-tools
#   - Create /var/lib/kiwix as the ZIM payload directory
#   - Install rpi-pod-kiwix.service (stays inactive until ZIMs appear)
#
# Phase 4 scope (additive):
#   - Re-sync the portal tree (new assets/ + status.html)
#   - Re-install the nginx config (now carries /assets/ + /api/ blocks)
#   - Reload nginx (validated)
#   - No new packages, no new services
#
# Phase 5 scope (additive):
#   - Install python3-fastapi + python3-uvicorn (apt; no pip)
#   - Stage api/rpi_pod_status into /opt/rpi-pod/api/
#   - Write /etc/rpi-pod/version (consumed by the status probe)
#   - Install + enable rpi-pod-status.service (uvicorn on 127.0.0.1:8000)
#   - Render config/motd/rpi-pod.motd → /etc/motd
#
# Phase 6 scope (additive, Pi 5 only):
#   - Stage assistant/ into /opt/rpi-pod/assistant/
#   - Create /var/lib/rpi-pod/{index,models}/ as data dirs
#   - Install + enable rpi-pod-retrieve.service (uvicorn on 127.0.0.1:8100)
#   - Install + enable rpi-pod-assist.service   (uvicorn on 127.0.0.1:8200)
#   - Install rpi-pod-llama.service (stays inactive until a model is staged)
#   - Refresh nginx config (carries /api/ask + /api/retrieve blocks)
#   - Refresh portal tree (carries ask.html + assets/js/ask.js)
#   No model weights or index are pulled here — those come from
#   models/fetch_models.sh and indexer/build_index.py on a workstation.
#
# Phase 7 scope (additive, Pi 4/5):
#   - apt: python3-cryptography (Ed25519 signatures)
#   - Stage mesh/ into /opt/rpi-pod/mesh/
#   - Install + enable rpi-pod-mesh.service (uvicorn on 127.0.0.1:8500)
#   - StateDirectory creates /var/lib/rpi-pod/keys (0700) for the keypair;
#     ExecStartPre generates it on first boot
#   - Refresh nginx config (carries /api/mesh/ block)
#   - Refresh portal tree (carries peers.html + peers.js)
#   No LoRa or BATMAN-adv radio daemons here — those are sub-phases 7.1
#   and 7.3 and require physical adapters + region-specific config.
#
# Phase 8 scope (additive, Pi 4/5 for full; Zero 2 W: NOAA+FM only):
#   - apt: rtl-sdr, multimon-ng (+ dump1090-mutability on Pi 4/5)
#   - Stage listen/ into /opt/rpi-pod/listen/
#   - Stage scripts/same_pipeline.sh into /opt/rpi-pod/scripts/
#   - Install + enable rpi-pod-listen.service (uvicorn on 127.0.0.1:8300)
#   - Install rpi-pod-listen-same.service (rtl_fm | multimon-ng | curl;
#     stays inactive when rtl_fm is absent or no dongle is plugged in)
#   - Refresh nginx config (carries /api/listen/ block)
#   - Refresh portal tree (carries listen.html + listen.js)
#
# Phase 9 scope (additive):
#   - Stage notes/ into /opt/rpi-pod/notes/
#   - Install + enable rpi-pod-notes.service (uvicorn on 127.0.0.1:8400)
#   - Generate /etc/rpi-pod/notes-owner-token (one-time, 32 hex chars)
#   - Refresh nginx config (carries /api/notes + /print/ blocks)
#   - Refresh portal tree (carries board.html + board.js)
#   - --pack=<name> applies a regional content pack (zims + print PDFs)
#
# PHASE selects how far up the stack to go. Phases are cumulative: PHASE=9
# runs Phase 1 through Phase 9. (Phases 7 + 8 land later; the value 9
# here means "include the 9A notes board"; we skip Phase 7 + 8 cleanly.)
# Default is the highest phase shipped at this tag.

set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${PHASE:-7}"
COUNTRY="${RPI_POD_COUNTRY_CODE:-US}"
PACK=""

log() { printf '[rpi-pod-install] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# Surface where a non-zero exit actually happened. `die` calls exit
# directly and bypasses ERR, so its own message is never duplicated here.
trap 'log "FAILED at line $LINENO (last command: ${BASH_COMMAND})"' ERR

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pack=*)  PACK="${1#--pack=}"; shift ;;
        --pack)    PACK="${2:-}"; shift 2 ;;
        --phase=*) PHASE="${1#--phase=}"; shift ;;
        --phase)   PHASE="${2:-}"; shift 2 ;;
        --)        shift; break ;;
        *)         die "unknown argument: $1 (try --phase=N, --pack=NAME)" ;;
    esac
done

if [[ -n "$PACK" && ! -d "${REPO_DIR}/packs/${PACK}" ]]; then
    die "unknown pack: '${PACK}' — no such directory at ${REPO_DIR}/packs/${PACK}"
fi

if [[ ! "$COUNTRY" =~ ^[A-Z]{2}$ ]]; then
    die "RPI_POD_COUNTRY_CODE must be ISO 3166-1 alpha-2 (got: '$COUNTRY')"
fi

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
    DEBIAN_FRONTEND=noninteractive apt-get update -qq \
        || die "apt-get update failed — check network and /etc/apt/sources.list"
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@" \
        || die "apt-get install failed for: $*"
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
    local marker_begin="# >>> rpi-POD Phase 1 (wlan0 static) >>>"
    local marker_end="# <<< rpi-POD Phase 1 (wlan0 static) <<<"
    local conf="/etc/dhcpcd.conf"
    [[ -f "$conf" ]] || die "$conf not found; is this Raspberry Pi OS?"

    if grep -qF "$marker_begin" "$conf"; then
        return 0
    fi

    {
        printf '\n%s\n' "$marker_begin"
        cat "${REPO_DIR}/config/dhcpcd/rpi-pod.conf"
        printf '%s\n' "$marker_end"
    } >>"$conf"
    log "appended rpi-POD block to $conf"
}

# On systems running NetworkManager (e.g. Debian Trixie) mark wlan0 as
# unmanaged so hostapd can take over the interface.  The static IP is
# assigned by rpi-pod-ap.service via 'ip addr add' after hostapd starts.
ensure_nm_unmanaged() {
    local conf="/etc/NetworkManager/conf.d/rpi-pod.conf"
    if [[ -f "$conf" ]] && grep -q "unmanaged-devices=interface-name:wlan0" "$conf"; then
        return 0
    fi
    install -d /etc/NetworkManager/conf.d
    cat >"$conf" <<'EOF'
# Purpose: Release wlan0 to hostapd for AP mode.
# Unit:    rpi-pod-ap.service (hostapd manages wlan0 directly)
# Phase:   1
[keyfile]
unmanaged-devices=interface-name:wlan0
EOF
    log "wrote $conf (wlan0 unmanaged by NetworkManager)"
    nmcli general reload conf 2>/dev/null \
        || systemctl reload NetworkManager 2>/dev/null \
        || true
    # Disconnect wlan0 from any existing NM connection so hostapd can claim it.
    nmcli device disconnect wlan0 2>/dev/null || true
    # NM's disconnect can leave a soft rfkill block; clear it now so hostapd
    # can initialise the radio immediately after install.
    rfkill unblock wifi 2>/dev/null || true
}

# Dispatch to whichever network manager is present.
configure_wlan0_static() {
    if systemctl is-active --quiet dhcpcd 2>/dev/null \
        || systemctl is-enabled --quiet dhcpcd 2>/dev/null; then
        ensure_dhcpcd_block
    elif systemctl is-active --quiet NetworkManager 2>/dev/null; then
        ensure_nm_unmanaged
    else
        log "warning: no supported network manager detected; wlan0 static IP must be configured manually"
    fi
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
    install_config "${REPO_DIR}/config/sysctl/rpi-pod.conf" /etc/sysctl.d/30-rpi-pod.conf || true
    sysctl --system >/dev/null
}

install_unit() {
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-ap.service" /etc/systemd/system/rpi-pod-ap.service
    systemctl daemon-reload
    systemctl enable rpi-pod-ap.service
}

phase1() {
    log "Phase 1 — Bare AP"
    require_bookworm

    # Stop cleanly before reconfiguring. Stop rpi-pod-ap first so its
    # ExecStop tears down hostapd and dnsmasq; the individual stops below
    # are belt-and-braces for the case where rpi-pod-ap never started.
    systemctl stop rpi-pod-ap.service 2>/dev/null || true
    systemctl stop hostapd dnsmasq 2>/dev/null || true
    systemctl unmask hostapd 2>/dev/null || true

    apt_install hostapd dnsmasq iptables iptables-persistent netfilter-persistent

    install_config "${REPO_DIR}/config/hostapd/hostapd.conf"  /etc/hostapd/hostapd.conf  || true
    local dnsmasq_changed=0
    install_config "${REPO_DIR}/config/dnsmasq/rpi-pod.conf"   /etc/dnsmasq.d/rpi-pod.conf && dnsmasq_changed=1
    apply_country_code
    ensure_hostapd_default
    configure_wlan0_static
    apply_sysctl
    apply_iptables
    install_unit

    # Restart dhcpcd only when it is the active network manager; NM-based
    # systems (Debian Trixie+) use ensure_nm_unmanaged instead.
    if systemctl is-active --quiet dhcpcd 2>/dev/null \
        || systemctl is-enabled --quiet dhcpcd 2>/dev/null; then
        systemctl restart dhcpcd \
            || die "dhcpcd restart failed — check 'journalctl -u dhcpcd'"
    fi
    # Use restart (not start) so re-runs re-fire ExecStartPre even if the
    # service is still "active" from RemainAfterExit.
    systemctl restart rpi-pod-ap.service \
        || die "rpi-pod-ap.service failed to start — check 'journalctl -u rpi-pod-ap' (common causes: wlan0 already managed, hostapd.conf rejected, country_code mismatch)"
    # If dnsmasq config changed (e.g. Phase 2 wildcard line), reload so the
    # new rules are live without bouncing hostapd.
    if [[ $dnsmasq_changed -eq 1 ]]; then
        systemctl reload dnsmasq 2>/dev/null \
            || log "warning: dnsmasq reload failed; restart it manually if the wildcard DNS rule isn't live"
    fi

    log "Phase 1 complete. Look for SSID 'RPI-POD-INFOHUB'."
    log "Status: systemctl status rpi-pod-ap"
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
    local available="/etc/nginx/sites-available/rpi-pod-portal"
    local enabled="/etc/nginx/sites-enabled/rpi-pod-portal"
    install -m 0644 "${REPO_DIR}/config/nginx/rpi-pod-portal.conf" "$available"
    [[ -L "$enabled" ]] || ln -s "$available" "$enabled"
    # Stock nginx ships a default_server that would shadow ours.
    rm -f /etc/nginx/sites-enabled/default
}

# Reload nginx if it is already running; otherwise start it. Surfaces the
# real reload error when reload fails (no `2>/dev/null` swallowing), so
# a perms/SELinux/operator-override issue is diagnosable from the log.
nginx_reload_or_start() {
    if systemctl is-active --quiet nginx.service; then
        systemctl reload nginx.service
    else
        systemctl start nginx.service
    fi
}

phase2() {
    log "Phase 2 — Captive portal"

    apt_install nginx

    ensure_nginx_site
    install_tree "${REPO_DIR}/www/portal" /var/www/rpi-pod-portal

    # Validate before reload so a typo doesn't take the AP offline.
    if ! nginx -t 2>/dev/null; then
        nginx -t  # re-run without quiet so the error reaches the log
        die "nginx config did not validate; aborting"
    fi
    systemctl enable nginx.service
    nginx_reload_or_start

    log "Phase 2 complete. Connect a client and the captive sheet should open."
}

phase3() {
    log "Phase 3 — Kiwix content layer"

    apt_install kiwix-tools

    install -d -m 0755 /var/lib/kiwix

    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-kiwix.service" /etc/systemd/system/rpi-pod-kiwix.service
    systemctl daemon-reload
    systemctl enable rpi-pod-kiwix.service

    # Start now if any ZIMs are present; otherwise the ConditionPathExistsGlob
    # in the unit keeps it inactive. Either way, surface the state.
    if compgen -G "/var/lib/kiwix/*.zim" >/dev/null; then
        systemctl restart rpi-pod-kiwix.service
        log "rpi-pod-kiwix started; library available at http://hub.local/library/"
    else
        log "/var/lib/kiwix is empty — rpi-pod-kiwix stays inactive."
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
    install_tree "${REPO_DIR}/www/portal" /var/www/rpi-pod-portal

    if ! nginx -t 2>/dev/null; then
        nginx -t  # re-run loud so the error reaches the log
        die "nginx config did not validate; aborting"
    fi
    nginx_reload_or_start

    if [[ ! -s /var/www/rpi-pod-portal/assets/fonts/exo2-700.woff2 ]]; then
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

    # Stage the API package under /opt/rpi-pod/api so PYTHONPATH in the
    # systemd unit can find it. We avoid /usr/lib/python3.11/site-packages
    # so apt-managed paths stay clean.
    install -d -m 0755 /opt/rpi-pod/api
    install_tree "${REPO_DIR}/api" /opt/rpi-pod/api
    # Scripts directory: the MOTD references /opt/rpi-pod/scripts/*.sh.
    install -d -m 0755 /opt/rpi-pod/scripts
    install_tree "${REPO_DIR}/scripts" /opt/rpi-pod/scripts

    # /etc/rpi-pod is the runtime config dir. Currently just holds VERSION;
    # Phase 7+ will park the mesh keypair here under 0600.
    install -d -m 0755 /etc/rpi-pod
    local version
    version="$(resolve_version)"
    printf '%s\n' "${version}" >/etc/rpi-pod/version
    chmod 0644 /etc/rpi-pod/version
    log "version pinned to ${version}"

    # MOTD: substitute {{VERSION}} + {{MESH_FP}}, drop into /etc/motd.
    # PAM reads /etc/motd on shell login. Mesh fingerprint comes from the
    # public key on disk (read directly to avoid waiting on the unit to
    # bind during phase5 — phase7 will have written the key by the time
    # we're here on a v1.0 install, or the placeholder stays until next run).
    local motd_tmp mesh_fp
    motd_tmp="$(mktemp)"
    if [[ -s /var/lib/rpi-pod/keys/ed25519.pub ]]; then
        mesh_fp="$(python3 -c "
import base64, hashlib, sys
pub = open('/var/lib/rpi-pod/keys/ed25519.pub','rb').read()
h = hashlib.sha256(pub).digest()[:15]
b = base64.b32encode(h).decode('ascii').rstrip('=')
print('-'.join(b[i:i+4] for i in range(0, len(b), 4)))
" 2>/dev/null)"
    fi
    mesh_fp="${mesh_fp:-(not yet generated — run phase 7)}"
    sed -e "s|{{VERSION}}|${version}|g" \
        -e "s|{{MESH_FP}}|${mesh_fp}|g" \
        "${REPO_DIR}/config/motd/rpi-pod.motd" >"${motd_tmp}"
    install -m 0644 "${motd_tmp}" /etc/motd
    rm -f "${motd_tmp}"

    # Service unit. After install + enable, restart unconditionally so a
    # re-run picks up code changes.
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-status.service" \
        /etc/systemd/system/rpi-pod-status.service
    systemctl daemon-reload
    systemctl enable rpi-pod-status.service
    systemctl restart rpi-pod-status.service

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
        log "rpi-pod-status responded on 127.0.0.1:8000 ✓"
    else
        log "warning: rpi-pod-status did not respond within 3s"
        log "         check 'journalctl -u rpi-pod-status' for details"
    fi

    log "Phase 5 complete. http://hub.local/api/status now lights up status.html."
}

phase6() {
    log "Phase 6 — RAG assistant (Pi 5 only)"

    # We do not block on hardware detection here — the unit guards
    # themselves are ConditionPathExists on model files. On a Zero 2 W
    # the user simply never stages weights and the Ask tile stays hidden.

    # Stage the assistant package alongside the api/ tree from Phase 5.
    install -d -m 0755 /opt/rpi-pod/assistant
    install_tree "${REPO_DIR}/assistant" /opt/rpi-pod/assistant

    # Runtime data dirs. These hold prebuilt index + downloaded weights;
    # both are produced on a workstation and rsynced over.
    install -d -m 0755 /var/lib/rpi-pod/index
    install -d -m 0755 /var/lib/rpi-pod/models

    # Refresh portal so ask.html + ask.js land alongside the existing tree.
    install_tree "${REPO_DIR}/www/portal" /var/www/rpi-pod-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    nginx_reload_or_start

    # Install all three units. Each one carries its own Condition guard so
    # they stay inactive until their respective data appears.
    for unit in rpi-pod-retrieve.service rpi-pod-assist.service rpi-pod-llama.service; do
        install -m 0644 "${REPO_DIR}/systemd/${unit}" "/etc/systemd/system/${unit}"
    done
    systemctl daemon-reload
    systemctl enable rpi-pod-retrieve.service rpi-pod-assist.service rpi-pod-llama.service

    # Start whatever is ready. If the index is missing the unit stays
    # inactive; we surface that to the user rather than letting it look
    # like a failure.
    if [[ -s /var/lib/rpi-pod/index/chunks.sqlite ]]; then
        systemctl restart rpi-pod-retrieve.service
        log "rpi-pod-retrieve started (index present)"
    else
        log "no index at /var/lib/rpi-pod/index — run indexer/build_index.py on a workstation."
    fi
    if [[ -s /var/lib/rpi-pod/models/qwen2.5-1.5b-instruct-q4_k_m.gguf ]]; then
        systemctl restart rpi-pod-llama.service rpi-pod-assist.service
        log "rpi-pod-assist started (model present)"
    else
        log "no model weights at /var/lib/rpi-pod/models — run models/fetch_models.sh on a workstation."
    fi

    log "Phase 6 complete. http://hub.local/ask.html lights up when both units are running."
}

phase7() {
    log "Phase 7 — Mesh control plane"

    # python3-cryptography is the Ed25519 dep. Bookworm ships it under
    # apt so we avoid pip. Without it the service falls back to a stub
    # signature path; we log loudly in that case.
    apt_install python3-cryptography

    install -d -m 0755 /opt/rpi-pod/mesh
    install_tree "${REPO_DIR}/mesh" /opt/rpi-pod/mesh

    # Refresh portal (peers.html + peers.js) and nginx route.
    install_tree "${REPO_DIR}/www/portal" /var/www/rpi-pod-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    nginx_reload_or_start

    # v1.2: split keypair provisioning out into its own oneshot, so the
    # long-running daemon can pick up the bytes via LoadCredential= and
    # drop filesystem access to /var/lib/rpi-pod/keys entirely.
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-mesh-keygen.service" \
        /etc/systemd/system/rpi-pod-mesh-keygen.service
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-mesh.service" \
        /etc/systemd/system/rpi-pod-mesh.service
    systemctl daemon-reload
    systemctl enable rpi-pod-mesh-keygen.service rpi-pod-mesh.service
    # Keygen first, then the daemon; the latter Requires= the former so
    # restart in this order is also what systemd would have done.
    systemctl restart rpi-pod-mesh-keygen.service
    systemctl restart rpi-pod-mesh.service

    # Surface the local fingerprint right after start so the operator
    # can confirm the keypair landed. 6×0.5s mirrors phase 5's status
    # probe — Pi Zero 2 W can take >1s for keygen + mesh bind.
    local i fp=""
    for i in 1 2 3 4 5 6; do
        fp=$(curl --silent --max-time 1 http://127.0.0.1:8500/identity 2>/dev/null \
              | python3 -c "import json,sys;print(json.load(sys.stdin).get('fingerprint',''))" 2>/dev/null || true)
        [[ -n "$fp" ]] && break
        sleep 0.5
    done
    if [[ -n "$fp" ]]; then
        log "mesh fingerprint: $fp"
    else
        log "warning: rpi-pod-mesh did not surface a fingerprint within 3s"
        log "         check 'journalctl -u rpi-pod-mesh-keygen' and 'journalctl -u rpi-pod-mesh'"
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

    install -d -m 0755 /opt/rpi-pod/listen
    install_tree "${REPO_DIR}/listen" /opt/rpi-pod/listen
    install -d -m 0755 /opt/rpi-pod/scripts
    install -m 0755 "${REPO_DIR}/scripts/same_pipeline.sh" /opt/rpi-pod/scripts/same_pipeline.sh

    install -d -m 0755 /var/lib/rpi-pod/listen

    # Refresh portal (listen.html + listen.js) and nginx route.
    install_tree "${REPO_DIR}/www/portal" /var/www/rpi-pod-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    nginx_reload_or_start

    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-listen.service" \
        /etc/systemd/system/rpi-pod-listen.service
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-listen-same.service" \
        /etc/systemd/system/rpi-pod-listen-same.service
    systemctl daemon-reload
    systemctl enable rpi-pod-listen.service rpi-pod-listen-same.service
    systemctl restart rpi-pod-listen.service

    # SAME pipeline starts only if the rtl_fm binary is present (a
    # ConditionPathExists= guard inside the unit handles missing
    # dongles cleanly).
    if command -v rtl_fm >/dev/null; then
        systemctl restart rpi-pod-listen-same.service 2>/dev/null \
            || log "rpi-pod-listen-same did not start (no dongle?); check journalctl"
    fi

    phase8_adsb
    phase8_adsb_shield

    log "Phase 8 complete. http://hub.local/listen.html lights up when the service is reachable."
}

phase8_adsb() {
    # Phase 8.4 — gate dump1090-mutability on a real dongle being present.
    #
    # Mutually exclusive with rpi-pod-listen-same — a single RTL-SDR dongle
    # is claimed by whichever service starts first. See docs/OVERVIEW.md §7.4.
    #
    # The package install above is unconditional (cheap; ~250 KB), so an
    # operator who plugs in a dongle later can flip the service on with
    # `systemctl enable --now dump1090-mutability` and the config we
    # dropped below will pick up automatically.
    #
    # Why detect at install time rather than relying on the systemd
    # ConditionPathExists= pattern we use for rpi-pod-listen-same: the
    # upstream dump1090-mutability.service ships with
    # START_DUMP1090="no" baked into /etc/default, so the unit refuses
    # to do anything until we write our drop-in. That drop-in only
    # makes sense once we've decided we *want* ADS-B running.

    # Always install the /etc/default file; without it the package's
    # own defaults (START=no, no JSON output) would leave the unit
    # quietly inert even if a dongle shows up later.
    if dpkg -s dump1090-mutability >/dev/null 2>&1; then
        install -m 0644 "${REPO_DIR}/config/dump1090/dump1090-mutability.default" \
            /etc/default/dump1090-mutability
    else
        log "dump1090-mutability package absent; sub-phase 8.4 will stay dormant."
        return 0
    fi

    # Detector lives at scripts/detect_rtlsdr.sh — exit 0 iff a known
    # RTL2832U-based dongle is on the USB bus right now.
    if "${REPO_DIR}/scripts/detect_rtlsdr.sh" >/dev/null 2>&1; then
        systemctl daemon-reload
        systemctl enable dump1090-mutability.service 2>/dev/null || true
        systemctl restart dump1090-mutability.service 2>/dev/null \
            || log "dump1090-mutability failed to start; check journalctl -u dump1090-mutability"
        log "Phase 8.4 — RTL-SDR dongle detected; dump1090-mutability enabled."
        log "    aircraft.json lands at /run/dump1090-mutability/, served at /adsb/"
        log "    rpi-pod-status probes that file's mtime+contents (see api/rpi_pod_status/system.py:_probe_adsb)"
    else
        # Leave the unit disabled so it does not race rpi-pod-listen-same
        # for the same single-dongle setup. Operator can opt in later.
        systemctl disable dump1090-mutability.service 2>/dev/null || true
        log "Phase 8.4 — no RTL-SDR dongle detected; dump1090-mutability stays disabled."
        log "    Plug a dongle in and run: sudo systemctl enable --now dump1090-mutability"
    fi
}

phase8_adsb_shield() {
    # Opt-in position-rounder — independent of whether dump1090-mutability
    # is installed. Both the service and timer carry
    # ConditionPathExists=/etc/rpi-pod/adsb-precision, so this is dormant
    # until the operator creates that file. We `enable --now` the timer
    # unconditionally; the condition-check makes the actual ticking opt-in.
    #
    # This must NOT live inside phase8_adsb(): that function has an early
    # return when dump1090-mutability is absent, which would silently skip
    # a privacy primitive that is decoder-independent.
    install -d -m 0755 /opt/rpi-pod/scripts
    install -m 0755 "${REPO_DIR}/scripts/adsb_shield.py" /opt/rpi-pod/scripts/adsb_shield.py
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-adsb-shield.service" \
        /etc/systemd/system/rpi-pod-adsb-shield.service
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-adsb-shield.timer" \
        /etc/systemd/system/rpi-pod-adsb-shield.timer
    systemctl daemon-reload
    systemctl enable --now rpi-pod-adsb-shield.timer 2>/dev/null \
        || log "warning: rpi-pod-adsb-shield.timer enable failed (the timer itself should always enable; the rounding job is the opt-in via /etc/rpi-pod/adsb-precision)"
    log "Phase 8.4 polish — adsb-shield timer installed (opt in: echo 1 >/etc/rpi-pod/adsb-precision)"
}

ensure_owner_tokens() {
    # Generate 32-hex-char tokens for the two trust domains if they are
    # not already on disk. The notes token gates DELETE /api/notes/{id}
    # and POST /api/notes/wipe; the mesh token gates POST
    # /api/mesh/peers/{fp}/{trust,block}. The owner shells into the
    # device to read each one.
    #
    # rpi-pod-mesh falls back to notes-owner-token when mesh-owner-token
    # is absent (pre-v1.3 deployments stay single-token until the
    # operator chooses to split).
    install -d -m 0755 /etc/rpi-pod
    local f
    for f in /etc/rpi-pod/notes-owner-token /etc/rpi-pod/mesh-owner-token; do
        if [[ ! -s "$f" ]]; then
            # /dev/urandom + tr is universal; openssl/uuidgen aren't always
            # in Bookworm minimal images.
            # Subshell absorbs tr's SIGPIPE when head closes the pipe early
            # (would otherwise trigger set -o pipefail and abort).
            (tr -dc 'a-f0-9' </dev/urandom || true) | head -c 32 >"$f"
            chmod 0600 "$f"
            log "generated owner token at $f (cat it as root)"
        fi
    done
}

phase9() {
    log "Phase 9 — Notes board + regional packs"

    # Notes board service code.
    install -d -m 0755 /opt/rpi-pod/notes
    install_tree "${REPO_DIR}/notes" /opt/rpi-pod/notes

    # Owner-moderation tokens (notes + mesh). One-time generation; never overwritten.
    ensure_owner_tokens

    # Refresh portal so board.html + board.js are served.
    install_tree "${REPO_DIR}/www/portal" /var/www/rpi-pod-portal
    ensure_nginx_site
    if ! nginx -t 2>/dev/null; then
        nginx -t
        die "nginx config did not validate; aborting"
    fi
    nginx_reload_or_start

    # Service unit. The unit creates /run/rpi-pod-notes (tmpfs) via
    # RuntimeDirectory= so we don't touch fstab.
    install -m 0644 "${REPO_DIR}/systemd/rpi-pod-notes.service" \
        /etc/systemd/system/rpi-pod-notes.service
    systemctl daemon-reload
    systemctl enable rpi-pod-notes.service
    systemctl restart rpi-pod-notes.service

    # Optional pack application. The workstation produces the PDFs +
    # writes the print/ tree; we just install them here. The user passes
    # --pack=<name> the same way they passed PHASE=N.
    if [[ -n "$PACK" ]]; then
        local pack_print_src="${REPO_DIR}/packs/${PACK}/print"
        if [[ -d "$pack_print_src" ]]; then
            install_tree "$pack_print_src" /var/www/rpi-pod-portal/print
            log "applied pack=$PACK print cards"
        else
            log "pack=$PACK has no print/ directory; skipping print install"
        fi
    fi

    log "Phase 9 complete. http://hub.local/board.html serves the board."
    log "Owner tokens: cat /etc/rpi-pod/notes-owner-token (notes moderation)"
    log "               cat /etc/rpi-pod/mesh-owner-token  (mesh peer trust/block)"
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
