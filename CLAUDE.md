# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

## Project Overview

**rpi-hub** is an Offline Survival InfoHub — a self-contained Wi-Fi
access point on a Raspberry Pi that serves a curated knowledge library,
a retrieval-grounded assistant, an ephemeral notes board, RTL-SDR radio
reception, and a Reticulum + BATMAN-adv mesh control plane — **without
any internet uplink**.

**Status: v1.3.0-phase13 shipped.** All nine original phases plus Phase 13
(GPS L1 C/A sky survey) are in the box. Software-only follow-ups through
v1.2.1 (ADS-B shield, split owner tokens, installer hardening,
notes→mesh test harness) are also included. What remains is gated on
specific hardware on a bench; see `docs/GAP_ANALYSIS.md` §1.

## Phase status (shipped sequencing 1→2→3→4→5→6→9→8→7→13)

| Tag | Phase | Scope |
|-----|-------|-------|
| `v0.1.0-phase1` | Bare AP | hostapd + dnsmasq + rpi-hub-ap.service |
| `v0.2.0-phase2` | Captive portal | nginx default-server 302 + wildcard DNS |
| `v0.3.0-phase3` | Kiwix content | rpi-hub-kiwix.service + `/library/` proxy |
| `v0.4.0-phase4` | Frontend | CoreConduit landing + status page |
| `v0.5.0-phase5` | Status API | FastAPI rpi-hub-status + bake_image.sh + MOTD |
| `v0.6.0-phase6` | RAG assistant | rpi-hub-retrieve + rpi-hub-assist + rpi-hub-llama + Ask UI |
| `v0.9.0-phase9` | Notes board + packs | rpi-hub-notes (tmpfs) + 5 regional packs + `/print/` |
| `v0.8.0-phase8` | Listen | rpi-hub-listen + SAME pipeline + alert banner + Listen UI |
| `v1.0.0`        | Mesh | rpi-hub-mesh + Ed25519 identity + peer trust UI |
| `v1.1.0`        | Post-v1.0 polish | LoRa+BATMAN scaffolds, audio fanout, ADS-B UI, mesh-propagated notes, read-only root |
| `v1.2.0`        | Mesh signing + QR | signed `/notes/publish`, `rpi-hub-mesh-keygen.service`, `/api/mesh/identity.svg` |
| `v1.2.1`        | ADS-B install gate | `scripts/detect_rtlsdr.sh`, dump1090 enabled on dongle detect, status row + live aircraft count |
| `v1.3.0-phase13` | GPS Sky Survey | `gps_sdr/` vendored engine, `GPSSweeper`, `GET/POST /api/listen/gps`, `sky.html`, `scripts/release.sh`; Polish items from v1.2.1 Unreleased folded in |

## Repository layout

```text
api/rpi_hub_status/   Phase 5 status API (exposes services block since v1.0+)
assistant/           Phase 6 (rpi_hub_retrieve, rpi_hub_assist)
indexer/             Phase 6 workstation-side ZIM → index builder
models/              Phase 6 weight fetch script (workstation only)
gps_sdr/             Phase 13 vendored GPS L1 C/A acquisition engine
listen/rpi_hub_listen/ Phase 8+13 RTL-SDR control plane + SAME parser + GPS sweeper
mesh/rpi_hub_mesh/    Phase 7 mesh control plane + Ed25519 identity
notes/rpi_hub_notes/  Phase 9A ephemeral notes board
packs/               Phase 9B regional content pack manifests
config/              hostapd, dnsmasq, dhcpcd, sysctl, nginx, motd
systemd/             one unit per service; all bind 127.0.0.1
www/portal/          landing + per-tile pages + assets (sky.html added Phase 13)
scripts/             healthcheck, factory_reset, bake_image, apply_pack, same_pipeline, release
content/             ZIM manifest + workstation fetch script
docs/                OVERVIEW.md (canonical), GAP_ANALYSIS.md, CONTENT_GUIDE.md, CROSS_OS_TEST_MATRIX.md
```

## Non-negotiable invariants

- **No data exfiltration** — the device never initiates outbound IP
  connections *at runtime*. Internet calls only happen in
  `content/fetch.sh` and `models/fetch_models.sh`, both workstation-only.
  The one on-device outbound path is `install.sh` provisioning (apt / a
  pip fallback) — that is install-time, not steady state; field devices
  should be imaged with `scripts/bake_image.sh` so they never apt-update
  in the field. Internal service clients enforce this in code: each
  refuses a non-loopback upstream unless
  `rpi_hub_ALLOW_NONLOOPBACK_UPSTREAM=1` is set.
- **No phone-home** — no telemetry, no update checks.
- **Read-only content** — the library is read-only; `rpi-hub-notes` is
  the only write path (rate-limited, ephemeral, owner-clearable).
- **Open source MIT** — model weights and ZIMs fetched separately with
  their own licenses; never bundled in the repo.
- **Capability discoverability** — every optional service surfaces its
  state in the status page (`services` block on `/api/status`) and in
  the landing-page tile probes.

## Architecture conventions (audit before changing)

- **Bookworm Pi OS Lite 64-bit, Python 3.11, legacy iptables**.
- **Every config file has a header comment**: purpose, owning systemd
  unit, phase introduced. Enforced by
  `scripts/check_config_header.py`.
- **Every systemd unit binds 127.0.0.1** — the only public listener is
  nginx on `:80`.
