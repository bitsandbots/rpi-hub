# Gap Analysis — v1.2.1 (+ Unreleased)

What this document is: the **single source of truth for open work** on
rpi-hub. Every row is verified against the live repo on **2026-06-13**
(v1.3.0-phase13 shipped; see `CHANGELOG.md`). Rows have file:line
citations or they don't ship here.

Three categories only:

1. **Hardware-gated** — scaffold ships; final wiring needs specific kit
   on a bench.
2. **Operator workflow** — no engineering; downloads, builders, or
   field-customisation steps the operator runs once during provisioning.
3. **Polish track** — non-blocking, slated for v1.3.

Anything previously listed here that has shipped has been deleted in
the same commit that closed it. The rows that vanish from this file
are the rows that vanish from the backlog — keep that invariant.

> History note: this file absorbed `docs/REMAINING_TASKS.md` in the
> v1.2.1+ docs-consolidation pass. Items that read "Closed v1.2.x" in
> earlier revisions are now simply absent.

---

## 1. Hardware-gated engineering

Each row is deliberately deferred until specific kit lands on a bench.
Scaffold code ships so integration is purely additive when hardware
arrives.

| Item | Hardware needed | Scaffold in repo | What's left |
|---|---|---|---|
| **Phase 7.1 — LoRa data plane** | RAK4631 USB hat | `mesh/rpi_hub_mesh/lora_bridge.py`, `systemd/rpi-hub-reticulum.service` | Reticulum daemon wiring; bridge ↔ Reticulum I/O exercised against the radio |
| **Phase 7.3 — Wi-Fi mesh data plane** | Second USB Wi-Fi adapter on a non-overlapping channel | `mesh/rpi_hub_mesh/wifi_bridge.py`, `systemd/rpi-hub-batman.service`, `scripts/batman_setup.sh` | BATMAN-adv kernel module config + ping validation; add `AF_NETLINK` to `rpi-hub-mesh.service` sandbox (currently `AF_INET AF_INET6 AF_UNIX` at `systemd/rpi-hub-mesh.service:69`) |
| **Phase 8.3 — Audio WebSocket route** | Pi 4 + RTL-SDR dongle | `listen/rpi_hub_listen/audio_bridge.py` (`AudioFanout` producer/many-consumer) | FastAPI WebSocket route consuming the fanout; buffer-size tuning |
| **Phase 8.5 — APRS scanner** | Pi 4/5 + RTL-SDR parked on 144.39 MHz | Schema-only mention in `listen/rpi_hub_listen/__init__.py` | Decoder + UI page (full new page + tile probe) |
| **Three-node mesh testbed write-up** | Three Pi 4/5 + LoRa hats | none | 72-hour run + `docs/MESH_TESTBED.md` |
| **Phase 13.1 — GPS hardware sweep timing + threshold tuning** | RTL-SDR Blog v4 + active GPS patch antenna, clear sky | `gps_sdr/`, `listen/rpi_hub_listen/gps.py` | Bench-measure sweep wall time on Pi 5; tighten `DEFAULT_TIMEOUT_S` (currently 180 s backstop); confirm `TCXO_PPM` correction unnecessary on v4 (`gps_sdr/__main__.py`) |
| **Phase 13.2 — `--ppm` plumb-through** | Same bench setup | `gps_sdr/__main__.py` `--ppm` flag exists; `POST /api/listen/gps/sweep` body does not expose it | After bench confirms v4's TCXO makes ppm correction unnecessary, close without change; otherwise add `ppm?: int` to `GpsSweepIn` (`listen/rpi_hub_listen/main.py:153`) and thread it through `default_argv()` (`gps.py:64`) |

Single-dongle caveat (carry into bring-up): `rpi-hub-listen-same` and
`dump1090-mutability` both want exclusive access to one RTL-SDR. With
one dongle, pick one. With two, pin each to a serial number via
`DEVICE=` in `config/dump1090/dump1090-mutability.default` and the
matching env override on `rpi-hub-listen-same.service`. See
`docs/OVERVIEW.md` §7.4.

