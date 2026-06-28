# rpi-hub — System Overview

Status: **v1.3.0-phase13 shipped.** This document supersedes the per-phase
`PHASE_<N>.md` notes and the `V1.x.md` release deltas that used to live
in this directory. Git history retains every word of those files at
the corresponding release tags.

---

## 1. What rpi-hub is

rpi-hub is an **Offline Survival InfoHub** — a self-contained
Wi-Fi access point on a Raspberry Pi that serves:

- a curated knowledge library (Kiwix),
- a retrieval-grounded assistant on Pi 5 (RAG over the library),
- an ephemeral community notes board,
- RTL-SDR radio reception (NOAA SAME, FM, ham band markers, ADS-B),
- a Reticulum + BATMAN-adv mesh control plane between hubs,

…**without any internet uplink**, with **no telemetry**, and with
**no transmit capability**. The device hands out DHCP leases on an
open SSID, drops every outbound packet, and serves a single public
listener on port 80.

### Design invariants

These are non-negotiable. If a change would violate one, push back on
the requirement instead of shipping the change.

| Invariant | Enforcement point |
|---|---|
| No outbound IP in production | iptables `FORWARD … DROP`; `ip_forward=0` in sysctl |
| No phone-home, no telemetry | No outbound HTTP from any service; verified at install time |
| Read-only content | Kiwix serves over a read-only mount; notes board is the *only* write path |
| Receive-only radio | `rpi-hub-listen` exposes tuning + decode; no transmit code path exists |
| Captive-portal friendly | Wildcard DNS + nginx default-server `302` to landing |
| Capability discoverability | Every optional service has a probe endpoint; tiles self-disable |
| Open source (MIT) | Repo MIT; ZIM + model weights carry their own licenses, fetched separately |

### Hardware tiers

| Tier | Board | Storage | Capabilities |
|---|---|---|---|
| **Minimal** | Pi Zero 2 W | 16 GB SD | AP + portal + small Kiwix library, NOAA + FM Listen |
| **Standard** | Pi 4 (4 GB+) | 64 GB SD or USB | + Notes board, Mesh control plane, full Listen incl. ADS-B |
| **Full** | Pi 5 (4 GB+) | NVMe or fast 256 GB SD | + RAG assistant (Qwen2.5 1.5B + bge-small) |

Additional kit:
- **RTL-SDR Blog v3/v4** (Phase 8 — receive only; v3/v4 required for hardware bias tee)
- **Active GPS patch antenna** (~$12, built-in LNA) (Phase 13 — GPS sky survey; powered via dongle bias tee; requires clear sky view)
- **RAK4631** USB LoRa hat (Phase 7.1 — mesh data plane, scaffold only)
- **Second USB Wi-Fi adapter** on a non-overlapping channel (Phase 7.3 — BATMAN-adv mesh)

> **Pi Zero 2 W + GPS sweep**: the 32-PRN × 41-Doppler-bin FFT correlation is too CPU-heavy for the Zero's single core. Files install on all tiers; the sweep self-disables on the Zero via the `/api/listen/gps` probe returning `dongle_present: false` under load. Use a Pi 4/5 for GPS sky survey.

---

## 2. Architecture

### Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│  client phone / laptop                                              │
│    │   joins open SSID  RPI-HUB-INFOHUB                              │
│    │   gets DHCP 192.168.4.10–250                                   │
│    │   wildcard DNS resolves * → 192.168.4.1                        │
│    ▼                                                                │
│  ┌──────────────────── Raspberry Pi (192.168.4.1) ──────────────┐   │
│  │                                                              │   │
│  │  ┌── hostapd (AP) ──┐  ┌── dnsmasq (DNS + DHCP) ──┐          │   │
│  │  │  open SSID       │  │  wildcard *→192.168.4.1 │          │   │
│  │  └──────────────────┘  └─────────────────────────┘          │   │
│  │                                                              │   │
│  │  ┌────────────────── nginx :80 (only public listener) ─────┐ │   │
│  │  │  /            → static landing                          │ │   │
│  │  │  /library/    → kiwix-serve :8080                       │ │   │
│  │  │  /api/status  → rpi-hub-status :8000                     │ │   │
│  │  │  /api/retrieve→ rpi-hub-retrieve :8100                   │ │   │
│  │  │  /api/ask     → rpi-hub-assist  :8200                    │ │   │
│  │  │  /api/listen/ → rpi-hub-listen  :8300                    │ │   │
│  │  │  /api/notes   → rpi-hub-notes   :8400                    │ │   │
│  │  │  /api/mesh/   → rpi-hub-mesh    :8500                    │ │   │
│  │  │  /adsb/       → /run/dump1090-mutability/ (static)      │ │   │
│  │  │  /print/      → /var/www/rpi-hub-portal/print/ (static)  │ │   │
│  │  │  *  (host-mismatch) → 302 /                             │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │                                                              │   │
│  │  ┌── kiwix-serve ──┐ ┌── rpi-hub-status ──┐ ┌── rpi-hub-notes ┐│   │
│  │  │  127.0.0.1:8080 │ │  127.0.0.1:8000   │ │  127.0.0.1:8400││   │
│  │  └─────────────────┘ └───────────────────┘ └────────────────┘│   │
│  │                                                              │   │
│  │  ┌── rpi-hub-retrieve :8100 ─┐  ┌── rpi-hub-listen :8300 ─┐    │   │
│  │  │  BM25 + HNSW + RRF       │  │  Dongle arbiter        │    │   │
│  │  └──────────────────────────┘  └────┬───────────────────┘    │   │
│  │            │  retrieve                │ spawns                │   │
│  │  ┌── rpi-hub-assist :8200 ──┐         ▼                       │   │
│  │  │  Safety → Prompt → LLM  │  ┌── rpi-hub-listen-same ─┐      │   │
│  │  │  → Citation validate     │  │ rtl_fm|multimon-ng| │      │   │
│  │  └──────────┬──────────────┘  │ curl SAME→/internal  │      │   │
│  │             │  llama-server   └───────────────────────┘      │   │
│  │  ┌── rpi-hub-llama :8201,:8202 ─┐                             │   │
│  │  │  Qwen2.5-1.5B + bge-small   │                             │   │
│  │  └─────────────────────────────┘                             │   │
│  │                                                              │   │
│  │  ┌── rpi-hub-mesh :8500 ─────────────────────────────┐        │   │
│  │  │  Identity (Ed25519, LoadCredential)              │        │   │
│  │  │  PeerTable (replay-protected)                    │        │   │
│  │  │  Signed envelopes                                │        │   │
│  │  │  /identity.svg (QR)                              │        │   │
│  │  └────┬──────────────────────┬──────────────────────┘        │   │
│  │       │                      │                                │   │
│  │  ┌── rpi-hub-mesh-keygen ┐   │                                │   │
│  │  │ oneshot, generates    │   │ lazy attach                    │   │
 │  │  │ /var/lib/rpi-hub/keys/  │   ▼                                │   │
│  │  └───────────────────────┘   ┌── rpi-hub-reticulum (scaffold) ┐│   │

│  │                              ┌── rpi-hub-batman (scaffold) ───┐│   │
│  │                              │  BATMAN-adv on usb-wlan       ││   │
│  │                              └───────────────────────────────┘│   │
│  │                                                              │   │
│  │  ┌── dump1090-mutability ─┐ (Phase 8.4, gated on dongle)    │   │
│  │  │  writes aircraft.json   │                                  │   │
│  │  │  → /run/dump1090-…/     │                                  │   │
│  │  └─────────────────────────┘                                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Service interaction patterns

- **Tile probes**: every optional service has a probe endpoint; the
  landing page hides its tile when the probe fails. See §5 for the
  per-page endpoint list.
- **Notes → mesh fan-out**: a successful `POST /api/notes` triggers
   a loopback call to `rpi-hub-mesh`'s `/notes/publish` so the envelope
  is signed and queued on whatever radio bridges are alive. Best-effort:
  a hub with no mesh hardware silently keeps notes local.
