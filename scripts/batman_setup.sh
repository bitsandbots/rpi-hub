#!/usr/bin/env bash
# Purpose: BATMAN-adv interface setup / teardown. Driven by
#          rpi-pod-batman.service (ExecStart/ExecStop).
# Unit:    rpi-pod-batman.service
# Phase:   7.3
#
# Reads /etc/rpi-pod/mesh.conf for:
#   MESH_IFACE   — wireless interface to add to bat0 (e.g. wlan1)
#   MESH_SSID    — IBSS / mesh-point SSID (mesh-only, never broadcast as AP)
#   MESH_CHANNEL — non-overlapping channel from the client AP
#   MESH_BAT_IF  — virtual bat0 interface name (default: bat0)
#
# Idempotent: re-running `up` over an already-up mesh is a no-op.

set -euo pipefail

CONF=/etc/rpi-pod/mesh.conf
[[ -r "$CONF" ]] || { echo "[batman] missing $CONF" >&2; exit 1; }
# shellcheck disable=SC1090
. "$CONF"

MESH_IFACE="${MESH_IFACE:-wlan1}"
MESH_SSID="${MESH_SSID:-rpi-pod-mesh}"
MESH_CHANNEL="${MESH_CHANNEL:-11}"
MESH_BAT_IF="${MESH_BAT_IF:-bat0}"

log() { printf '[batman] %s\n' "$*" >&2; }

require() { command -v "$1" >/dev/null || { log "missing $1"; exit 1; }; }
require batctl
require alfred
require iw
require ip

up() {
    log "loading batman-adv kernel module"
    modprobe batman-adv 2>/dev/null || log "module already loaded"

    log "configuring $MESH_IFACE → IBSS @ channel $MESH_CHANNEL SSID=$MESH_SSID"
    ip link set "$MESH_IFACE" down 2>/dev/null || true
    iw "$MESH_IFACE" set type ibss 2>/dev/null || true
    ip link set "$MESH_IFACE" mtu 1532 || true
    ip link set "$MESH_IFACE" up
    iw "$MESH_IFACE" ibss join "$MESH_SSID" "$(channel_to_freq "$MESH_CHANNEL")" || true

    log "attaching $MESH_IFACE to $MESH_BAT_IF"
    batctl if add "$MESH_IFACE" 2>/dev/null || log "already attached"
    ip link set "$MESH_BAT_IF" up

    log "starting alfred (-i $MESH_BAT_IF)"
    # alfred runs as a daemon; -d backgrounds it. The service uses
    # Type=forking so this is what RemainAfterExit tracks.
    alfred -i "$MESH_BAT_IF" -d -m -u /run/alfred.sock 2>/dev/null || log "alfred already running"

    log "mesh up: $MESH_BAT_IF (member: $MESH_IFACE)"
}

down() {
    log "stopping alfred"
    pkill -TERM -x alfred 2>/dev/null || true

    log "detaching $MESH_IFACE from $MESH_BAT_IF"
    batctl if del "$MESH_IFACE" 2>/dev/null || true
    ip link set "$MESH_BAT_IF" down 2>/dev/null || true

    log "leaving IBSS on $MESH_IFACE"
    iw "$MESH_IFACE" ibss leave 2>/dev/null || true
    ip link set "$MESH_IFACE" down 2>/dev/null || true

    log "mesh down"
}

# Translate a 2.4 GHz channel number to a MHz frequency. We only set up
# IBSS on 2.4 GHz because most cheap USB Wi-Fi adapters lack 5 GHz
# regulatory ack.
channel_to_freq() {
    local ch="$1"
    case "$ch" in
        1)  echo 2412 ;;  2)  echo 2417 ;;  3)  echo 2422 ;;
        4)  echo 2427 ;;  5)  echo 2432 ;;  6)  echo 2437 ;;
        7)  echo 2442 ;;  8)  echo 2447 ;;  9)  echo 2452 ;;
        10) echo 2457 ;; 11) echo 2462 ;; 12) echo 2467 ;;
        13) echo 2472 ;;
        *)  log "unsupported channel: $ch"; echo 2462 ;;
    esac
}

case "${1:-up}" in
    up)   up ;;
    down) down ;;
    *)    log "usage: $0 {up|down}"; exit 2 ;;
esac