ADS-B (Phase 8.4) is **shipped** in v1.2.1: install-time detection via
`scripts/detect_rtlsdr.sh`, `dump1090-mutability` enabled on detection,
`/adsb/` UI live, status row wired.

## 2. Operator workflow (provisioning, not engineering)

Without these, the device boots green but the library is empty and the
field cards aren't printable. None require Pi-side work.

### 2a. ZIM payload

Driven by `content/manifest.yaml` via `./content/fetch.sh <tier>` on a
workstation with internet. Pick a tier sized to the target Pi:

| Tier | Approx. size | Hardware target | ZIMs |
|---|---|---|---|
| `minimal` | ~5 GB | Pi Zero 2 W + 16 GB SD | Simple Wikipedia (nopic), zimgit survival bundle, iFixit |
| `core` | ~13.6 GB | Pi 4 + 64 GB SD | + Wiktionary (nopic), WikEM, zimgit-medicine |
| `full` | ~150 GB | Pi 5 + 256 GB+ SSD | + full English Wikipedia (nopic), Project Gutenberg |

Full manifest fields, sha256 pinning workflow, and refresh procedure
in `docs/CONTENT_GUIDE.md`.

### 2b. Model weights (assistant tier only)

`./models/fetch_models.sh` downloads two GGUFs into
`payload/var/lib/rpi-hub/models/`:

- `qwen2.5-1.5b-instruct-q4_k_m.gguf` — generation
- `bge-small-en-v1.5-q8_0.gguf` — embedding

Both from Hugging Face. sha256s locked in `models/fetch_models.sh` as
of commit 1945e9e (qwen 6a1a2eb…, bge ec38e8da…). Re-running the
script reports `cached` for both once the files are on disk; bump the
shas alongside any future URL change.

### 2c. Pack PDFs (build step)

All 16 field-card HTML sources are written and committed across the
five packs (`packs/general-purpose | gulf-coast | mountain-west |
pacific-northwest | urban-resilience`). Shared template at
`packs/_template/`. PDFs are gitignored (build artefacts), so every
fresh workstation clone needs to render them once:

```bash
./scripts/build_pack_pdfs.sh        # walks every packs/*/print/*.html
./scripts/apply_pack.sh <name>      # validates → stages PDFs
```

The builder accepts chromium / google-chrome / chromium-browser /
wkhtmltopdf — whichever is on PATH first. Verified end-to-end with
chromium on Bookworm: all 16 cards render in <30s, every manifest
entry resolves to a non-empty PDF on disk. `apply_pack.sh` fails
loudly with a pointer to the builder if a PDF is missing —
unmissable at provision time, not silent.

## 3. Polish track (next release)

### 3a. Pi Zero 2 W GPS sweep

GPS sky survey (`POST /api/listen/gps/sweep`) is explicitly unsupported
on Pi Zero 2 W — the 32-PRN × ~41-Doppler-bin FFT correlation peaks at
~43 MB RSS and several seconds of wall time, which exceeds the Zero's
headroom. Files install on all tiers (install.sh Phase 13 sub-function);
the portal tile self-disables via the `/api/listen/gps` probe. Operator
documentation notes this in `docs/OVERVIEW.md §1`. No code change needed
unless a lighter acquisition path becomes available (e.g. fewer PRNs,
shorter integration).

## 4. Future phases (scoped, unstarted)

Extracted from `CORE_PROJECT.md` (2026-06-10 synthesis). No scaffold
exists for any of these; they are design decisions awaiting hardware and
priority approval.

