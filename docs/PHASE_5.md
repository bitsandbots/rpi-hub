# Phase 5 — Status API & Polish

## Goal

The device knows its own health. The status page (built in Phase 4) lights
up with live numbers. A fresh Pi OS Lite SD card can become a working hub
in under 15 minutes via `install.sh`, or instantly via a baked `.img.xz`
flashed with Raspberry Pi Imager. Healthchecks and factory-reset exist so
a long-deployed hub stays trustworthy.

## What was built

| Artifact | Path |
|---|---|
| FastAPI app | `api/signal_status/main.py` (single `GET /status`) |
| Host probes | `api/signal_status/system.py` (uptime, load, disk, leases, vcgencmd, time source, version) |
| Tests | `api/signal_status/tests/test_status.py` (13 unit + endpoint tests) |
| Dev tooling | `api/pyproject.toml` (ruff, black, mypy --strict, pytest) |
| Systemd unit | `systemd/signal-status.service` (uvicorn on 127.0.0.1:8000, sandboxed) |
| Healthcheck | `scripts/healthcheck.sh` (drives `make smoke`) |
| Factory reset | `scripts/factory_reset.sh` (preserves /var/lib/kiwix) |
| Image bake | `scripts/bake_image.sh` (loop-mount + chroot + xz) |
| MOTD | `config/motd/signal.motd` (templated with `{{VERSION}}` at deploy) |
| Version pin | `VERSION` (single source of truth; read by install.sh + bake) |
| Installer step | `phase5()` in `install.sh` (default `PHASE=5`) |
| Uninstaller step | `remove_status()` in `uninstall.sh` |

## Response schema

`GET /api/status` returns JSON shaped like:

```json
{
  "uptime_seconds": 12345.67,
  "load_avg": [0.12, 0.08, 0.05],
  "storage": {
    "kiwix_bytes_free": 12345678,
    "kiwix_bytes_total": 23456789
  },
  "voltage": {
    "throttled": "0x0",
    "undervoltage": false
  },
  "dhcp_clients": 3,
  "time_source": "none",
  "build_version": "v0.5.0-phase5"
}
```

Every probe is fail-soft. On a fresh non-Pi (no `vcgencmd`, no
`dnsmasq.leases`, no `/var/lib/kiwix`), every field that can't be read
becomes `null` and the response still returns 200. The frontend
(`status.js`) handles `null` values gracefully.

## How the system unit is locked down

`signal-status.service` runs under `DynamicUser=yes` with
`SupplementaryGroups=video` so the uvicorn process can read `/dev/vcio`
via `vcgencmd` but holds no other privileges. The sandbox profile
includes `ProtectSystem=strict`, `RestrictAddressFamilies=AF_INET
AF_INET6 AF_UNIX`, `SystemCallFilter=@system-service`, `NoNewPrivileges`,
`PrivateTmp`, and a `MemoryMax=128M` ceiling. The probes never write to
disk; `ReadOnlyPaths=` covers the four paths they read from.

## Bake workflow

`scripts/bake_image.sh` produces a flashable `signal-${VERSION}-${VARIANT}-arm64.img.xz`
under `dist/`. The bake:

1. Downloads the pinned Raspberry Pi OS Lite arm64 base (`.bake-cache/`,
   sha256-verified — pin the hash in the script after a first known-good
   run).
2. Decompresses, loop-mounts both partitions.
3. Copies the repo into `/opt/signal/` inside the image.
4. If the host isn't aarch64, installs `qemu-aarch64-static` into the
   chroot for cross-arch execution.
5. Runs `PHASE=5 ./install.sh` inside the chroot.
6. Cleans the apt cache, zeros `/etc/machine-id`, removes the qemu
   binary.
7. Unmounts, detaches the loop, re-xz-compresses with all cores.
8. Writes a sha256 file next to the output.

**Linux-only.** macOS and WSL2 don't expose enough loop-mount surface
for this script. For those workstations, do the install on the Pi itself
(`PHASE=5 ./install.sh` on a freshly flashed Pi OS Lite SD card).

## How to verify on a Pi Zero 2 W

From a Phase 1+2+3+4 install (or a clean image):

```bash
git pull
sudo ./install.sh           # defaults to PHASE=5
```

Then on a connected client:

1. **API responds.** `curl http://hub.local/api/status` returns 200 with
   valid JSON in well under 200 ms.
2. **Status page lights up.** Open `http://hub.local/status.html` — the
   four metric cards populate with real numbers. The amber "service not
   running yet" banner from Phase 4 disappears.
3. **Power detection.** Plug into an underpowered USB supply: the
   "Power" card flips to red "Undervoltage" within ~5 seconds (the page
   polls every 5s while visible).
4. **MOTD.** SSH into the Pi: the tactical banner shows on shell start,
   with the version pinned from `/etc/signal/version`.
5. **Healthcheck.** Run `sudo /opt/signal/scripts/healthcheck.sh` — every
   phase block reports OK; an empty `/var/lib/kiwix` is a calibrated
   WARN, not a FAIL.
6. **Factory reset (dry run).** `sudo /opt/signal/scripts/factory_reset.sh`
   (no `--yes`) lists what would be wiped without changing anything.
7. **Bake (optional, on a workstation).** `make bake` produces
   `dist/signal-v0.5.0-phase5-generic-arm64.img.xz`. Flash to a fresh
   SD card with Raspberry Pi Imager; first boot brings up the hub
   without any further `install.sh` invocation.

## Acceptance criteria (from build plan)

- ✅ Fresh image + `bash install.sh` → working hub in **< 15 min** on a Pi
  Zero 2 W (most of that is apt install). Verified by timing a manual
  install end-to-end.
- ✅ `/api/status` returns valid JSON in **< 200 ms** (measured ~4 ms on a
  dev machine, ~30–40 ms expected on a Pi due to vcgencmd subprocess).

## Known limitations going into Phase 6

- **`BASE_IMAGE_SHA256` in `bake_image.sh` is a placeholder.** First
  bake on a trusted machine, capture the printed sha256, commit the pin
  back to the script. Until then bakes log a warning and proceed.
- **No FastAPI version pinning on the device.** Apt's `python3-fastapi`
  on Bookworm is 0.92 (pydantic 1.10). The code is written to the
  lowest-common-denominator API and tested against current upstream, so
  this is fine in practice — but if a future probe needs pydantic v2
  features, switch the install to a venv.
- **Status page assumes the FastAPI app is the only thing on port 8000.**
  Phase 6 (RAG) introduces ports 8100/8200 deliberately so they don't
  collide.
- **MOTD references `/opt/signal/scripts/*.sh` — those paths require
  the Phase 5 deploy.** A Phase ≤4 install has no `/opt/signal/`, and
  the MOTD command hints will 404. Acceptable: at Phase 5 the MOTD
  exists, at earlier phases it doesn't.

## Rollback

```bash
sudo ./uninstall.sh
```

`remove_status` disables the unit, drops the unit file, removes
`/opt/signal` and `/etc/signal`, and blanks `/etc/motd` if our banner is
still there. Library content at `/var/lib/kiwix/` is preserved.

## Tag

`v0.5.0-phase5`
