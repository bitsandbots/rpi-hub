#!/usr/bin/env bash
# rpi-hub — image bake.
#
# Produces a flashable rpi-hub-vX.Y.Z-arm64.img.xz from a Raspberry Pi OS
# Lite Bookworm base, with install.sh already applied so the SD card boots
# straight into a working hub.
#
# Workflow:
#   1. Download the base RPi OS Lite arm64 image (pinned URL + sha256).
#   2. Decompress to a working .img.
#   3. losetup loop devices for the boot + root partitions.
#   4. Mount, copy this repo into /opt/rpi-hub, drop a qemu-user-static
#      binary in if host arch != aarch64.
#   5. chroot in, run install.sh.
#   6. Clean up the chroot (remove qemu binary, clear apt cache, zerofree).
#   7. Unmount, detach loop, xz-compress the result.
#   8. Output rpi-hub-${VERSION}-${VARIANT}-arm64.img.xz alongside its sha256.
#
# Requirements (Linux only):
#   - root (loop mounts, chroot)
#   - losetup, kpartx (or sfdisk + losetup -P), mount, umount
#   - qemu-user-static + binfmt-support  (cross-arch chroot from x86_64)
#   - xz-utils, curl, sha256sum
#   - rsync
#
# macOS / WSL2 are NOT supported by this script. Use a Linux VM or do the
# bake on the Pi itself (`PHASE=5 ./install.sh` on a fresh card).
#
# Usage:
#   sudo ./scripts/bake_image.sh                     # bake, default variant
#   sudo ./scripts/bake_image.sh --dry-run           # show plan only
#   sudo ./scripts/bake_image.sh --variant zero2w    # tagging-only metadata
#   sudo ./scripts/bake_image.sh --keep-mounts       # debug: leave the chroot
#   sudo ./scripts/bake_image.sh --skip-download     # reuse cached base img

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- configuration -----------------------------------------------------------

# Pinned base image. Update both fields together when bumping versions.
# Source: https://downloads.raspberrypi.com/raspios_lite_arm64/images/
BASE_IMAGE_URL="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-11-19/2024-11-19-raspios-bookworm-arm64-lite.img.xz"
BASE_IMAGE_SHA256="ae6b75e3c4d9d3a39a5cb7c1c9b78b35bdcabb6c5e72d6e9c12d2d6f9a8d2e58"  # placeholder — replace with actual after first run
BASE_IMAGE_FILE="${REPO_DIR}/.bake-cache/$(basename "$BASE_IMAGE_URL")"

# Output naming.
VERSION="$(git -C "$REPO_DIR" describe --tags --always 2>/dev/null || echo "dev")"
VARIANT="generic"

# Mount points (under a per-run scratch dir for safe cleanup).
SCRATCH_DIR=""

# CLI flags.
DRY_RUN=0
KEEP_MOUNTS=0
SKIP_DOWNLOAD=0

log() { printf '[rpi-hub-bake] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^#\s\?//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)        DRY_RUN=1; shift ;;
        --keep-mounts)    KEEP_MOUNTS=1; shift ;;
        --skip-download)  SKIP_DOWNLOAD=1; shift ;;
        --variant)        VARIANT="$2"; shift 2 ;;
        -h|--help)        usage 0 ;;
        *)                log "unknown arg: $1"; usage 2 ;;
    esac
done

[[ $EUID -eq 0 ]] || die "must run as root (try: sudo $0)"

# --- prerequisite checks -----------------------------------------------------

need() { command -v "$1" >/dev/null 2>&1 || die "missing tool: $1"; }
for t in curl xz losetup mount umount sha256sum rsync; do need "$t"; done

HOST_ARCH="$(uname -m)"
NEEDS_QEMU=0
if [[ "$HOST_ARCH" != "aarch64" ]]; then
    NEEDS_QEMU=1
    need qemu-aarch64-static || true  # not all distros expose the symlink
    [[ -x /usr/bin/qemu-aarch64-static ]] || die "qemu-aarch64-static not found (apt install qemu-user-static binfmt-support)"