- **Every optional unit carries `ConditionPathExists=`** so a missing
  ZIM / model / dongle / index means *inactive*, never crash-loop.
- **Every UI tile self-disables** via a fetch probe to its own endpoint;
  Library / Status / Maps tiles render without JS.
- **All Python: ruff + black + mypy strict; pytest for tests**.
- **All shell: `set -euo pipefail`, shellcheck-clean**.
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:`.

## Build / test / deploy

```bash
# Default install (all phases through 7):
sudo ./install.sh

# Phase-scoped install (cumulative):
sudo PHASE=5 ./install.sh
sudo PHASE=all ./install.sh

# Regional pack:
sudo ./install.sh --pack=pacific-northwest

# Workstation steps for Phase 3 / 6 / 9B:
./content/fetch.sh core
./models/fetch_models.sh
python -m indexer.build_index --zim-dir /var/lib/kiwix --out ./payload/var/lib/rpi-hub/index
./scripts/apply_pack.sh pacific-northwest

# Health on a live device:
make smoke    # → scripts/healthcheck.sh
```

## Final port map

```text
80/tcp    nginx           public          landing, /library, /api/*, /print
53/udp    dnsmasq         public          wildcard DNS → 192.168.4.1
67/udp    dnsmasq         public          DHCP
8000/tcp  rpi-hub-status   127.0.0.1       /api/status
8080/tcp  kiwix-serve     127.0.0.1       /library proxy
8100/tcp  rpi-hub-retrieve 127.0.0.1       /api/retrieve
8200/tcp  rpi-hub-assist   127.0.0.1       /api/ask
8201/tcp  llama-server    127.0.0.1       embedding model
8202/tcp  llama-server    127.0.0.1       generation model
8300/tcp  rpi-hub-listen   127.0.0.1       /api/listen
8400/tcp  rpi-hub-notes    127.0.0.1       /api/notes
8500/tcp  rpi-hub-mesh     127.0.0.1       /api/mesh
```

## Known follow-ups (hardware-gated as of v1.3.0-phase13)

Every software-only follow-up has shipped. What remains is gated on
specific hardware on a bench (all tracked with file:line citations
in `docs/GAP_ANALYSIS.md` §1 and §4):

- **Phase 7.1** — LoRa data plane. Needs RAK4631 USB hat. Bridge +
  `rpi-hub-reticulum.service` scaffold present.
- **Phase 7.3** — Wi-Fi mesh data plane. Needs second USB Wi-Fi
  adapter. Bridge + `rpi-hub-batman.service` + `scripts/batman_setup.sh`
  scaffold present. Also needs `AF_NETLINK` added to `rpi-hub-mesh`
  sandbox once BATMAN attaches.
- **Phase 8.3** — WebSocket audio bridge. Needs Pi 4 + RTL-SDR for
  buffer-size tuning. `AudioFanout` producer ships.
- **Phase 8.5** — APRS scanner. Needs RTL-SDR on 144.39 MHz. Schema
  stub only.
- **Phase 13.1** — GPS hardware sweep timing + threshold tuning on the
  v4 dongle + active GPS patch antenna. Sim path verified on workstation.
- **Phase 14** — Offline stratum-1 time (u-blox + PPS + chrony). ~1 d + $15 BOM.
- **Phase 15** — Power & storage lifecycle (UPS HAT telemetry, degradation tiers). ~3–4 d.
- **Three-node mesh testbed write-up** — `docs/MESH_TESTBED.md` once
  three Pi 4/5 + LoRa hats are on the bench.

## Source-of-truth documents

- **`docs/OVERVIEW.md`** — canonical v1.3.0-phase13 system reference (purpose,
  architecture, tech stack, setup, API reference, frontend pages, ops
  runbooks, module map). Replaces the per-phase notes that used to
  live in this directory.
- **`docs/GAP_ANALYSIS.md`** — open hardware-gated work, future phases (14–16),
  and polish track. Single source of truth for the backlog.
- **`Blueprint_Overview.html`** — visual blueprint for operators (SVG
  architecture diagram, service grid, hardware tiers, port inventory).
- **`rpi-hub-wizard.html`** — interactive build checklist.
- **`CHANGELOG.md`** — per-release notes (canonical).
- **`scripts/release.sh`** — release automation: stamps CHANGELOG,
  writes VERSION, prints git commit/tag commands (introduced v1.3.0-phase13).

The per-phase `docs/PHASE_<N>.md` files were retired in the v1.2.1
docs-consolidation pass; `docs/PHASE13_GPS.md` retired at v1.3.0-phase13.
Content remains in git history at the corresponding release tags.

## When extending an existing phase

1. Read the relevant section of `docs/OVERVIEW.md` for the current
   shape of the service; check `docs/GAP_ANALYSIS.md` for known
   limits.
2. Match the existing unit-of-work pattern: service code under its
   package, systemd unit under `systemd/`, nginx route in
    `config/nginx/rpi-hub-portal.conf`, UI page under `www/portal/`, tile
   probe wired in `index.html`, install step in `install.sh`, removal
   in `uninstall.sh`, doc update, commit, tag.
3. If you introduce a new port, add it to the port map in
   `docs/OVERVIEW.md` §2 and bind only to 127.0.0.1.
4. If you add an optional capability, surface it in
    `api/rpi_hub_status/system.py:services()` so the status page reflects
   it automatically.
