#!/usr/bin/env bash
# Purpose: Enable / disable a read-only rootfs with overlayfs, per the
#          v1.1 design from the original build plan. Writable areas are
#          carved out as bind mounts onto a small persistent partition
#          (or tmpfs) so logs, leases, captive-portal state, and the
#          notes-board's owner token survive boots while the rest of /
#          stays immutable.
# Unit:    n/a (operator-run on a quiescent system; reboot required)
# Phase:   v1.1
#
# Usage:
#   sudo ./scripts/readonly_root.sh enable      # converts to overlay root
#   sudo ./scripts/readonly_root.sh disable     # reverts to rw root
#   sudo ./scripts/readonly_root.sh status      # show current mode
#
# Design:
#   * lower = /  (read-only after enabling)
#   * upper = /var/lib/rpi-hub/overlay/upper  (small writable layer)
#   * work  = /var/lib/rpi-hub/overlay/work
#   * Bind mounts for /var/log, /etc/rpi-hub, /var/lib/dnsmasq,
#     /var/lib/rpi-hub, /var/lib/kiwix, /run, /tmp (already tmpfs).
#
# Caveats:
#   - First run requires a reboot to switch the mount.
#   - apt updates need `disable` before they run, then `enable` again.
#     A wrapper script (apt-rw) and a systemd hook would automate this
#     in a v1.2 polish pass; here we ship the primitive.
#   - The rpi-hub-notes board, the mesh keypair, and the kiwix library
#     are explicitly *not* on the overlay — they live on the writable
#     bind mounts so they persist boots.

set -euo pipefail  # -e: enable/disable subcommands must not silently fail mid-run

OVERLAY_BASE=/var/lib/rpi-hub/overlay
MARKER=/etc/rpi-hub/readonly-root.enabled