fi

# --- cleanup trap ------------------------------------------------------------

cleanup() {
    local rc=$?
    if [[ $KEEP_MOUNTS -eq 1 && -n "$SCRATCH_DIR" ]]; then
        log "leaving mounts in place at $SCRATCH_DIR (--keep-mounts)"
        return $rc
    fi
    if [[ -n "$SCRATCH_DIR" && -d "$SCRATCH_DIR" ]]; then
        local mnt="$SCRATCH_DIR/mnt"
        # Reverse order matters: boot is bind-mounted under root.
        umount -lf "$mnt/boot/firmware" 2>/dev/null || true
        umount -lf "$mnt/sys" 2>/dev/null || true
        umount -lf "$mnt/proc" 2>/dev/null || true
        umount -lf "$mnt/dev/pts" 2>/dev/null || true
        umount -lf "$mnt/dev" 2>/dev/null || true
        umount -lf "$mnt" 2>/dev/null || true
        if [[ -n "${LOOP_DEV:-}" ]]; then
            losetup -d "$LOOP_DEV" 2>/dev/null || true
        fi
        rm -rf "$SCRATCH_DIR"
    fi
    return $rc
}
trap cleanup EXIT INT TERM

# --- step 1: fetch base image ------------------------------------------------

fetch_base() {
    install -d "$(dirname "$BASE_IMAGE_FILE")"
    if [[ -f "$BASE_IMAGE_FILE" && $SKIP_DOWNLOAD -eq 1 ]]; then
        log "reusing cached $BASE_IMAGE_FILE"
        return
    fi
    if [[ ! -f "$BASE_IMAGE_FILE" ]]; then
        log "downloading $BASE_IMAGE_URL"
        curl --fail --location --progress-bar -o "$BASE_IMAGE_FILE" "$BASE_IMAGE_URL"
    fi
    if [[ "$BASE_IMAGE_SHA256" != "placeholder"* ]]; then
        log "verifying sha256"
        echo "$BASE_IMAGE_SHA256  $BASE_IMAGE_FILE" | sha256sum --check --status \
            || die "base image sha256 mismatch — refusing to bake"
    else
        log "WARNING: BASE_IMAGE_SHA256 is a placeholder; pin it after first known-good run"
        log "  observed sha256: $(sha256sum "$BASE_IMAGE_FILE" | awk '{print $1}')"
    fi
}

# --- step 2: decompress to working img --------------------------------------

decompress() {
    SCRATCH_DIR="$(mktemp -d /tmp/rpi-hub-bake.XXXXXX)"
    log "scratch dir: $SCRATCH_DIR"
    local img="$SCRATCH_DIR/working.img"
    log "decompressing to $img"
    xz --decompress --keep --stdout "$BASE_IMAGE_FILE" >"$img"
    echo "$img"
}

# --- step 3: loop-mount + chroot --------------------------------------------

mount_image() {
    local img="$1" mnt="$SCRATCH_DIR/mnt"

    log "losetup -P $img"
    LOOP_DEV="$(losetup --show -fP "$img")"
    log "loop device: $LOOP_DEV"

    install -d "$mnt"
    # RPi OS images: p1 = /boot/firmware (FAT32), p2 = / (ext4)
    mount "${LOOP_DEV}p2" "$mnt"
    install -d "$mnt/boot/firmware"
    mount "${LOOP_DEV}p1" "$mnt/boot/firmware"

    mount --bind /dev "$mnt/dev"
    mount --bind /dev/pts "$mnt/dev/pts"
    mount -t proc proc "$mnt/proc"
    mount -t sysfs sys "$mnt/sys"
    log "image mounted at $mnt"
}

