#!/usr/bin/env bash
# rpi-hub — factory reset.
#
# Wipes mutable state on the hub:
#   - DHCP leases (clients re-acquire on reconnect)
#   - nginx access/error logs
#   - systemd journal (vacuum to 0)
#   - /var/lib/rpi-hub/* (notes board state, Phase 9)
#
# *Preserves*:
#   - /var/lib/kiwix (re-downloading tens of GB is not a "reset")
#   - /etc configs (the build defines them, not local edits)
#   - /opt/rpi-hub (the deployed code)
#
# Requires --yes to actually run. Without it, just lists what would be wiped.

set -euo pipefail

CONFIRM="${1:-}"

log() { printf '[rpi-hub-reset] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

[[ $EUID -eq 0 ]] || die "must run as root (try: sudo $0 --yes)"

dry_run=1
if [[ "$CONFIRM" == "--yes" ]]; then
    dry_run=0
fi

if [[ $dry_run -eq 1 ]]; then
    log "DRY RUN. Pass --yes to actually reset."
fi

# Each target is (description, action). Action is the command to run on --yes.
do_step() {
    local desc="$1"; shift
    if [[ $dry_run -eq 1 ]]; then
        log "would: $desc"
    else
        log "doing: $desc"
        "$@"
    fi
}

# 1. DHCP leases. Truncate, then SIGHUP dnsmasq so it re-reads.
# shellcheck disable=SC2016  # single-quoted on purpose: $f is the child
# bash -c's own loop variable, not meant to expand in this outer shell.
do_step "truncate dnsmasq leases" \
    bash -c 'for f in /var/lib/misc/dnsmasq.leases /var/lib/dnsmasq/dnsmasq.leases; do
                 [[ -f "$f" ]] && : >"$f"
             done; true'

# 2. nginx logs. Truncate rather than delete so logrotate's open handles
#    keep working without a restart.
do_step "truncate nginx logs" \
    bash -c ': >/var/log/nginx/rpi-hub-portal.access.log 2>/dev/null
             : >/var/log/nginx/rpi-hub-portal.error.log 2>/dev/null
             true'

# 3. systemd journal vacuum.
do_step "vacuum systemd journal" \
    journalctl --rotate --vacuum-time=1s --quiet

# 4. rpi-hub state directory (Phase 9 notes, future scratch).
do_step "wipe /var/lib/rpi-hub/* (preserves dir, removes contents)" \
    bash -c 'if [[ -d /var/lib/rpi-hub ]]; then
                 find /var/lib/rpi-hub -mindepth 1 -delete
             fi'

if [[ $dry_run -eq 0 ]]; then
    # Bounce stateful services so they pick up the wiped state.
    systemctl reload dnsmasq 2>/dev/null || systemctl restart dnsmasq 2>/dev/null || true
    log "done. Library at /var/lib/kiwix and configs preserved."
else
    log "no changes made. Re-run with --yes to apply."
fi