log() { printf '[ro-root] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

require_root() { [[ $EUID -eq 0 ]] || die "must run as root"; }

current_mode() {
    if findmnt -n -o FSTYPE / 2>/dev/null | grep -q overlay; then
        echo "overlay"
    elif findmnt -n -o OPTIONS / 2>/dev/null | grep -q '^ro\|,ro,\|,ro$'; then
        echo "ro"
    else
        echo "rw"
    fi
}

ensure_dirs() {
    install -d -m 0755 "${OVERLAY_BASE}/upper"
    install -d -m 0700 "${OVERLAY_BASE}/work"
    install -d -m 0755 /etc/rpi-hub
}

# State directories that MUST persist across boots even though / is an
# overlay with a volatile (tmpfs) upper. Each is bind-mounted in the
# initramfs hook directly from the persistent lower disk, bypassing the
# overlay — so the mesh Ed25519 keypair, the notes/mesh owner tokens, the
# DHCP leases, and the kiwix library all survive a reboot. WITHOUT these
# binds, enabling overlay root regenerates the mesh identity every boot
# (breaking peer trust) and rotates the owner tokens.
PERSIST_PATHS=(
    /etc/rpi-hub          # owner tokens, adsb-precision, config
    /var/lib/rpi-hub      # mesh keypair (keys/), index, models
    /var/lib/dnsmasq      # DHCP lease database
    /var/lib/kiwix        # ZIM library (read-mostly, but large)
)

write_fstab_block() {
    local marker_begin="# >>> rpi-hub Phase 1.1 (readonly root) >>>"
    local marker_end="# <<< rpi-hub Phase 1.1 (readonly root) <<<"
    if grep -qF "$marker_begin" /etc/fstab; then
        return 0
    fi
    {
        printf '\n%s\n' "$marker_begin"
        cat <<'EOF'
# overlayfs root: lower=/ (persistent, ro)  upper=tmpfs (volatile)
# Volatile scratch: logs and /tmp reset every boot (that's the point of a
# read-only root). Persistent STATE is bind-mounted from the lower disk by
# the initramfs hook (see PERSIST_PATHS in readonly_root.sh) so the mesh
# keypair, owner tokens, DHCP leases, and the kiwix library survive boots.
tmpfs   /var/log           tmpfs   defaults,nosuid,nodev,size=64m   0 0
tmpfs   /tmp               tmpfs   defaults,nosuid,nodev,size=128m  0 0
EOF
        printf '%s\n' "$marker_end"
    } >>/etc/fstab
}

remove_fstab_block() {
    sed -i '/# >>> rpi-hub Phase 1.1 (readonly root) >>>/,/# <<< rpi-hub Phase 1.1 (readonly root) <<</d' /etc/fstab
}

enable() {
    require_root
    ensure_dirs
    write_fstab_block
    # The actual overlay mount happens early in boot via an initramfs
    # script — generated here so it survives kernel upgrades.
    install -d -m 0755 /usr/share/initramfs-tools/scripts/init-bottom
    # The persistent bind list is baked into the hook so it survives kernel
    # upgrades. Generated from PERSIST_PATHS so the two never drift.
    local persist_lines=""
    local p
    for p in "${PERSIST_PATHS[@]}"; do
        persist_lines+="bind_persist ${p}"$'\n'
    done
    cat >/usr/share/initramfs-tools/scripts/init-bottom/rpi-hub-overlay <<EOF
#!/bin/sh
# rpi-hub overlay-root init-bottom hook.
# Mounts an overlay over the just-mounted rootfs: the lower is the real,
# persistent disk (read-only); the upper is a VOLATILE tmpfs, so ordinary
# root writes reset every boot. Specific STATE directories are then
# bind-mounted straight from the persistent lower (bypassing the overlay)
# so the mesh keypair, owner tokens, DHCP leases, and the kiwix library
# survive reboots. /var/log and /tmp are tmpfs via /etc/fstab.
PREREQ=""
prereqs() { echo "\$PREREQ"; }
case \$1 in
    prereqs) prereqs; exit 0 ;;
esac
. /scripts/functions

mkdir -p /overlay/upper /overlay/work /overlay/lower
# Bounded, volatile upper so root writes can't exhaust RAM.
mount -t tmpfs -o size=128m,mode=0755 tmpfs /overlay/upper
mkdir -p /overlay/upper/data /overlay/upper/work
mount --move \${rootmnt} /overlay/lower
mount -t overlay overlay \\
    -o lowerdir=/overlay/lower,upperdir=/overlay/upper/data,workdir=/overlay/upper/work \\
    \${rootmnt}

# Re-expose persistent state from the lower disk (read-write) over the
# overlay so it is NOT volatile. The lower is the real rootfs, so writes
# here hit the SD card and persist.
bind_persist() {
    [ -d "/overlay/lower\$1" ] || mkdir -p "/overlay/lower\$1"
    mkdir -p "\${rootmnt}\$1"
    mount --bind "/overlay/lower\$1" "\${rootmnt}\$1"
}
${persist_lines}
EOF
    chmod 0755 /usr/share/initramfs-tools/scripts/init-bottom/rpi-hub-overlay
    # Regenerate initramfs so the hook is picked up.
    update-initramfs -u 2>/dev/null || die "update-initramfs failed"
    touch "$MARKER"
    log "enabled — reboot to switch to overlay root"
}

disable() {
    require_root
    rm -f /usr/share/initramfs-tools/scripts/init-bottom/rpi-hub-overlay
    remove_fstab_block
    update-initramfs -u 2>/dev/null || die "update-initramfs failed"
    rm -f "$MARKER"
    log "disabled — reboot to return to writable root"
}

status() {
    local mode marker
    mode="$(current_mode)"
    marker=$([[ -f "$MARKER" ]] && echo "enabled" || echo "disabled")
    printf 'overlay marker : %s\n' "$marker"
    printf 'current root   : %s\n' "$mode"
    printf 'upper          : %s\n' "$OVERLAY_BASE/upper"
    if [[ -d "$OVERLAY_BASE/upper" ]]; then
        printf 'upper size     : %s\n' "$(du -sh "$OVERLAY_BASE/upper" 2>/dev/null | cut -f1)"
    fi
}

case "${1:-status}" in
    enable)  enable ;;
    disable) disable ;;
    status)  status ;;
    *)       die "usage: $0 {enable|disable|status}" ;;
esac