| Phase | Name | Effort | Key decision |
|---|---|---|---|
| **6.1** | **PDF-backed ZIM content indexing** | ~2–3 d | The 5 `zimgit-*` "minimal tier" survival ZIMs (water, food-prep, knots, post-disaster, medicine) store their real content as bundled PDFs cataloged by a client-rendered `database.js` — confirmed each ZIM has exactly 2 `text/html` entries regardless of size (spot-checked live via libzim, 2026-07-01). `indexer.build_index._iter_articles` (`indexer/build_index.py:86`, `indexer/htmlstrip.py`) correctly indexes `text/html` only, so these five ZIMs currently contribute ~0 real chunks to the assistant index — the RAG assistant cannot answer questions grounded in them today. Decision needed: add a PDF-text-extraction dependency (e.g. `pypdf`) to `indexer/requirements.txt` plus an `application/pdf`-keyed extraction path, or document the limitation in `docs/CONTENT_GUIDE.md` and accept these guides as browse-only (still served fine via `/library/`, just not retrievable through Ask). |
| **14** | **Offline Stratum-1 Time** | ~1 d + $15 BOM | u-blox GPS module with PPS output → chrony on the Pi. Gives the hub a sane RTC-class clock for TLS-less log correlation + mesh signature timestamps. **This is the right tool for offline time** — not an extension of Phase 13's gps_sdr acquisition engine. Hardware: one active antenna can serve either Phase 13 sweeps OR Phase 14 time (both are L1 1575.42 MHz); budget two antennas if simultaneous use is needed. |
| **15** | **Power & Storage Lifecycle** | ~3–4 d | UPS HAT telemetry (low-battery state exposed on `/api/status`), low-voltage degradation tiers (graceful service shutdown order), mirrored-storage guidance (Btrfs RAID-1 on NVMe for Pi 5 deployments). Closes the C.O.R.E. narrative gap on "graceful degradation." |
| **16** | **Resource Directory service** | deferred | Community-scoped phonebook of local resources (mesh-propagated). Deferred pending community deployment feedback. |

Phase 6.1 has no hardware dependency and can be picked up independently
of the 14 → 15 → 16 sequencing below.
Phase sequencing recommended: **14 → 15**, then 16 if community feedback demands it.
Phase 14 and Phase 13's bench step can share the same hardware session (same antenna BOM decision).

## 5. Polish track

Non-blocking. Each row is "would improve the experience" not "blocks
shipping."

### 5a. Frontend polish

_All rows closed in v1.2.x — canonical service-down classes
(`.svc-status` / `.svc-fallback` / `.ask-defer`) and the canonical
`<noscript>` block are documented at the top of
`www/portal/assets/js/README.md`. New rows file here as they appear._

### 5b. Security / sandbox

- Add `AF_NETLINK` to `rpi-hub-mesh` sandbox once the BATMAN bridge
  actually attaches (BATMAN uses netlink). Tracked alongside §1 Phase 7.3.

### 5c. Test-coverage gaps

_All rows closed in v1.3.0-phase13 (see `CHANGELOG.md`). New rows
file here as they appear._

## 6. Closed (recently)

For anyone reading this and wondering where the older rows went —
they're tracked in `CHANGELOG.md`. The most recent sweep closed:

- §3b "Unconditional `rpi-hub-adsb-shield` install in `phase8_adsb`" —
  shield extracted into `phase8_adsb_shield()`, called unconditionally
  from `phase8()`. Static regression tests added to
  `tests/test_install_phase8.py`. See `CHANGELOG.md [Unreleased] Security`.
- Security — owner-token timing side-channel (`notes/rpi_hub_notes/main.py`,
  `mesh/rpi_hub_mesh/main.py`): plain `!=` → `secrets.compare_digest()`.
  Pinned by `tests/test_owner_token_timing.py`.
- Security — silent crypto downgrade in `mesh/rpi_hub_mesh/messages.py`:
  module-level `CRYPTO_AVAILABLE` flag now logs a loud warning when
  `cryptography` is unavailable.
- P2 — fail-open vs fail-closed for missing crypto: `verify()` now returns
  `False` and `sign()` raises when `cryptography` is absent; stub re-enabled
  by `rpi_hub_ALLOW_INSECURE_CRYPTO=1`. See `CHANGELOG.md [Unreleased] Changed`.
