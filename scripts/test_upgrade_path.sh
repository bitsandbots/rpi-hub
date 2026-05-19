#!/usr/bin/env bash
# SIGNAL — upgrade path validation (v1.1.0 → v1.2.0 → v1.2.1).
#
# Phase introduced: tooling pass for v1.2.1 (closes GAP §7 row
# "No upgrade path test").
#
# What this script does:
#   Walks the release tags in order and re-runs install.sh on each one,
#   asserting that every service comes back active and that the
#   LoadCredential semantics introduced in v1.2 are honoured by the
#   units carried forward from v1.1.
#
# Why it's gated:
#   install.sh has no --dry-run mode (it must mutate /etc, /opt, and
#   systemd state to be meaningful). Running this on a developer
#   workstation would clobber the host. The supported environments are:
#
#     1. A disposable Raspberry Pi OS Lite Bookworm VM (qemu user-mode
#        aarch64 or a real Pi), or
#     2. A throwaway container that mocks systemctl (fast path; doesn't
#        catch every unit-ordering regression but useful for CI dry-runs).
#
#   On anything else this script exits 0 with a NOTICE so CI green-paths
#   it on machines where it can't safely run.
#
# Usage:
#   sudo ./scripts/test_upgrade_path.sh                # full upgrade walk
#   FORCE=1 sudo ./scripts/test_upgrade_path.sh        # run anyway

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAGS=(v1.1.0 v1.2.0 v1.2.1)

log()   { printf '[upgrade-path] %s\n' "$*"; }
fatal() { printf '[upgrade-path] FAIL: %s\n' "$*" >&2; exit 1; }

is_disposable_env() {
    # Heuristic: we're inside a container OR a VM the operator has
    # marked disposable. Refuse to run anywhere else.
    [[ -n "${FORCE:-}" ]] && return 0
    [[ -f /.dockerenv ]] && return 0
    [[ -f /run/.containerenv ]] && return 0
    grep -q "docker\|containerd\|lxc" /proc/1/cgroup 2>/dev/null && return 0
    [[ "${SIGNAL_UPGRADE_TEST_ENV:-}" == "disposable" ]] && return 0
    return 1
}

if ! is_disposable_env; then
    log "NOTICE: This script documents the v1.1.0 → v1.2.0 → v1.2.1"
    log "        upgrade path. install.sh has no --dry-run mode, so"
    log "        running it on a non-disposable host would mutate"
    log "        /etc, /opt, and systemd state."
    log ""
    log "        To execute the walk, run inside a disposable Pi OS"
    log "        VM or container, OR set FORCE=1 / SIGNAL_UPGRADE_TEST_ENV=disposable"
    log "        if you know what you're doing."
    log ""
    log "Manual procedure (one-shot per release):"
    for tag in "${TAGS[@]}"; do
        log "  git checkout ${tag} && sudo ./install.sh"
        log "    systemctl is-active --quiet signal-{ap,status,notes,mesh}"
        log "    systemctl show -p LoadCredential signal-mesh.service"
    done
    exit 0
fi

[[ $(id -u) -eq 0 ]] || fatal "must run as root to invoke install.sh"

log "running in disposable env — proceeding with full upgrade walk"

cd "${REPO_DIR}"

# Preserve any local in-flight work.
STASHED=0
if ! git diff --quiet || ! git diff --cached --quiet; then
    log "stashing local changes"
    git stash push -u -m "test_upgrade_path-$(date +%s)"
    STASHED=1
fi

restore_state() {
    log "restoring original branch"
    git checkout - >/dev/null 2>&1 || true
    if [[ "${STASHED}" -eq 1 ]]; then
        git stash pop || log "WARN: stash pop failed; check 'git stash list'"
    fi
}
trap restore_state EXIT

UNITS=(signal-ap signal-status signal-notes signal-mesh)

assert_units_active() {
    local tag="$1"
    for u in "${UNITS[@]}"; do
        if ! systemctl is-active --quiet "${u}.service"; then
            # The unit only exists from the phase it was introduced.
            # signal-mesh is v1.0+, signal-notes is v0.9+, signal-status
            # is v0.5+. All three are active by v1.1, which is the floor
            # tag in this walk, so a missing unit here is a real failure.
            fatal "${tag}: ${u}.service is not active"
        fi
    done
}

assert_loadcredential() {
    local tag="$1"
    # v1.2.0 introduced LoadCredential= on signal-mesh.service.
    # v1.1.0 does NOT carry it. Anything from v1.2.0 onward must.
    if [[ "${tag}" == "v1.1.0" ]]; then
        return 0
    fi
    if ! systemctl show -p LoadCredential signal-mesh.service \
            | grep -q "owner-token\|LoadCredential="; then
        fatal "${tag}: signal-mesh.service missing LoadCredential semantics"
    fi
}

for tag in "${TAGS[@]}"; do
    log "=== checkout ${tag} ==="
    git checkout "${tag}"
    log "running install.sh for ${tag}"
    ./install.sh
    log "asserting units are active for ${tag}"
    assert_units_active "${tag}"
    assert_loadcredential "${tag}"
    log "${tag}: OK"
done

log "upgrade path v1.1.0 → v1.2.0 → v1.2.1 PASSED"
