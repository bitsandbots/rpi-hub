# SIGNAL — System Overview

Status: **v1.2.1 shipped.** This document supersedes the per-phase
`PHASE_<N>.md` notes and the `V1.x.md` release deltas that used to live
in this directory. Git history retains every word of those files at
the corresponding release tags.

---

## 1. What SIGNAL is

SIGNAL is an **Offline Survival InfoHub** — a self-contained
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
| Receive-only radio | `signal-listen` exposes tuning + decode; no transmit code path exists |
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
- **RTL-SDR Blog v4** (Phase 8 — receive only)
- **RAK4631** USB LoRa hat (Phase 7.1 — mesh data plane, scaffold only)
- **Second USB Wi-Fi adapter** on a non-overlapping channel (Phase 7.3 — BATMAN-adv mesh)

---

## 2. Architecture

### Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│  client phone / laptop                                              │
│    │   joins open SSID  SIGNAL_INFOHUB                              │
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
│  │  │  /api/status  → signal-status :8000                     │ │   │
│  │  │  /api/retrieve→ signal-retrieve :8100                   │ │   │
│  │  │  /api/ask     → signal-assist  :8200                    │ │   │
│  │  │  /api/listen/ → signal-listen  :8300                    │ │   │
│  │  │  /api/notes   → signal-notes   :8400                    │ │   │
│  │  │  /api/mesh/   → signal-mesh    :8500                    │ │   │
│  │  │  /adsb/       → /run/dump1090-mutability/ (static)      │ │   │
│  │  │  /print/      → /var/www/signal-portal/print/ (static)  │ │   │
│  │  │  *  (host-mismatch) → 302 /                             │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │                                                              │   │
│  │  ┌── kiwix-serve ──┐ ┌── signal-status ──┐ ┌── signal-notes ┐│   │
│  │  │  127.0.0.1:8080 │ │  127.0.0.1:8000   │ │  127.0.0.1:8400││   │
│  │  └─────────────────┘ └───────────────────┘ └────────────────┘│   │
│  │                                                              │   │
│  │  ┌── signal-retrieve :8100 ─┐  ┌── signal-listen :8300 ─┐    │   │
│  │  │  BM25 + HNSW + RRF       │  │  Dongle arbiter        │    │   │
│  │  └──────────────────────────┘  └────┬───────────────────┘    │   │
│  │            │  retrieve                │ spawns                │   │
│  │  ┌── signal-assist :8200 ──┐         ▼                       │   │
│  │  │  Safety → Prompt → LLM  │  ┌── signal-listen-same ─┐      │   │
│  │  │  → Citation validate     │  │ rtl_fm|multimon-ng| │      │   │
│  │  └──────────┬──────────────┘  │ curl SAME→/internal  │      │   │
│  │             │  llama-server   └───────────────────────┘      │   │
│  │  ┌── signal-llama :8201,:8202 ─┐                             │   │
│  │  │  Qwen2.5-1.5B + bge-small   │                             │   │
│  │  └─────────────────────────────┘                             │   │
│  │                                                              │   │
│  │  ┌── signal-mesh :8500 ─────────────────────────────┐        │   │
│  │  │  Identity (Ed25519, LoadCredential)              │        │   │
│  │  │  PeerTable (replay-protected)                    │        │   │
│  │  │  Signed envelopes                                │        │   │
│  │  │  /identity.svg (QR)                              │        │   │
│  │  └────┬──────────────────────┬──────────────────────┘        │   │
│  │       │                      │                                │   │
│  │  ┌── signal-mesh-keygen ┐   │                                │   │
│  │  │ oneshot, generates    │   │ lazy attach                    │   │
│  │  │ /var/lib/signal/keys/ │   ▼                                │   │
│  │  └───────────────────────┘   ┌── signal-reticulum (scaffold) ┐│   │
│  │                              │  LoRa via RAK4631             ││   │
│  │                              └───────────────────────────────┘│   │
│  │                              ┌── signal-batman (scaffold) ───┐│   │
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
  a loopback call to `signal-mesh`'s `/notes/publish` so the envelope
  is signed and queued on whatever radio bridges are alive. Best-effort:
  a hub with no mesh hardware silently keeps notes local.
