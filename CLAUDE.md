# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

## Project Overview

**SIGNAL** is an Offline Survival InfoHub — a self-contained Wi-Fi
access point on a Raspberry Pi that serves a curated knowledge library,
a retrieval-grounded assistant, an ephemeral notes board, RTL-SDR radio
reception, and a Reticulum + BATMAN-adv mesh control plane — **without
any internet uplink**.

**Status: v1.0 shipped. All nine phases landed.**

## Phase status (all shipped per the approved sequencing 1→2→3→4→5→6→9→8→7)

| Tag | Phase | Scope |
|-----|-------|-------|
| `v0.1.0-phase1` | Bare AP | hostapd + dnsmasq + signal-ap.service |
| `v0.2.0-phase2` | Captive portal | nginx default-server 302 + wildcard DNS |
| `v0.3.0-phase3` | Kiwix content | signal-kiwix.service + `/library/` proxy |
| `v0.4.0-phase4` | Frontend | CoreConduit landing + status page |
| `v0.5.0-phase5` | Status API | FastAPI signal-status + bake_image.sh + MOTD |
| `v0.6.0-phase6` | RAG assistant | signal-retrieve + signal-assist + signal-llama + Ask UI |
| `v0.9.0-phase9` | Notes board + packs | signal-notes (tmpfs) + 5 regional packs + `/print/` |
| `v0.8.0-phase8` | Listen | signal-listen + SAME pipeline + alert banner + Listen UI |
| `v1.0.0`        | Mesh | signal-mesh + Ed25519 identity + peer trust UI |

## Repository layout

```
api/signal_status/   Phase 5 status API (exposes services block since v1.0+)
assistant/           Phase 6 (signal_retrieve, signal_assist)
indexer/             Phase 6 workstation-side ZIM → index builder
models/              Phase 6 weight fetch script (workstation only)
listen/signal_listen/ Phase 8 RTL-SDR control plane + SAME parser
mesh/signal_mesh/    Phase 7 mesh control plane + Ed25519 identity
notes/signal_notes/  Phase 9A ephemeral notes board
packs/               Phase 9B regional content pack manifests
config/              hostapd, dnsmasq, dhcpcd, sysctl, nginx, motd
systemd/             one unit per service; all bind 127.0.0.1
www/portal/          landing + per-tile pages + assets
scripts/             healthcheck, factory_reset, bake_image, apply_pack, same_pipeline
content/             ZIM manifest + workstation fetch script
docs/                PHASE_1.md … PHASE_9.md, CONTENT_GUIDE, CROSS_OS_TEST_MATRIX
```

## Non-negotiable invariants

- **No data exfiltration** — the device never initiates outbound IP
  connections in production. Internet calls only happen in
  `content/fetch.sh` and `models/fetch_models.sh`, both workstation-only.
- **No phone-home** — no telemetry, no update checks.
- **Read-only content** — the library is read-only; `signal-notes` is
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
python -m indexer.build_index --zim-dir /var/lib/kiwix --out ./payload/var/lib/signal/index
./scripts/apply_pack.sh pacific-northwest

# Health on a live device:
make smoke    # → scripts/healthcheck.sh
```

## Final port map

```
80/tcp    nginx           public          landing, /library, /api/*, /print
53/udp    dnsmasq         public          wildcard DNS → 192.168.4.1
67/udp    dnsmasq         public          DHCP
8000/tcp  signal-status   127.0.0.1       /api/status
8080/tcp  kiwix-serve     127.0.0.1       /library proxy
8100/tcp  signal-retrieve 127.0.0.1       /api/retrieve
8200/tcp  signal-assist   127.0.0.1       /api/ask
8201/tcp  llama-server    127.0.0.1       embedding model
8202/tcp  llama-server    127.0.0.1       generation model
8300/tcp  signal-listen   127.0.0.1       /api/listen
8400/tcp  signal-notes    127.0.0.1       /api/notes
8500/tcp  signal-mesh     127.0.0.1       /api/mesh
```

## Known follow-ups (post-v1.0)

- **Phase 7.1–7.3**: Reticulum daemon (LoRa) + BATMAN-adv (Wi-Fi mesh)
  data planes. Control plane shipped; data planes need physical
  hardware on the bench.
- **Phase 8.3**: WebSocket audio bridge for the Listen UI.
- **Phase 8.4**: dump1090 / ADS-B UI (decoder installed, UI follow-up).
- **Phase 9.2**: mesh-propagated notes (depends on Phase 7.1–7.2).
- **v1.1**: read-only root via overlayfs.

## Source-of-truth documents

- `signal-wizard.html` — interactive checklist UI (phase scope + acceptance gates).
- `docs/PHASE_<N>.md` — per-phase implementation notes.
- `Project_SIGNAL_*.docx` — original engineering specs (Phases 1–5, 6, 7–9).

## When extending an existing phase

1. Read the phase's `docs/PHASE_<N>.md` for invariants and known limits.
2. Match the existing unit-of-work pattern: service code under its
   package, systemd unit under `systemd/`, nginx route in
   `config/nginx/signal-portal.conf`, UI page under `www/portal/`, tile
   probe wired in `index.html`, install step in `install.sh`, removal
   in `uninstall.sh`, doc update, commit, tag.
3. If you introduce a new port, add it to the port map in
   `docs/PHASE_7.md` and bind only to 127.0.0.1.
4. If you add an optional capability, surface it in
   `api/signal_status/system.py:services()` so the status page reflects
   it automatically.