- P3 — lint-clean reproducible: `pyproject.toml` created with pinned ruff/
  black/mypy constraints, `PLR2004` suppressed in tests, `PLC0415` annotated
  at all 11 intentional deferred-import sites. `requirements-dev.txt` added.
- P4 — shell strict-mode: `batman_setup.sh` and `readonly_root.sh` now use
  `set -euo pipefail`; comments explain the intent.
- P5 — documentation niceties: `PostNoteIn.text max_length=400` comment
  added; `messages.py` dev-stub comment updated.

- Per-phase test rows (`mesh/rpi_hub_mesh/tests/test_identity_endpoint.py`,
  `test_keygen_unit_ordering.py`, `test_qrcode_decode.py`).
- All four tooling rows (`qr-decoder` and `bake-image-lint` jobs in
  `.github/workflows/lint-and-test.yml`, `.github/workflows/lighthouse.yml`,
  `.github/workflows/upgrade-path.yml` + `scripts/test_upgrade_path.sh`).
- Pack PDF authoring — HTML sources for all 16 cards now live under
  `packs/<name>/print/`; `scripts/build_pack_pdfs.sh` compiles them on
  the workstation (chromium headless, wkhtmltopdf fallback);
  `scripts/apply_pack.sh` validates each manifest entry has a built
  PDF before staging. Shared template at `packs/_template/`. Only the
  one-shot operator build step (§2c) remains.
- All frontend a11y items previously listed: `<caption class="sr-only">`
  on the ADS-B table, initial `aria-hidden="true"` on
  `listen.html`'s hardware banner, `status.html` footer version, polling
  cadence README, `role="alert"` vs `aria-live` reconciliation.
- Inline doc rows: QR `<img onerror>` comment, single-dongle
  mutual-exclusion in `rpi-hub-listen-same.service` and
  `config/dump1090/dump1090-mutability.default`, `rpi-hub-mesh-keygen.service`
  Why-line, shared owner-token note
  in both service `main.py` files.
- Frontend §3a rows: service-down classes unified as
  `.svc-status` / `.svc-fallback` / `.ask-defer`; canonical
  `<noscript>` block documented in `www/portal/assets/js/README.md`
  so reviewers catch drift.

---

## How to use this doc

- **Filing a new gap**: add a row in §1, §2, §3, or §5 with a file:line
  citation. Speculation doesn't ship here — only items cross-referenced
  to code or to a sibling doc.
- **Closing a gap**: delete the row in the same commit that closes
  it, and add the closure line to `CHANGELOG.md [Unreleased]`.
- **Spotting drift**: when a tag ships, sweep §1 for any
  hardware-gated row whose hardware is plausibly acquirable, and
  promote it to the active backlog.

## Source-of-truth map

| Document | Role |
|---|---|
| `docs/OVERVIEW.md` | Canonical system reference (purpose, architecture, tech stack, setup, API, frontend pages, runbooks, module map) |
| `docs/GAP_ANALYSIS.md` (this file) | Single canonical open-work list |
| `docs/CONTENT_GUIDE.md` | Library content workflow |
| `docs/CROSS_OS_TEST_MATRIX.md` | Captive-portal probe matrix per OS |
| `CHANGELOG.md` | Per-release notes |
| `README.md` | Top-of-funnel intro |
| `CLAUDE.md` | Working guidance for Claude |
| `Blueprint_Overview.html` | Visual blueprint for operators |
| `rpi-hub-wizard.html` | Interactive build checklist UI |
| `archive/Project_rpi-hub_*.docx` | Frozen pre-implementation specs (historical) |

Retired in the v1.2.1 docs-consolidation pass (recoverable via the
release tags `v0.1.0-phase1` … `v1.0.0`):

- `docs/PHASE_<N>.md` (one per phase)
- `docs/V1.1.md`, `docs/V1.2.md`
- `docs/REMAINING_TASKS.md` (folded into this file)
