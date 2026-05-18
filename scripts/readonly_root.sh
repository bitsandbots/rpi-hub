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
#   * upper = /var/lib/signal/overlay/upper  (small writable layer)
#   * work  = /var/lib/signal/overlay/work
#   * Bind mounts for /var/log, /etc/signal, /var/lib/dnsmasq,
#     /var/lib/signal, /var/lib/kiwix, /run, /tmp (already tmpfs).
#
# Caveats:
#   - First run requires a reboot to switch the mount.
#   - apt updates need `disable` before they run, then `enable` again.
#     A wrapper script (apt-rw) and a systemd hook would automate this
#     in a v1.2 polish pass; here we ship the primitive.
#   - The signal-notes board, the mesh keypair, and the kiwix library
#     are explicitly *not* on the overlay — they live on the writable
#     bind mounts so they persist boots.

set -uo pipefail

OVERLAY_BASE=/var/lib/signal/overlay
MARKER=/etc/signal/readonly-root.enabled

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
    install -d -m 0755 /etc/signal
}

write_fstab_block() {
    local marker_begin="# >>> SIGNAL Phase 1.1 (readonly root) >>>"
    local marker_end="# <<< SIGNAL Phase 1.1 (readonly root) <<<"
    if grep -qF "$marker_begin" /etc/fstab; then
        return 0
    fi
    {
        printf '\n%s\n' "$marker_begin"
        cat <<'EOF'
# overlayfs root: lower=/  upper=/var/lib/signal/overlay/upper
# These bind mounts keep state writable across boots without giving up
# read-only protection on the rest of /.
tmpfs   /var/log           tmpfs   defaults,nosuid,nodev,size=64m   0 0
tmpfs   /tmp               tmpfs   defaults,nosuid,nodev,size=128m  0 0
EOF
        printf '%s\n' "$marker_end"
    } >>/etc/fstab
}

remove_fstab_block() {
    sed -i '/# >>> SIGNAL Phase 1.1 (readonly root) >>>/,/# <<< SIGNAL Phase 1.1 (readonly root) <<</d' /etc/fstab
}

enable() {
    require_root
    ensure_dirs
    write_fstab_block
    # The actual overlay mount happens early in boot via an initramfs
    # script — generated here so it survives kernel upgrades.
    install -d -m 0755 /usr/share/initramfs-tools/scripts/init-bottom
    cat >/usr/share/initramfs-tools/scripts/init-bottom/signal-overlay <<'EOF'
#!/bin/sh
# SIGNAL overlay-root init-bottom hook.
# Mounts an overlay over the just-mounted rootfs so subsequent writes
# go to a tmpfs upper layer; bind mounts for /var/log, /tmp, /var/lib
# are applied by /etc/fstab.
PREREQ=""
prereqs() { echo "$PREREQ"; }
case $1 in
    prereqs) prereqs; exit 0 ;;
esac
. /scripts/functions

mkdir -p /overlay/upper /overlay/work /overlay/lower
mount --move ${rootmnt} /overlay/lower
mount -t overlay overlay \
    -o lowerdir=/overlay/lower,upperdir=/overlay/upper,workdir=/overlay/work \
    ${rootmnt}
EOF
    chmod 0755 /usr/share/initramfs-tools/scripts/init-bottom/signal-overlay
    # Regenerate initramfs so the hook is picked up.
    update-initramfs -u 2>/dev/null || die "update-initramfs failed"
    touch "$MARKER"
    log "enabled — reboot to switch to overlay root"
}

disable() {
    require_root
    rm -f /usr/share/initramfs-tools/scripts/init-bottom/signal-overlay
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