- **Status API as central health surface**: `/api/status` polls every
  per-service `/health` (or, for ADS-B, the JSON file's mtime) and
  surfaces a unified `services` block.
- **GPS sweep child**: `POST /api/listen/gps/sweep` spawns
  `python3 -m gps_sdr --once --json` as a finite child under
  `rpi-hub-listen`'s cgroup (mode `"gps"` in the Tuner arbiter).
  No new port or nginx route — `/api/listen/` prefix proxy covers it.

### Final port map

```
80/tcp    nginx                  public      landing, /library, /api/*, /adsb, /print
53/udp    dnsmasq                public      wildcard DNS → 192.168.4.1
67/udp    dnsmasq                public      DHCP
8000/tcp  rpi-hub-status          127.0.0.1   /api/status

8100/tcp  rpi-hub-retrieve        127.0.0.1   /api/retrieve

8200/tcp  rpi-hub-assist          127.0.0.1   /api/ask

8300/tcp  rpi-hub-listen          127.0.0.1   /api/listen

8400/tcp  rpi-hub-notes           127.0.0.1   /api/notes

8500/tcp  rpi-hub-mesh            127.0.0.1   /api/mesh
```

Every internal service binds 127.0.0.1 only. The public surface is
always nginx on `:80`.

---

## 3. Tech stack

| Layer | Choice | Version | Why |
|---|---|---|---|
| OS | Raspberry Pi OS Lite 64-bit | Bookworm | Long-term Debian base, kernel + firmware compatibility on Pi Zero 2 W through Pi 5 |
| Language | Python | 3.11 | Bookworm system Python; no venv needed for services |
| Web framework | FastAPI | Bookworm system pkg (0.92) | Type-driven endpoints, OpenAPI-free runtime, async ready |
| ASGI server | uvicorn | Bookworm system pkg | Slim, works under `DynamicUser=` sandboxing |
| AP daemon | hostapd | Bookworm | Standard Linux AP stack |
| DNS/DHCP | dnsmasq | Bookworm | Wildcard DNS rules + DHCP in one binary |
| Reverse proxy | nginx | Bookworm | Only public listener; default-server captures host-mismatch probes |
| Library server | kiwix-tools (kiwix-serve) | Bookworm | Native ZIM serving, no transcoding |
| Crypto | python3-cryptography | Bookworm system pkg (43.0) | Ed25519 sign/verify |
| LLM runtime | llama.cpp (built from source) | pinned to commit in `models/fetch_models.sh` | CPU-only inference on Pi 5 |
| Indexer | sentence-transformers + hnswlib + libzim | Workstation only | Build artefact rsynced to device |
| Linting | ruff, black, mypy `--strict` | root + per-package `pyproject.toml` | Versions pinned: ruff ≥0.9, black ≥25.1, mypy ≥1.15 |
| Tests | pytest | root `pyproject.toml` + per-package `pyproject.toml` | Unit + endpoint coverage |
| QR encoder | Vendored pure-Python | `mesh/rpi_hub_mesh/qrcode.py` | Avoids extra apt/pip dep on the offline image |

Outbound network usage is **isolated to two workstation-only
scripts**: `content/fetch.sh` (Kiwix ZIMs) and `models/fetch_models.sh`
(LLM weights). Neither runs on the device.

---

## 4. Setup & usage

### 4.1 Bare-metal install

On a fresh **Raspberry Pi OS Lite 64-bit (Bookworm)** image:

```bash
git clone https://github.com/coreconduit/rpi-hub.git
cd rpi-hub
sudo ./install.sh                 # default PHASE=7 — runs every phase in 1→2→3→4→5→6→9→8→7 order
sudo reboot
```

Phase-scoped installs (cumulative, useful for bring-up debugging):

```bash
sudo PHASE=1 ./install.sh    # AP only
sudo PHASE=5 ./install.sh    # AP + portal + Kiwix + frontend + status API
sudo PHASE=all ./install.sh  # alias for PHASE=7 — same execution order
```

Optional `--pack` flag stages a regional content pack's print tree:

```bash
sudo ./install.sh --pack=pacific-northwest
sudo ./install.sh --pack=gulf-coast
sudo ./install.sh --pack=mountain-west
sudo ./install.sh --pack=urban-resilience
sudo ./install.sh --pack=general-purpose   # default
```

After reboot: connect to the open `RPI-HUB-INFOHUB` SSID. Most modern
phones / laptops pop the captive sheet automatically within ~10s; if
yours doesn't, browse to `http://hub.local/`. See
`docs/CROSS_OS_TEST_MATRIX.md` for per-OS captive-portal behaviour.

### 4.2 Image bake (workstation, Linux only)

`scripts/bake_image.sh` produces a flashable
`rpi-hub-${VERSION}-${VARIANT}-arm64.img.xz`:

   make bake                         # → dist/rpi-hub-v1.2.1-generic-arm64.img.xz
```

The script loop-mounts the upstream Pi OS Lite base, runs
`PHASE=5 ./install.sh` in a (qemu-bridged if needed) chroot, scrubs the
machine-id, and re-xz-compresses. Linux-only because macOS/WSL don't
expose enough loop-mount surface. On macOS/WSL workstations, install
on the Pi itself.

### 4.3 Content (workstation → device)

```bash
# Off-device, on a workstation with internet:
./content/fetch.sh core              # ~20 GB into ./payload/var/lib/kiwix/
./content/verify.sh ./payload/var/lib/kiwix/

# Transfer to a running device:
rsync -avh --progress \
    payload/var/lib/kiwix/ pi@hub.local:/var/lib/kiwix/
ssh pi@hub.local sudo systemctl restart rpi-hub-kiwix
```

Tiers: `minimal` (≈12 GB), `core` (≈20 GB), `full` (≈150 GB).
See `docs/CONTENT_GUIDE.md` for the manifest fields, sha256 pinning
workflow, and curation principles.

### 4.4 Assistant index + weights (Pi 5 only)

```bash
# Workstation:
./models/fetch_models.sh             # weights → ./payload/var/lib/rpi-hub/models/
python -m indexer.build_index \
    --zim-dir /var/lib/kiwix \
    --out ./payload/var/lib/rpi-hub/index

# Transfer:
rsync -avh payload/var/lib/rpi-hub/models/ pi@hub.local:/var/lib/rpi-hub/models/
rsync -avh payload/var/lib/rpi-hub/index/  pi@hub.local:/var/lib/rpi-hub/index/
```

Each assistant unit has `ConditionPathExists=` on the artefact it
needs, so they auto-activate when the rsync completes — no
`systemctl` call needed.

### 4.5 Health + recovery

```bash
make smoke                           # → scripts/healthcheck.sh
sudo /opt/rpi-hub/scripts/healthcheck.sh
sudo /opt/rpi-hub/scripts/factory_reset.sh        # dry-run; --yes to commit
sudo /opt/rpi-hub/scripts/readonly_root.sh status
```

`readonly_root.sh enable` flips the root filesystem to an overlayfs
overlay (notes board + DHCP leases live on tmpfs anyway). Keys, ZIMs,
index, weights, and `/etc/rpi-hub/` are explicitly carved out of the
overlay so re-deployable identity survives reboots.

### 4.6 Captive portal HTTPS — explicitly out of scope

The portal listens on **HTTP only**. This is a deliberate design
choice, not a TODO. Three reasons:

1. **Captive-portal detection fails on TLS.** iOS / macOS / Android /
   Windows all run their captive-portal probes against
   well-known HTTP URLs (`apple.com/library/test/success.html`,
   `connectivitycheck.gstatic.com/generate_204`, …). When those probes
   hit our nginx default-server `302` to landing, the OS pops the
   captive sheet. If the portal answered on TLS with a self-signed cert,
   the probe would mark the network as "no internet" and **never show
   the sheet** — operators would have to type `http://hub.local/`
   manually, which defeats the whole captive-portal UX.
2. **No CA reachable.** An offline hub by definition cannot complete
   an ACME challenge, so any "real" cert is impossible. Self-signed
   means a browser warning on every fetch, which trains users to
   click through warnings — worse than HTTP.
3. **Threat model already allows passive observation.** The SSID is
   open by spec. Anyone on the AP can already see every byte; TLS
   between the client and the loopback nginx wouldn't change that.
   The data being served is read-only public-domain library content
   plus an ephemeral notes board — nothing that warrants the operational
   complexity TLS would add here.

**Operators who need HTTPS** (e.g., a deployment that also hosts a
private static IP behind it, or a hub paired with a public-trust
hostname) should bring their own ACME bootstrap **outside this repo**:
provision a cert via a one-off internet-connected step, ship it onto
the device manually, and add a TLS server block to
`config/nginx/rpi-hub-portal.conf` alongside the existing `:80`
default-server. The captive-portal detection problem above does not go
away — the operator must accept that some clients will not see the
auto-pop sheet.

---

## 5. API reference

Every endpoint is reverse-proxied through `nginx :80`. Internal
listeners are loopback-only.

### 5.1 `rpi-hub-status` — `GET /api/status`

```json
{
  "uptime_seconds": 12345.67,
  "load_avg": [0.12, 0.08, 0.05],
  "storage":  { "kiwix_bytes_free": 0, "kiwix_bytes_total": 0 },
  "voltage":  { "throttled": "0x0", "undervoltage": false },
  "dhcp_clients": 3,
  "time_source": "ntp | rtc | none",
  "build_version": "v1.2.1",
  "services": {
    "retrieve": "ready | not-running | unknown",
    "assist":   "ready | not-running | unknown",
    "listen":   "ready | not-running | unknown",
    "notes":    "ready | not-running | unknown",
    "mesh":     "ready | not-running | unknown",
    "adsb":     "ready | not-running | unknown",
    "adsb_aircraft": 7,
    "mesh_fingerprint": "ABCD-EFGH-IJKL-MNOP-QRST-UVWX"
  }
}
```

Every probe is fail-soft; the endpoint always returns 200. The ADS-B
probe is file-based (mtime of `aircraft.json` ≤ 30s + parseable JSON);
every other service probe is a loopback HTTP `GET /health`.

### 5.2 `rpi-hub-retrieve` — `GET /api/retrieve`

```
GET /api/retrieve?q=knot&k=5    →  { ready, results: [{article, section, score, url}, …] }
```

Hybrid BM25 + HNSW with reciprocal-rank fusion; per-article diversity
cap of 3 results.

### 5.3 `rpi-hub-assist` — `POST /api/ask`

```
POST /api/ask  {"q": "how to purify water"}
  → 200  {
      "mode": "answer | defer | noanswer",
      "answer": "…",
      "citations": [{"number": 1, "article": "…", "section": "…", "url": "/library/…"}],
      "banner":     "…",      // only when mode == "defer"
      "confidence": 0.42
    }
```

Three rules enforced at the boundary:

1. **Grounded or silent** — retrieval below confidence floor → `noanswer`.
2. **Cited or silent** — citation coverage < 60% post-processing → discarded.
3. **Deferential on dangerous topics** — six regex rules (drug dosing,
   severe trauma, mains voltage, structural, chemical, weapons) →
   `defer` with a red banner + verbatim passage, **no model call**.

### 5.4 `rpi-hub-listen` — `/api/listen/*`

Key endpoints (full list in the FastAPI OpenAPI schema at `/api/listen/docs`
when the service is running):

```
GET  /api/listen/state          → { mode, frequency_hz, label, started_ts, dongle_present }
GET  /api/listen/presets        → [ { label, frequency_hz, … }, … ]
POST /api/listen/tune           { frequency_hz, mode }  →  state
POST /api/listen/stop           →  state
GET  /api/listen/alerts         → [ { event_code, … }, … ]  (SAME alert ring)
POST /api/listen/alerts/internal  (localhost only — SAME decoder pipeline)

# Phase 13 — GPS sky survey
GET  /api/listen/gps            → { running, dongle_present, simulate, last }
                                  last: { requested_ts, completed_ts, ok, error, report }
                                  report: gps_sdr JSON contract (ts/scan/mode/bias_tee/
                                          sample_rate/integration_ms/threshold/elapsed_s/
                                          acquired_count/results[])
                                  results[]: { prn, acquired, doppler_hz, code_phase,
                                              metric, cn0_proxy_db }
POST /api/listen/gps/sweep      { prns?: int[1..32][], integration_ms?: 1..10 }
                                  → 202 + state | 409 dongle busy | 503 no dongle
```

Arbitration: all modes share a single-dongle arbiter (`dongle.Tuner`). A GPS
sweep returns **409** while any audio mode holds the dongle; audio tuning
returns 409 while a sweep is running. `POST /stop` cancels a sweep.
`rpi_hub_GPS_SIMULATE=1` in the unit environment routes sweeps through the
`gps_sdr` simulator (no dongle required — bench/dev path).

`rpi-hub-listen-same.service` is the SAME decoder data plane (separate unit).

### 5.5 `rpi-hub-notes` — `/api/notes`

- On every successful POST the service fires `rpi-hub-mesh /notes/publish`
  best-effort; mesh-less hubs are unaffected.

### 5.6 `rpi-hub-mesh` — `/api/mesh/*`

delivered into `rpi-hub-mesh.service` via systemd `LoadCredential=`
(see §6.6); the daemon never opens `/var/lib/rpi-hub/keys/` at runtime.

Owner token at `/etc/rpi-hub/mesh-owner-token` (32 hex, 0600), distinct
from the notes owner token in §5.5. For pre-v1.3 single-token
deployments the service falls back to `/etc/rpi-hub/notes-owner-token`
if `mesh-owner-token` is absent; a re-run of `install.sh` provisions
the dedicated file and the fallback stops applying.

---

## 6. Frontend pages

All pages live under `www/portal/` and are served as static assets by
nginx, with the contrast toggle, skip link, and CoreConduit visual
language (navy / silver / blue / orange) shared across them.

| Page | Role | Endpoints consumed | Degradation on backend failure |
|---|---|---|---|
| `index.html` | Hub home; grouped tiles + live status strip | `/api/status` (strip), `/api/retrieve?q=hub&k=1`, `/api/listen/state`, `/api/mesh/identity`, `/api/notes?limit=1`, `/adsb/aircraft.json`, `/api/listen/gps`, `/print/` | Probed tile fades to offline and is disabled; strip shows `—` when status API is down |
| `status.html` | System metrics dashboard | `/api/status` (poll 5s) | Banner: "service not running yet"; metrics show `—` |
| `ask.html` | Library-grounded Q&A | `POST /api/ask` (25s timeout) | Falls through to `renderNoAnswer()` (no error wall) |
| `listen.html` | RTL-SDR control | `/api/listen/state` (5s), `/api/listen/presets`, `POST /api/listen/tune`, `/api/listen/stop`, `/api/listen/alerts` (15s) | Inline "no dongle" banner; previous state persists if service down |
| `peers.html` | Mesh peers + this node's QR | `/api/mesh/identity`, `/api/mesh/identity.svg`, `/api/mesh/peers` (10s) | QR image `<img>` `onerror` hides itself; peer list preserves last render |
| `board.html` | Ephemeral notes wall | `/api/notes?limit=100` (8s), `POST /api/notes` | Inline error on submit failure; list preserves last render |
| `adsb.html` | Live aircraft table | `/adsb/aircraft.json` (3s) | "No aircraft in range" or "dump1090 isn't running yet" |
| `sky.html` | GPS sky survey | `GET /api/listen/gps` (poll 2.5s), `POST /api/listen/gps/sweep` | Inline "no dongle" banner; "radio busy" banner links to listen.html |

### Accessibility surface (consistent across pages)

- Skip link to `#main`.
- High-contrast toggle (`.contrast-toggle`) — flips a `.contrast-high`
  class on `<html>`, persisted in `localStorage`.
- `@media (prefers-contrast: more)` auto-engages high-contrast mode.
- `<noscript>` notices explain JS-required features and link to the library.
- AA-compliant contrast on every text/background pair in both modes.

The per-page a11y inconsistencies (polling cadence, aria-live
placement, ADS-B table caption) that earlier revisions tracked all
closed in v1.2.x; see `CHANGELOG.md` and `www/portal/assets/js/README.md`
for the canonical conventions.

---

## 7. Operations runbooks

### 7.1 Read-only root

```bash
sudo ./scripts/readonly_root.sh enable
sudo reboot
sudo ./scripts/readonly_root.sh status
# overlay marker : enabled
# current root   : overlay
# upper          : /var/lib/rpi-hub/overlay/upper

# To apt-upgrade:
sudo ./scripts/readonly_root.sh disable
sudo reboot
sudo apt update && sudo apt upgrade
sudo ./scripts/readonly_root.sh enable
sudo reboot
```

State that persists across reboots even with the overlay enabled
(carved out via fstab bind mounts):
- `/var/lib/rpi-hub/keys/` — Ed25519 mesh keypair
- `/var/lib/rpi-hub/index/` — assistant index
- `/var/lib/rpi-hub/models/` — LLM weights
- `/var/lib/kiwix/` — ZIM library
- `/etc/rpi-hub/` — owner token, version pin

### 7.2 Regional packs

```bash
# Workstation:
./scripts/apply_pack.sh pacific-northwest      # stages packs/pacific-northwest/

# Pi:
sudo ./install.sh --pack=pacific-northwest     # copies print tree, sets manifest
```

Pack contents (per `packs/<name>/pack.yaml`):
- `zims` — manifest entries the workstation `fetch.sh` honours
- `print[]` — printable field cards (PDFs) staged under `/print/`
- `noaa.preset_frequencies_mhz` — pre-loaded into `rpi-hub-listen`'s preset cache

### 7.3 Mesh data planes (scaffolds, hardware-gated)

LoRa (`rpi-hub-reticulum.service`):

   sudo systemctl enable --now rpi-hub-reticulum

Wi-Fi mesh (`rpi-hub-batman.service`):

   sudo systemctl enable --now rpi-hub-batman
```

Both bridges fail-open: a missing socket / binary surfaces as
`state="unavailable"` on `/api/mesh/health`; the daemon stays up.

### 7.4 ADS-B (Phase 8.4)

```bash
# Detection (read-only):
./scripts/detect_rtlsdr.sh    # exits 0 if a known RTL2832U is plugged in

# Auto-handled by install.sh:
sudo ./install.sh             # detector → install + enable dump1090 if present

# Manual opt-in after plugging in a dongle:
sudo systemctl enable --now dump1090-mutability
```

Single-dongle hubs cannot run NOAA SAME (`rpi-hub-listen-same`) and
ADS-B (`dump1090-mutability`) simultaneously — the second to start
will lose the device-claim race. Disable the mode you're not using,
or attach a second dongle and pin `DEVICE=1` in the right config file.

**Opt-in position-rounding.** `aircraft.json` is exposed at `/adsb/`
to anyone on the open SSID. For deployments where exposing precise
tracks is PII-adjacent (homes near a base, scheduled-flight predictability,
etc.), the operator can have `rpi-hub-adsb-shield.timer` round per-aircraft
`lat`/`lon` before nginx serves the file:

```bash
# 0 ≈ 110 km, 1 ≈ 11 km, 2 ≈ 1.1 km, 3 ≈ 110 m, 4 ≈ 11 m
echo 1 | sudo tee /etc/rpi-hub/adsb-precision   # opt in at ~11 km
sudo rm /etc/rpi-hub/adsb-precision             # opt out
```

Both `rpi-hub-adsb-shield.timer` and its service carry
`ConditionPathExists=/etc/rpi-hub/adsb-precision`, so without the file
nothing runs and nginx falls through to the raw `aircraft.json`. When
the file exists, the timer wakes the script once per second; it writes
`aircraft.shielded.json` atomically next to the raw output and nginx
prefers it via `location = /adsb/aircraft.json` (see
`config/nginx/rpi-hub-portal.conf`).

### 7.5 GPS sky survey (Phase 13)

```bash
# Via the portal:
#   http://hub.local/sky.html → "Run sweep" button

# Via the API:
curl -s http://hub.local/api/listen/gps          # check state + last report
curl -s -X POST http://hub.local/api/listen/gps/sweep \
     -H "Content-Type: application/json" \
     -d '{"integration_ms": 2}'                  # start sweep (202)

# Sim mode (no dongle needed — bench/dev only):
sudo systemctl edit rpi-hub-listen --force
# Add: [Service]
#      Environment=rpi_hub_GPS_SIMULATE=1
sudo systemctl restart rpi-hub-listen
```

Single-dongle caveat: the GPS sweep and every audio mode share the same
RTL-SDR. Stop Listen before sweeping. A sweep returns `409` while audio
is tuned; `POST /api/listen/stop` first.

Hardware required for a real acquisition: **RTL-SDR Blog v3/v4** + an
**active GPS patch antenna** (~$12) with built-in LNA (~27 dB gain),
powered via the dongle's hardware bias tee. Clear sky view is
mandatory — GPS L1 (~−130 dBm) does not penetrate roofs.

### 7.6 Mesh key rotation

The Ed25519 keypair at `/var/lib/rpi-hub/keys/ed25519.{priv,pub}` is
**permanent identity**. Rotating it means previously-trusted peers
will treat this node as a new, untrusted peer. To force regenerate:

```bash
   sudo systemctl stop rpi-hub-mesh rpi-hub-mesh-keygen

   sudo systemctl start rpi-hub-mesh-keygen rpi-hub-mesh
```

---

## 8. Module reference

### `api/rpi_hub_status/` — Phase 5

- `main.py` — single `GET /status` endpoint.
- `system.py` — host probes: uptime, load, kiwix disk, vcgencmd voltage,
  dnsmasq lease count, time source, build version, service probes
  including the file-based ADS-B probe.
- `tests/test_status.py` — endpoint shape, every probe's fail-soft
  path, ADS-B mtime/JSON variants.

### `assistant/` — Phase 6

- `rpi_hub_retrieve/` — hybrid BM25 + HNSW + reciprocal-rank fusion;

- `rpi_hub_assist/` — safety classifier (`safety.py`), prompt scaffold
  (`prompt.py`), Qwen2.5 chat-template wrapper, citation-validating
  post-processor (`postprocess.py`, 60% coverage floor).
- `tests/` — `test_retrieval`, `test_safety`, `test_assist`,
  `test_postprocess` — no model and no network required.

### `indexer/` — workstation-only

- `build_index.py` — ZIM → chunks → embeddings → HNSW + sqlite index.
- `chunk.py`, `embed.py`, `manifest.py` — supporting modules.
- Output: `payload/var/lib/rpi-hub/index/chunks.sqlite`,
  `index.hnsw`, `bm25.bin`, `manifest.json`.

### `models/` — workstation-only

- `fetch_models.sh` — sha256-verified download of:
  - `qwen2.5-1.5b-instruct-q4_k_m.gguf` (~880 MB)
  - `bge-small-en-v1.5.q8_0.gguf` (~25 MB)
  - `llama-server` binary (pinned commit; built on workstation, deployed via bake)

### `gps_sdr/` — Phase 13 (vendored acquisition engine)

GPS L1 C/A satellite acquisition via Parallel Code Phase Search (PCPS,
Borre et al. 2007), numpy-vectorised. **Acquisition only — no position or
time fix.** Its role is RF self-diagnostics and sky-state readout.

- `constants.py` — GPS L1 constants and PRN G2 tap table (IS-GPS-200).
- `prn.py` — C/A Gold code generator + FFT pre-computation.
- `hardware.py` — RTL-SDR wrapper with dual-path bias tee control (pyrtlsdr).
- `acquisition.py` — vectorised PCPS engine (batch FFT over all PRNs and Doppler bins).
- `simulate.py` — synthetic GPS signal generator (no hardware required).
- `__main__.py` — CLI entry point; `--once --json` mode produces the machine-readable
  report consumed by `GPSSweeper`.

Staged to `/opt/rpi-hub/gps_sdr/` (PYTHONPATH sibling of `listen/`).

### `listen/rpi_hub_listen/` — Phase 8 + Phase 13

- `main.py` — control plane (`/api/listen/*`); Phase 13 adds `GET /gps` and `POST /gps/sweep`.
- `dongle.py` — single-listener arbiter; Phase 13 adds `start_gps()` (piped, finite child) and `finish()`.
- `gps.py` — **Phase 13.** `GPSSweeper`: lifecycle management (background thread, timeout/cancel), JSON report parsing, last-result store.
- `same.py` — NOAA SAME / EAS parser with event-code lookup.
- `alerts.py` — bounded alert ring with promote-banner flagging.
- `presets.py` — pack-aware NOAA station presets.
- `audio_bridge.py` — bounded-queue producer-many-consumers fanout
  (v1.1 primitive; FastAPI WS route still hardware-gated).

### `mesh/rpi_hub_mesh/` — Phase 7 + v1.2

- `main.py` — control plane (`/api/mesh/*`).
- `identity.py` — Ed25519 keypair management; `load_or_create()` for
  the keygen oneshot, `load_from_credentials()` for the running daemon.
- `messages.py` — canonical-JSON wire format, `make_presence | note |
  index`, `sign`, `verify`.
- `peers.py` — peer table with replay-protected sequence numbers and
  trust states (`UNVERIFIED | TRUSTED | BLOCKED`).
- `lora_bridge.py`, `wifi_bridge.py` — scaffold radio bridges.
- `qrcode.py` — vendored pure-Python QR encoder (byte mode, ECC M,
  versions 1-3, 8-mask penalty selection).

### `notes/rpi_hub_notes/` — Phase 9A

- `mesh_client.py` — best-effort `rpi-hub-mesh /notes/publish` call.
- `validation.py` — text sanitiser; 280-char cap, control-char strip.

### `packs/` — Phase 9B

- `<name>/pack.yaml` per region.
- `SCHEMA.md` documents the `zims`, `print[]`, `noaa` keys.
- `general-purpose` is the default that ships if `--pack` is omitted.

### `config/` — every file carries a header comment

- `hostapd/`, `dnsmasq/`, `dhcpcd/`, `sysctl/`, `nginx/`, `motd/`,
  `dump1090/` — one file per system component.
- All headers checked by `scripts/check_config_header.py`.

### `systemd/` — every unit binds 127.0.0.1

- One unit per service. Optional units carry
  `ConditionPathExists=` so a missing artefact yields *inactive*, not
  crash-loop. Sandbox profile is uniform: `DynamicUser=yes`,
  `ProtectSystem=strict`, `MemoryDenyWriteExecute=yes`,
  `SystemCallFilter=@system-service`, narrow `RestrictAddressFamilies=`,
  `MemoryMax=` ceilings.

### `scripts/` — operator tooling

All scripts use `set -euo pipefail`. Exception: `healthcheck.sh` intentionally
omits `-e` so it continues past individual check failures (documented inline).

- `healthcheck.sh` — drives `make smoke`; calibrated WARN/FAIL.
- `factory_reset.sh` — dry-run by default; preserves
  `/var/lib/kiwix/` and `/var/lib/rpi-hub/{keys,index,models}`.
- `bake_image.sh` — workstation-only `.img.xz` producer.
- `readonly_root.sh enable | disable | status` — overlayfs root toggle.
- `apply_pack.sh` — workstation pack-staging.
- `batman_setup.sh up | down` — idempotent BATMAN-adv bring-up.
- `same_pipeline.sh` — `rtl_fm | multimon-ng | curl` SAME decoder.
- `detect_rtlsdr.sh` — lsusb-based RTL2832U detection.
- `fetch_fonts.sh` — workstation-only woff2 downloader.
- `check_config_header.py` — pre-commit header lint.

---

## 9. Versioning & releases

Tags follow `v<major>.<minor>.<patch>[-phase<N>]`:

- `v0.1.0-phase1` … `v0.9.0-phase9` — per-phase incremental ships.
- `v1.0.0` — full nine-phase build.
- `v1.1.0` — radio scaffolds, audio fanout, ADS-B UI, read-only root.
- `v1.2.0` — signed mesh envelopes (`LoadCredential=`) + QR endpoint.
- `v1.2.1` — dump1090 install gate + ADS-B status row.
- `v1.3.0-phase13` — GPS L1 C/A sky survey: `gps_sdr/` vendored engine, `GPSSweeper`, `GET/POST /api/listen/gps`, `sky.html` + `sky.js`, `MemoryMax` 96M → 320M, `scripts/release.sh`.

Full per-release detail in `CHANGELOG.md`. Open work and known
hardware-gated items are tracked in `docs/GAP_ANALYSIS.md`.
