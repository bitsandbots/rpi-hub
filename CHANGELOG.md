# Changelog

All notable changes to this project follow [Keep a Changelog](https://keepachangelog.com/)
and use [Semantic Versioning](https://semver.org/).

Tags ship in this repo as `v<major>.<minor>.<patch>[-phase<N>]` where the
`-phase<N>` suffix identifies which build-plan phase landed at that
commit.

## [Unreleased]

Post-v1.0 follow-ups under active work. Tracked but not yet tagged.

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

## [0.8.0-phase8] — 2026-05-18

See `docs/PHASE_8.md`. RTL-SDR Listen + NOAA SAME alert banner.

## [0.9.0-phase9] — 2026-05-18

See `docs/PHASE_9.md`. Notes board + regional content packs.

## [0.6.0-phase6] — 2026-05-18

See `docs/PHASE_6.md`. RAG assistant (Pi 5 only).

## [0.5.0-phase5] — 2026-05-18

See `docs/PHASE_5.md`. Status API + image bake + factory reset + MOTD.

## [0.4.0-phase4] — 2026-05-18

See `docs/PHASE_4.md`. CoreConduit frontend + status view.

## [0.3.0-phase3] — 2026-05-18

See `docs/PHASE_3.md`. Kiwix content layer + `/library/` proxy.

## [0.2.0-phase2] — 2026-05-18

See `docs/PHASE_2.md`. Captive portal redirect + nginx default-server.

## [0.1.0-phase1] — 2026-05-18

See `docs/PHASE_1.md`. Bare AP — hostapd + dnsmasq + `signal-ap.service`.

[Unreleased]: https://github.com/coreconduit/signal/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/coreconduit/signal/releases/tag/v1.0.0
[0.8.0-phase8]: https://github.com/coreconduit/signal/releases/tag/v0.8.0-phase8
[0.9.0-phase9]: https://github.com/coreconduit/signal/releases/tag/v0.9.0-phase9
[0.6.0-phase6]: https://github.com/coreconduit/signal/releases/tag/v0.6.0-phase6
[0.5.0-phase5]: https://github.com/coreconduit/signal/releases/tag/v0.5.0-phase5
[0.4.0-phase4]: https://github.com/coreconduit/signal/releases/tag/v0.4.0-phase4
[0.3.0-phase3]: https://github.com/coreconduit/signal/releases/tag/v0.3.0-phase3
[0.2.0-phase2]: https://github.com/coreconduit/signal/releases/tag/v0.2.0-phase2
[0.1.0-phase1]: https://github.com/coreconduit/signal/releases/tag/v0.1.0-phase1