stage_repo() {
    local mnt="$SCRATCH_DIR/mnt"
    log "staging repo to /opt/rpi-hub inside chroot"
    install -d "$mnt/opt/rpi-hub"
    rsync -a --delete \
        --exclude='.git' --exclude='.bake-cache' --exclude='__pycache__' \
        "$REPO_DIR/" "$mnt/opt/rpi-hub/"

    if [[ $NEEDS_QEMU -eq 1 ]]; then
        log "installing qemu-aarch64-static into chroot"
        install -m 0755 /usr/bin/qemu-aarch64-static "$mnt/usr/bin/qemu-aarch64-static"
    fi

    # Pre-seed the version file so the API picks it up on first boot.
    install -d "$mnt/etc/rpi-hub"
    printf '%s\n' "$VERSION" >"$mnt/etc/rpi-hub/version"
}

run_install_in_chroot() {
    local mnt="$SCRATCH_DIR/mnt"
    log "running install.sh inside chroot (this is the slow step)"
    chroot "$mnt" /bin/bash -lc '
        set -e
        cd /opt/rpi-hub
        export DEBIAN_FRONTEND=noninteractive
        PHASE=5 ./install.sh
        apt-get clean
        rm -rf /var/lib/apt/lists/*
    '
}

finalize_chroot() {
    local mnt="$SCRATCH_DIR/mnt"
    if [[ $NEEDS_QEMU -eq 1 ]]; then
        rm -f "$mnt/usr/bin/qemu-aarch64-static"
    fi
    # Zero machine-id so each cloned SD card gets a fresh one on first boot.
    : >"$mnt/etc/machine-id"
    log "chroot finalized"
}

# --- step 4: re-compress and output -----------------------------------------

compress_output() {
    local img="$1"
    local out_dir="$REPO_DIR/dist"
    install -d "$out_dir"
    local out_name="rpi-hub-${VERSION}-${VARIANT}-arm64.img.xz"
    local out_path="$out_dir/$out_name"
    log "compressing → $out_path"
    xz --threads=0 --compress --keep --stdout "$img" >"$out_path"
    sha256sum "$out_path" | tee "$out_path.sha256"
    log "DONE → $out_path"
}

# --- main --------------------------------------------------------------------

if [[ $DRY_RUN -eq 1 ]]; then
    log "DRY RUN. Plan:"
    log "  1. fetch $BASE_IMAGE_URL → $BASE_IMAGE_FILE"
    log "  2. decompress to scratch dir"
    log "  3. losetup -P + mount p1+p2"
    log "  4. rsync repo → /opt/rpi-hub in chroot"
    log "  5. install qemu-aarch64-static into chroot (host=$HOST_ARCH, needs_qemu=$NEEDS_QEMU)"
    log "  6. chroot + PHASE=5 install.sh + apt-get clean"
    log "  7. zero /etc/machine-id, remove qemu binary"
    log "  8. unmount, losetup -d"
    log "  9. xz-compress → dist/rpi-hub-${VERSION}-${VARIANT}-arm64.img.xz"
    exit 0
fi

fetch_base
img="$(decompress)"
mount_image "$img"
stage_repo
run_install_in_chroot
finalize_chroot

# Unmount before compression so the filesystem image is consistent.
KEEP_MOUNTS_PREV=$KEEP_MOUNTS
KEEP_MOUNTS=0
cleanup_partial() {
    local mnt="$SCRATCH_DIR/mnt"
    umount -lf "$mnt/boot/firmware" 2>/dev/null || true
    umount -lf "$mnt/sys" 2>/dev/null || true
    umount -lf "$mnt/proc" 2>/dev/null || true
    umount -lf "$mnt/dev/pts" 2>/dev/null || true
    umount -lf "$mnt/dev" 2>/dev/null || true
    umount -lf "$mnt" 2>/dev/null || true
    losetup -d "$LOOP_DEV" 2>/dev/null || true
    LOOP_DEV=""
}
cleanup_partial
KEEP_MOUNTS=$KEEP_MOUNTS_PREV

compress_output "$img"
