# Gap Analysis — v1.2.1

What this document is: the **single source of truth for open work** on
SIGNAL. Every row is verified against the live repo on **2026-05-18**
(post-v1.2.1). Rows have file:line citations or they don't ship here.

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
| **Phase 7.1 — LoRa data plane** | RAK4631 USB hat | `mesh/signal_mesh/lora_bridge.py`, `systemd/signal-reticulum.service` | Reticulum daemon wiring; bridge ↔ Reticulum I/O exercised against the radio |
| **Phase 7.3 — Wi-Fi mesh data plane** | Second USB Wi-Fi adapter on a non-overlapping channel | `mesh/signal_mesh/wifi_bridge.py`, `systemd/signal-batman.service`, `scripts/batman_setup.sh` | BATMAN-adv kernel module config + ping validation; add `AF_NETLINK` to `signal-mesh.service` sandbox (currently `AF_INET AF_INET6 AF_UNIX` at `systemd/signal-mesh.service:69`) |
| **Phase 8.3 — Audio WebSocket route** | Pi 4 + RTL-SDR dongle | `listen/signal_listen/audio_bridge.py` (`AudioFanout` producer/many-consumer) | FastAPI WebSocket route consuming the fanout; buffer-size tuning |
| **Phase 8.5 — APRS scanner** | Pi 4/5 + RTL-SDR parked on 144.39 MHz | Schema-only mention in `listen/signal_listen/__init__.py` | Decoder + UI page (full new page + tile probe) |
| **Three-node mesh testbed write-up** | Three Pi 4/5 + LoRa hats | none | 72-hour run + `docs/MESH_TESTBED.md` |

Single-dongle caveat (carry into bring-up): `signal-listen-same` and
`dump1090-mutability` both want exclusive access to one RTL-SDR. With
one dongle, pick one. With two, pin each to a serial number via
`DEVICE=` in `config/dump1090/dump1090-mutability.default` and the
matching env override on `signal-listen-same.service`. See
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
| `minimal` | ~12 GB | Pi Zero 2 W + 16 GB SD | Simple Wikipedia (nopic), WikiHow |
| `core` | ~20 GB | Pi 4 + 64 GB SD | + Wiktionary (nopic), WHO medical |
| `full` | ~150 GB | Pi 5 + 256 GB+ SSD | + full English Wikipedia (nopic), Project Gutenberg |

Full manifest fields, sha256 pinning workflow, and refresh procedure
in `docs/CONTENT_GUIDE.md`.

### 2b. Model weights (assistant tier only)

`./models/fetch_models.sh` downloads two GGUFs into
`payload/var/lib/signal/models/`:

- `qwen2.5-1.5b-instruct-q4_k_m.gguf` — generation
- `bge-small-en-v1.5-q8_0.gguf` — embedding

Both from Hugging Face. The shipped script has empty sha256 fields;
lock them in after first fetch (same pattern as the ZIM manifest).

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

## 3. Polish track (v1.3)

Non-blocking. Each row is "would improve the experience" not "blocks
shipping."

### 3a. Frontend polish

_All rows closed in v1.2.x — canonical service-down classes
(`.svc-status` / `.svc-fallback` / `.ask-defer`) and the canonical
`<noscript>` block are documented at the top of
`www/portal/assets/js/README.md`. New rows file here as they appear._

### 3b. Security / sandbox (track for v1.3)

- Add `AF_NETLINK` to `signal-mesh` sandbox once the BATMAN bridge
  actually attaches (BATMAN uses netlink). Tracked alongside §1 Phase 7.3.

### 3c. Test-coverage gaps

_All rows closed in v1.3 (see `CHANGELOG.md [Unreleased]`). New rows
file here as they appear._

## 4. Closed (recently)

For anyone reading this and wondering where the older rows went —
they're tracked in `CHANGELOG.md`. The most recent sweep closed:

- Per-phase test rows (`mesh/signal_mesh/tests/test_identity_endpoint.py`,
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
  mutual-exclusion in `signal-listen-same.service` and
  `config/dump1090/dump1090-mutability.default`, `signal-mesh-keygen.service`
  Why-line, ADS-B file-based probe semantics, shared owner-token note
  in both service `main.py` files.
- Frontend §3a rows: service-down classes unified as
  `.svc-status` / `.svc-fallback` / `.ask-defer`; canonical
  `<noscript>` block documented in `www/portal/assets/js/README.md`
  so reviewers catch drift.

---

## How to use this doc

- **Filing a new gap**: add a row in §1, §2, or §3 with a file:line
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
| `signal-wizard.html` | Interactive build checklist UI |
| `Project_SIGNAL_*.docx` | Frozen pre-implementation specs (historical) |

Retired in the v1.2.1 docs-consolidation pass (recoverable via the
release tags `v0.1.0-phase1` … `v1.0.0`):

- `docs/PHASE_<N>.md` (one per phase)
- `docs/V1.1.md`, `docs/V1.2.md`
- `docs/REMAINING_TASKS.md` (folded into this file)