- **Status API as central health surface**: `/api/status` polls every
  per-service `/health` (or, for ADS-B, the JSON file's mtime) and
  surfaces a unified `services` block.

### Final port map

```
80/tcp    nginx                  public      landing, /library, /api/*, /adsb, /print
53/udp    dnsmasq                public      wildcard DNS → 192.168.4.1
67/udp    dnsmasq                public      DHCP
8000/tcp  signal-status          127.0.0.1   /api/status
8080/tcp  kiwix-serve            127.0.0.1   /library proxy
8100/tcp  signal-retrieve        127.0.0.1   /api/retrieve
8200/tcp  signal-assist          127.0.0.1   /api/ask
8201/tcp  llama-server (embed)   127.0.0.1   bge-small
8202/tcp  llama-server (gen)     127.0.0.1   Qwen2.5-1.5B
8300/tcp  signal-listen          127.0.0.1   /api/listen
8400/tcp  signal-notes           127.0.0.1   /api/notes
8500/tcp  signal-mesh            127.0.0.1   /api/mesh
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
| Linting | ruff, black, mypy `--strict` | pre-commit | Enforced in CI |
| Tests | pytest | per-package `pyproject.toml` | Unit + endpoint coverage |
| QR encoder | Vendored pure-Python | `mesh/signal_mesh/qrcode.py` | Avoids extra apt/pip dep on the offline image |

Outbound network usage is **isolated to two workstation-only
scripts**: `content/fetch.sh` (Kiwix ZIMs) and `models/fetch_models.sh`
(LLM weights). Neither runs on the device.

---

## 4. Setup & usage

### 4.1 Bare-metal install

On a fresh **Raspberry Pi OS Lite 64-bit (Bookworm)** image:

```bash
git clone https://github.com/coreconduit/signal.git
cd signal
sudo ./install.sh                 # equivalent to PHASE=all
sudo reboot
```

Phase-scoped installs (cumulative, useful for bring-up debugging):

```bash
sudo PHASE=1 ./install.sh    # AP only
sudo PHASE=5 ./install.sh    # AP + portal + Kiwix + frontend + status API
sudo PHASE=all ./install.sh  # everything (default; same as PHASE=7)
```

Optional `--pack` flag stages a regional content pack's print tree:

```bash
sudo ./install.sh --pack=pacific-northwest
sudo ./install.sh --pack=gulf-coast
sudo ./install.sh --pack=mountain-west
sudo ./install.sh --pack=urban-resilience
sudo ./install.sh --pack=general-purpose   # default
```

After reboot: connect to the open `SIGNAL_INFOHUB` SSID. Most modern
phones / laptops pop the captive sheet automatically within ~10s; if
yours doesn't, browse to `http://hub.local/`. See
`docs/CROSS_OS_TEST_MATRIX.md` for per-OS captive-portal behaviour.

### 4.2 Image bake (workstation, Linux only)

`scripts/bake_image.sh` produces a flashable
`signal-${VERSION}-${VARIANT}-arm64.img.xz`:

```bash
make bake                         # → dist/signal-v1.2.1-generic-arm64.img.xz
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
ssh pi@hub.local sudo systemctl restart signal-kiwix
```

Tiers: `minimal` (≈12 GB), `core` (≈20 GB), `full` (≈150 GB).
See `docs/CONTENT_GUIDE.md` for the manifest fields, sha256 pinning
workflow, and curation principles.

### 4.4 Assistant index + weights (Pi 5 only)

```bash
# Workstation:
./models/fetch_models.sh             # weights → ./payload/var/lib/signal/models/
python -m indexer.build_index \
    --zim-dir /var/lib/kiwix \
    --out ./payload/var/lib/signal/index

# Transfer:
rsync -avh payload/var/lib/signal/models/ pi@hub.local:/var/lib/signal/models/
rsync -avh payload/var/lib/signal/index/  pi@hub.local:/var/lib/signal/index/
```

Each assistant unit has `ConditionPathExists=` on the artefact it
needs, so they auto-activate when the rsync completes — no
`systemctl` call needed.

### 4.5 Health + recovery

```bash
make smoke                           # → scripts/healthcheck.sh
sudo /opt/signal/scripts/healthcheck.sh
sudo /opt/signal/scripts/factory_reset.sh        # dry-run; --yes to commit
sudo /opt/signal/scripts/readonly_root.sh status
```

`readonly_root.sh enable` flips the root filesystem to an overlayfs
overlay (notes board + DHCP leases live on tmpfs anyway). Keys, ZIMs,
index, weights, and `/etc/signal/` are explicitly carved out of the
overlay so re-deployable identity survives reboots.

---

## 5. API reference

Every endpoint is reverse-proxied through `nginx :80`. Internal
listeners are loopback-only.

### 5.1 `signal-status` — `GET /api/status`

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

### 5.2 `signal-retrieve` — `GET /api/retrieve`

```
GET /api/retrieve?q=knot&k=5    →  { ready, results: [{article, section, score, url}, …] }
```

Hybrid BM25 + HNSW with reciprocal-rank fusion; per-article diversity
cap of 3 results.

### 5.3 `signal-assist` — `POST /api/ask`

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

### 5.4 `signal-listen` — `/api/listen/*`

```
GET   /api/listen/state                        → { mode, frequency_hz, label, dongle_present }
GET   /api/listen/presets?mode=weather         → { mode, presets: [{label, frequency_hz}, …] }
POST  /api/listen/tune  {mode, frequency_hz, label}
                                               → 200 state (single-arbiter dongle claim)
POST  /api/listen/stop                         → 200 state (idle)
GET   /api/listen/alerts                       → { alerts: [{event_code, event_label,
                                                              fips_codes, duration_minutes,
                                                              station, received_ts,
                                                              expires_ts, promote_banner}] }
POST  /alerts/internal  (loopback-only)        → SAME pipeline write path
```

nginx returns 404 for `/api/listen/alerts/internal`; the app
additionally gates on `peer ∈ {127.0.0.1, ::1}`. The SAME pipeline
(`scripts/same_pipeline.sh`: `rtl_fm | multimon-ng | curl`) lives in
`signal-listen-same.service`.

### 5.5 `signal-notes` — `/api/notes`

```
GET    /api/notes?limit=100          → { notes: [{id, name, text, created_ts}, …] }
POST   /api/notes  {text, name?}     → 201 { id, name, text, created_ts }
                                     → 429 (rate-limit: 1/min and 10/h per IP)
                                     → 400 (empty after sanitisation)
DELETE /api/notes/{id}               → 204     (X-Owner-Token required)
POST   /api/notes/wipe               → { wiped: N }  (X-Owner-Token required)
GET    /api/notes/health             → { ready, note_count }
```

- Text-only, 280-char hard cap, control-chars stripped, URLs **not** clickable.
- SQLite over `RuntimeDirectory=` tmpfs → wipes on reboot.
- Owner token at `/etc/signal/notes-owner-token` (32 hex, 0600).
- On every successful POST the service fires `signal-mesh /notes/publish`
  best-effort; mesh-less hubs are unaffected.

### 5.6 `signal-mesh` — `/api/mesh/*`

```
GET   /api/mesh/identity                       → { fingerprint, public_key_b64, version }
GET   /api/mesh/identity.svg                   → image/svg+xml (QR of fingerprint)
GET   /api/mesh/peers                          → { peers: [{fingerprint, display_name,
                                                            trust, last_seen_ts,
                                                            last_rssi, radio}] }
POST  /api/mesh/peers/{fp}/trust  {display_name} → 200 PeerOut (X-Owner-Token)
POST  /api/mesh/peers/{fp}/block               → 200 PeerOut (X-Owner-Token)
GET   /api/mesh/health                         → { version, fingerprint, peer_count,
                                                   lora: {state, detail, last_change_ts},
                                                   wifi: {state, detail, last_change_ts} }
POST  /api/mesh/notes/publish (loopback only)  → { queued, radios: ["wifi"] }
```

Wire format for inter-node messages (signed):

```json
{
  "kind":   "presence | note | index",
  "sender": "<fingerprint>",
  "seq":    42,
  "ts":     0.0,
  "body":   { ... kind-specific ... },
  "sig":    "<base64 Ed25519 over canonical(body)>"
}
```

Replay protection: per-peer monotonic sequence numbers (wall-clock is
advisory because nodes may have no time source). The private key is
delivered into `signal-mesh.service` via systemd `LoadCredential=`
(see §6.6); the daemon never opens `/var/lib/signal/keys/` at runtime.

---

## 6. Frontend pages

All pages live under `www/portal/` and are served as static assets by
nginx, with the contrast toggle, skip link, and CoreConduit visual
language (navy / silver / blue / orange) shared across them.

| Page | Role | Endpoints consumed | Degradation on backend failure |
|---|---|---|---|
| `index.html` | Hub home; category tiles | `/api/retrieve?q=hub&k=1`, `/api/listen/state`, `/api/mesh/identity`, `/api/notes?limit=1`, `/print/` | Tile is hidden (no error UI) |
| `status.html` | System metrics dashboard | `/api/status` (poll 5s) | Banner: "service not running yet"; metrics show `—` |
| `ask.html` | Library-grounded Q&A | `POST /api/ask` (25s timeout) | Falls through to `renderNoAnswer()` (no error wall) |
| `listen.html` | RTL-SDR control | `/api/listen/state` (5s), `/api/listen/presets`, `POST /api/listen/tune`, `/api/listen/stop`, `/api/listen/alerts` (15s) | Inline "no dongle" banner; previous state persists if service down |
| `peers.html` | Mesh peers + this node's QR | `/api/mesh/identity`, `/api/mesh/identity.svg`, `/api/mesh/peers` (10s) | QR image `<img>` `onerror` hides itself; peer list preserves last render |
| `board.html` | Ephemeral notes wall | `/api/notes?limit=100` (8s), `POST /api/notes` | Inline error on submit failure; list preserves last render |
| `adsb.html` | Live aircraft table | `/adsb/aircraft.json` (3s) | "No aircraft in range" or "dump1090 isn't running yet" |

### Accessibility surface (consistent across pages)

- Skip link to `#main`.
- High-contrast toggle (`.contrast-toggle`) — flips a `.contrast-high`
  class on `<html>`, persisted in `localStorage`.
- `@media (prefers-contrast: more)` auto-engages high-contrast mode.
- `<noscript>` notices explain JS-required features and link to the library.
- AA-compliant contrast on every text/background pair in both modes.

See `docs/GAP_ANALYSIS.md` §4 for per-page inconsistencies that the
docs pass surfaced (polling cadence, aria-live placement, table caption
on ADS-B).

---

## 7. Operations runbooks

### 7.1 Read-only root

```bash
sudo ./scripts/readonly_root.sh enable
sudo reboot
sudo ./scripts/readonly_root.sh status
# overlay marker : enabled
# current root   : overlay
# upper          : /var/lib/signal/overlay/upper

# To apt-upgrade:
sudo ./scripts/readonly_root.sh disable
sudo reboot
sudo apt update && sudo apt upgrade
sudo ./scripts/readonly_root.sh enable
sudo reboot
```

State that persists across reboots even with the overlay enabled
(carved out via fstab bind mounts):
- `/var/lib/signal/keys/` — Ed25519 mesh keypair
- `/var/lib/signal/index/` — assistant index
- `/var/lib/signal/models/` — LLM weights
- `/var/lib/kiwix/` — ZIM library
- `/etc/signal/` — owner token, version pin

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
- `noaa.preset_frequencies_mhz` — pre-loaded into `signal-listen`'s preset cache

### 7.3 Mesh data planes (scaffolds, hardware-gated)

LoRa (`signal-reticulum.service`):
```bash
# Operator drops Reticulum config:
sudo install -d /etc/signal/reticulum
sudo nano /etc/signal/reticulum/reticulum.conf
sudo systemctl enable --now signal-reticulum
```

Wi-Fi mesh (`signal-batman.service`):
```bash
echo 'MESH_IFACE=wlan1' | sudo tee /etc/signal/mesh.conf
sudo apt install -y batctl alfred
sudo ./scripts/batman_setup.sh up      # idempotent
sudo systemctl enable --now signal-batman
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

Single-dongle hubs cannot run NOAA SAME (`signal-listen-same`) and
ADS-B (`dump1090-mutability`) simultaneously — the second to start
will lose the device-claim race. Disable the mode you're not using,
or attach a second dongle and pin `DEVICE=1` in the right config file.

### 7.5 Mesh key rotation

The Ed25519 keypair at `/var/lib/signal/keys/ed25519.{priv,pub}` is
**permanent identity**. Rotating it means previously-trusted peers
will treat this node as a new, untrusted peer. To force regenerate:

```bash
sudo systemctl stop signal-mesh signal-mesh-keygen
sudo rm /var/lib/signal/keys/ed25519.{priv,pub}
sudo systemctl start signal-mesh-keygen signal-mesh
```

---

## 8. Module reference

### `api/signal_status/` — Phase 5

- `main.py` — single `GET /status` endpoint.
- `system.py` — host probes: uptime, load, kiwix disk, vcgencmd voltage,
  dnsmasq lease count, time source, build version, service probes
  including the file-based ADS-B probe.
- `tests/test_status.py` — endpoint shape, every probe's fail-soft
  path, ADS-B mtime/JSON variants.

### `assistant/` — Phase 6

- `signal_retrieve/` — hybrid BM25 + HNSW + reciprocal-rank fusion;
  per-article diversity cap; loads index from
  `/var/lib/signal/index/`.
- `signal_assist/` — safety classifier (`safety.py`), prompt scaffold
  (`prompt.py`), Qwen2.5 chat-template wrapper, citation-validating
  post-processor (`postprocess.py`, 60% coverage floor).
- `tests/` — `test_retrieval`, `test_safety`, `test_assist`,
  `test_postprocess` — no model and no network required.

### `indexer/` — workstation-only

- `build_index.py` — ZIM → chunks → embeddings → HNSW + sqlite index.
- `chunk.py`, `embed.py`, `manifest.py` — supporting modules.
- Output: `payload/var/lib/signal/index/chunks.sqlite`,
  `index.hnsw`, `bm25.bin`, `manifest.json`.

### `models/` — workstation-only

- `fetch_models.sh` — sha256-verified download of:
  - `qwen2.5-1.5b-instruct-q4_k_m.gguf` (~880 MB)
  - `bge-small-en-v1.5.q8_0.gguf` (~25 MB)
  - `llama-server` binary (pinned commit; built on workstation, deployed via bake)

### `listen/signal_listen/` — Phase 8

- `main.py` — control plane (`/api/listen/*`).
- `dongle.py` — single-listener arbiter; uses `rtl_test` to detect.
- `same.py` — NOAA SAME / EAS parser with event-code lookup.
- `alerts.py` — bounded alert ring with promote-banner flagging.
- `presets.py` — pack-aware NOAA station presets.
- `audio_bridge.py` — bounded-queue producer-many-consumers fanout
  (v1.1 primitive; FastAPI WS route still hardware-gated).

### `mesh/signal_mesh/` — Phase 7 + v1.2

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

### `notes/signal_notes/` — Phase 9A

- `main.py` — control plane (`/api/notes`).
- `storage.py` — SQLite over tmpfs; per-IP rate-limit ring.
- `mesh_client.py` — best-effort `signal-mesh /notes/publish` call.
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

- `healthcheck.sh` — drives `make smoke`; calibrated WARN/FAIL.
- `factory_reset.sh` — dry-run by default; preserves
  `/var/lib/kiwix/` and `/var/lib/signal/{keys,index,models}`.
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

Full per-release detail in `CHANGELOG.md`. Open work and known
hardware-gated items are tracked in `docs/GAP_ANALYSIS.md`.
