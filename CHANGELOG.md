# Changelog

All notable changes to this project follow [Keep a Changelog](https://keepachangelog.com/)
and use [Semantic Versioning](https://semver.org/).

Tags ship in this repo as `v<major>.<minor>.<patch>[-phase<N>]` where the
`-phase<N>` suffix identifies which build-plan phase landed at that
commit.

## [Unreleased]

### Verified

- Pack PDF build pipeline end-to-end on a Bookworm workstation with
  chromium: `scripts/build_pack_pdfs.sh` renders all 16 cards in <30s,
  every `pack.yaml` `.print[].file` entry resolves to a non-empty PDF
  on disk. PDFs remain gitignored (one-time per-workstation step).
  `docs/GAP_ANALYSIS.md` §2c updated to note the verification + the
  chromium / google-chrome / chromium-browser / wkhtmltopdf
  auto-detection in the builder.

### Tests

- New `tests/test_readonly_root.py` — 9-case harness for
  `scripts/readonly_root.sh`. Static layer pins: the three subcommands
  exist, `enable`/`disable` call `require_root` early, the fstab
  begin/end markers appear in both the writer and the `sed` remover
  (otherwise disable would leave the block forever), and the
  initramfs hook path is cleaned up by `disable`. Dynamic layer
  exercises `status` (the only read-only path) under a stubbed
  `findmnt`/`du` on `PATH` and asserts the three label lines the
  `docs/OVERVIEW.md §7.1` runbook tells operators to look for.
  Closes `docs/GAP_ANALYSIS.md` §3c row "Read-only root".
- New `tests/test_notes_mesh_e2e.py` — drives `POST /api/notes` end to
  end into `signal-mesh /notes/publish`, then verifies the resulting
  signed envelope against the mesh app's public key. Bridges the two
  FastAPI apps by intercepting `urllib.request.urlopen` (the call
  `notes/signal_notes/mesh_client.publish` makes) and re-emitting it
  against an in-memory `TestClient` for the mesh app. Catches drift
  in JSON schema, canonical body shape, or sign/verify pairing — none
  of the isolated suites covered all three together. Closes
  `docs/GAP_ANALYSIS.md` §3c row "End-to-end notes → mesh fan-out".

### Docs

- `docs/OVERVIEW.md §4.6` — new "Captive portal HTTPS — explicitly out
  of scope" section. Documents why the portal stays HTTP-only (captive-
  portal probes fail on TLS; no CA reachable; threat model already
  allows passive observation on the open SSID) and what an operator
  who needs HTTPS must bring themselves. Closes `docs/GAP_ANALYSIS.md`
  §3b row "Document the captive portal's HTTP-only design".
- `docs/GAP_ANALYSIS.md` §3c — closed the `phase8_adsb()` install
  detector row. `tests/test_install_phase8.py` shipped in commit
  a3037a5 (static guards on `install.sh` + dynamic stubbed-`lsusb`
  exercise of `scripts/detect_rtlsdr.sh`); the row was never deleted.

### Security

- Opt-in ADS-B position-rounding (`signal-adsb-shield`). The operator
  writes a precision (0–4 decimal places) into
  `/etc/signal/adsb-precision`; both `signal-adsb-shield.timer` and its
  oneshot service carry `ConditionPathExists=` so nothing runs until
  the file appears. When active, the timer ticks the script once per
  second; the script rounds per-aircraft `lat`/`lon` and atomically
  writes `aircraft.shielded.json` next to the raw output. nginx
  prefers the shielded copy via `location = /adsb/aircraft.json` with
  an `if (-f)` rewrite to a named internal location (safe-`if` pattern
  — static file selection only, no `proxy_pass` involved). New script
  `scripts/adsb_shield.py`, units `systemd/signal-adsb-shield.{service,timer}`,
  install/uninstall wiring in `install.sh:phase8_adsb` and
  `uninstall.sh:remove_listen`, docs in `docs/OVERVIEW.md §7.4`, tests
  in `tests/test_adsb_shield.py` (12 cases pinning the rounding +
  precision-file contracts). Closes `docs/GAP_ANALYSIS.md` §3b row
  "Opt-in ADS-B position-rounding flag".
- Split owner token into per-domain files:
  `/etc/signal/notes-owner-token` continues to gate `signal-notes`
  DELETE + wipe; `/etc/signal/mesh-owner-token` is the new file gating
  `signal-mesh` peer trust/block (`POST /api/mesh/peers/{fp}/{trust,block}`).
  `install.sh:ensure_owner_tokens` provisions both. For pre-v1.3
  deployments that landed when only the notes file existed,
  `signal-mesh` falls back to `notes-owner-token` so the upgrade is
  non-breaking — re-running `install.sh` provisions the dedicated
  mesh token and the fallback stops applying. Touch points:
  `install.sh`, `uninstall.sh`, `systemd/signal-mesh.service`
  (`Environment=SIGNAL_MESH_TOKEN_FILE=…`),
  `mesh/signal_mesh/main.py` (`OWNER_TOKEN_PATH` +
  `LEGACY_OWNER_TOKEN_PATH`), `notes/signal_notes/main.py` (comment
  only — path unchanged), `scripts/healthcheck.sh` (new mesh-token
  check), `docs/OVERVIEW.md` §5.5–§5.6. New
  `mesh/signal_mesh/tests/test_owner_token.py` pins the fallback
  contract. Closes `docs/GAP_ANALYSIS.md` §3b row "Split
  `X-Owner-Token` into per-domain tokens".

### Docs

- Docs consolidation pass. `docs/REMAINING_TASKS.md` folded into
  `docs/GAP_ANALYSIS.md`; the latter is now the single canonical
  open-work list, restructured around three categories
  (hardware-gated · operator workflow · polish track). Every row
  re-verified against the live repo on 2026-05-18.
- `docs/GAP_ANALYSIS.md` §5 / §7 — closed the test-coverage and tooling
  rows already shipped: `test_identity_endpoint.py`,
  `test_keygen_unit_ordering.py`, `test_qrcode_decode.py`,
  `qr-decoder` + `bake-image-lint` jobs, `lighthouse.yml`,
  `upgrade-path.yml`, `scripts/test_upgrade_path.sh`.
- Pack PDFs reframed as an operator workflow item, not hardware-gated
  (HTML sources + `scripts/build_pack_pdfs.sh` + `_template/` all ship).
- `README.md` — fixed dead link to `docs/HARDWARE.md` (now points to
  `OVERVIEW.md` §1 *Hardware tiers*).
- `CLAUDE.md` — fixed dead refs to `docs/V1.x.md` and `docs/PHASE_7.md`;
  port-map authority is now `docs/OVERVIEW.md` §2.
- `CHANGELOG.md` — removed `See docs/V1.x.md` / `See docs/PHASE_<N>.md`
  pointers (those files were retired in v1.2.1; the prose lives in git
  history at each tag).
- `Blueprint_Overview.html` "What's left" table — removed Pack PDFs
  row (no longer hardware-gated), added Phase 8.5 APRS scanner.

### Changed

- `config/dump1090/dump1090-mutability.default` header — added inline
  single-dongle mutual-exclusion note (mirrors
  `systemd/signal-listen-same.service:11-12`) and inline reference to
  the file-based ADS-B status probe semantics
  (`api/signal_status/system.py::_probe_adsb`).
- Portal CSS — renamed `.ask-noanswer` → `.svc-fallback` and
  `.board-status` (+ `--error`) → `.svc-status` so cross-page reuse
  no longer carries a misleading per-page prefix. Class structure is
  unchanged; `.ask-defer` stays as-is (genuine alert-card on both ask
  deferrals and NOAA SAME banners). Touch points: `signal.css`,
  `ask.html`, `listen.html`, `peers.html`, `board.html`, `adsb.html`,
  `board.js` (sole `classList.toggle` call site). Closes
  `docs/GAP_ANALYSIS.md` §3a row "Pick one canonical service-down UX
  pattern".
- `www/portal/assets/js/README.md` — documented the canonical
  `<noscript>` block (verbatim copy + page list) and the
  `.svc-status` / `.svc-fallback` / `.ask-defer` taxonomy so future
  edits don't drift. Closes `docs/GAP_ANALYSIS.md` §3a row
  "`<noscript>` snippet drift risk".

## [1.2.1] — 2026-05-18

Phase 8.4 install gate. dump1090-mutability now enables itself only
when a known RTL-SDR dongle is on the USB bus at provision time, and
the status page surfaces a live aircraft count beside the per-service
readiness dot. Closes the "dump1090-mutability install integration"
item from v1.1's hardware-gated backlog.

### Added

- `scripts/detect_rtlsdr.sh` — `lsusb`-based detector that exits 0 iff
  a USB device matches a known RTL2832U vendor/product ID.
- `config/dump1090/dump1090-mutability.default` — `/etc/default/`
  override pointing JSON output at `/run/dump1090-mutability/` (the
  v1.1 `/adsb/` nginx alias target), `START_DUMP1090="yes"`, BaseStation
  TCP and embedded HTTP listener both disabled.
- `install.sh phase8_adsb()` — runs the detector; enables + starts
  `dump1090-mutability.service` on a hit, leaves it disabled with a
  helpful log line on a miss.
- `_probe_adsb()` in `api/signal_status/system.py` — file-based probe
  that returns `"ready"` + the live aircraft count when
  `aircraft.json` mtime is fresh (≤30s).
- `adsb` + `adsb_aircraft` fields on `GET /api/status`'s `services`
  block.
- `status.html` + `status.js` render an "ADS-B" row; "ready" rows show
  the live aircraft count inline.

### Changed

- `uninstall.sh` removes the dump1090 default override (only if it
  carries our SIGNAL marker) and disables the unit.

## [1.2.0] — 2026-05-18

Polish release closing two of the four non-hardware-gated items
deferred past v1.1.

### Added

- **Signed mesh envelopes.** `/notes/publish` now signs the outbound
  envelope with the real Ed25519 private key instead of the zero-byte
  stub. The keypair is delivered into `signal-mesh.service` via systemd
  `LoadCredential=`, so the running daemon has no filesystem access to
  `/var/lib/signal/keys`.
- **`signal-mesh-keygen.service`** (oneshot, `RemainAfterExit=yes`) —
  owns first-boot keypair generation. `signal-mesh.service` is
  `Requires=` + `After=` this unit, so the credential loader always
  sees a populated key directory.
- **`GET /api/mesh/identity.svg`** — server-rendered QR code of the
  local fingerprint, for the cross-hub trust workflow. Rendered by a
  hand-rolled pure-Python QR encoder (`mesh/signal_mesh/qrcode.py`):
  byte mode, ECC level M, versions 1-3, all 8 mask patterns evaluated.
- **`peers.html`** surfaces the QR inline beneath the fingerprint with
  a calm "scan with any QR reader" caption. The image element 404s
  silently if mesh is offline.

### Changed

- `signal-mesh.service` drops `ReadWritePaths=/var/lib/signal/keys`,
  `StateDirectory=signal/keys`, and the in-unit keypair-generation
  `ExecStartPre=`. Those responsibilities moved to the new keygen
  oneshot.
- `identity.load_from_credentials()` replaces the daemon's call to
  `identity.load_or_create()`; the latter stays for the keygen unit
  and for tests.
- Mesh test suite adds three coverage points: credentials-dir vs disk
  fallback, deterministic stub when neither is present, and a real
  Ed25519 signature on `/notes/publish` verifying against the public
  key.

## [1.1.0] — 2026-05-18

Post-v1.0 follow-ups bundled.

### Added

- **Phase 7.1 scaffold** — `mesh/signal_mesh/lora_bridge.py` +
  `signal-reticulum.service`. Reticulum daemon wiring; degrades to
  `unavailable` cleanly when no LoRa hat is present.
- **Phase 7.3 scaffold** — `mesh/signal_mesh/wifi_bridge.py` +
  `signal-batman.service` + `scripts/batman_setup.sh`. BATMAN-adv
  setup script; polls `batctl o -nH` to surface Wi-Fi peers.
- **Phase 9.2** — `notes/signal_notes/mesh_client.py` calls
  `signal-mesh` on every local post; mesh service signs the envelope
  and fans it out to whichever radio bridges are up.
- **Phase 8.3 primitive** — `listen/signal_listen/audio_bridge.py`
  with bounded-queue producer-many-consumers fanout.
- **Phase 8.4 UI** — `www/portal/adsb.html` + `adsb.js` + `/adsb/`
  nginx alias to dump1090-mutability's output directory.
- **Read-only root** — `scripts/readonly_root.sh` `enable | disable | status`;
  initramfs hook + fstab block for overlayfs root. Operator-run; reboot
  required.
- **`/api/mesh/health`** gains `lora` + `wifi` radio status fields with
  state machine (`unavailable | connecting | connected | error |
  running`).

### Changed

- `signal-mesh.service` lazily attaches both radio bridges on first
  /health call so test clients don't spin up threads.
- Mesh peer table tags Wi-Fi peers with `BAT:` prefix so the UI
  distinguishes them from Ed25519-fingerprint peers.

## [1.0.0] — 2026-05-18

**The full nine-phase build.** Every phase from the original plan now
ships in a single image. Approved sequencing was
`1 → 2 → 3 → 4 → 5 → 6 → 9 → 8 → 7`.

### Added — Phase 7 — Mesh Networking

- `signal-mesh.service` on `127.0.0.1:8500` — FastAPI control plane with
  Ed25519 identity, peer table, replay protection, signed wire format.
- Keypair generation at first boot (`/var/lib/signal/keys/`, 0600).
- Fingerprint format: 24-char base32 of SHA-256(pubkey)[:15], grouped 6×4.
- Owner-token-gated `POST /peers/{fp}/trust` and `.../block`.
- `peers.html` + `peers.js` for the trust UI.
- `apt_install python3-cryptography` in `phase7()`.

### Added — Phase 8 — RTL-SDR Listen

- `signal-listen.service` on `127.0.0.1:8300` — control plane with
  single-listener dongle arbiter.
- `signal-listen-same.service` — `rtl_fm | multimon-ng | curl` pipeline
  parked on a NOAA WX frequency; POSTs decoded SAME headers to
  `/alerts/internal` (loopback-gated).
- SAME parser with subcounty-aware FIPS filtering, bounded alert ring,
  pack-aware NOAA presets.
- `listen.html` + `listen.js` with mode buttons, preset dropdown,
  red-banner alert promotion.
- Receive only. Transmit not present.

### Added — Phase 9 — Notes Board + Regional Packs

- `signal-notes.service` on `127.0.0.1:8400` — ephemeral SQLite over
  tmpfs (wipes on reboot), 280-char text + 24-char name limits,
  rate limiting (1/min + 10/hour per IP), owner-token DELETE + wipe.
- 32-hex owner token at `/etc/signal/notes-owner-token` (0600),
  generated once by `install.sh`.
- Five regional content packs: general-purpose, pacific-northwest,
  gulf-coast, mountain-west, urban-resilience.
- `install.sh --pack=<name>` flag; `scripts/apply_pack.sh` for the
  workstation-side staging step.
- `board.html` + `board.js`; `/print/` nginx alias for field cards.

### Added — Phase 6 — RAG Assistant *(Pi 5 only)*

- `signal-retrieve.service` on `127.0.0.1:8100` — hybrid BM25 + HNSW
  retrieval with reciprocal-rank fusion, per-article diversity cap.
- `signal-assist.service` on `127.0.0.1:8200` — safety classifier (six
  deferral rules), prompt scaffold for Qwen2.5 chat template,
  citation-validating post-processor (≥60% coverage floor).
- `signal-llama.service` — two llama.cpp instances (Qwen + bge-small).
- Workstation indexer (`indexer/`) and weight fetcher (`models/`).
- `ask.html` + `ask.js` with three-mode renderer
  (answer | defer | noanswer).
- Three rules enforced at the boundary: grounded-or-silent,
  cited-or-silent, deferential-on-dangerous-topics.

### Changed (v1.0 polish, after Phase 7)

- `/api/status` now carries a `services` block listing per-unit
  readiness (`retrieve`, `assist`, `listen`, `notes`, `mesh`) plus the
  mesh fingerprint.
- MOTD templates `{{MESH_FP}}` and links every per-tile URL.
- `scripts/healthcheck.sh` extended to probe all optional units with
  optional-unit semantics (inactive = warn, not fail).
- Status page renders the `services` block as a coloured-dot grid with
  the mesh fingerprint inline.
- `CLAUDE.md` rewritten for v1.0 shipped state.

> The per-phase entries below were the cut-over tags during initial
> build-up. The `docs/PHASE_<N>.md` write-ups they once pointed at
> were retired in v1.2.1; the prose lives in git history at each tag,
> and the *current* state of every phase is in `docs/OVERVIEW.md`.

## [0.8.0-phase8] — 2026-05-18

RTL-SDR Listen + NOAA SAME alert banner.

## [0.9.0-phase9] — 2026-05-18

Notes board + regional content packs.

## [0.6.0-phase6] — 2026-05-18

RAG assistant (Pi 5 only).

## [0.5.0-phase5] — 2026-05-18

Status API + image bake + factory reset + MOTD.

## [0.4.0-phase4] — 2026-05-18

CoreConduit frontend + status view.

## [0.3.0-phase3] — 2026-05-18

Kiwix content layer + `/library/` proxy.

## [0.2.0-phase2] — 2026-05-18

Captive portal redirect + nginx default-server.

## [0.1.0-phase1] — 2026-05-18

Bare AP — hostapd + dnsmasq + `signal-ap.service`.

[Unreleased]: https://github.com/coreconduit/signal/compare/v1.2.1...HEAD
[1.2.1]: https://github.com/coreconduit/signal/releases/tag/v1.2.1
[1.2.0]: https://github.com/coreconduit/signal/releases/tag/v1.2.0
[1.1.0]: https://github.com/coreconduit/signal/releases/tag/v1.1.0
[1.0.0]: https://github.com/coreconduit/signal/releases/tag/v1.0.0
[0.8.0-phase8]: https://github.com/coreconduit/signal/releases/tag/v0.8.0-phase8
[0.9.0-phase9]: https://github.com/coreconduit/signal/releases/tag/v0.9.0-phase9
[0.6.0-phase6]: https://github.com/coreconduit/signal/releases/tag/v0.6.0-phase6
[0.5.0-phase5]: https://github.com/coreconduit/signal/releases/tag/v0.5.0-phase5
[0.4.0-phase4]: https://github.com/coreconduit/signal/releases/tag/v0.4.0-phase4
[0.3.0-phase3]: https://github.com/coreconduit/signal/releases/tag/v0.3.0-phase3
[0.2.0-phase2]: https://github.com/coreconduit/signal/releases/tag/v0.2.0-phase2
[0.1.0-phase1]: https://github.com/coreconduit/signal/releases/tag/v0.1.0-phase1
