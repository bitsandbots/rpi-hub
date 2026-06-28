# Changelog

All notable changes to this project follow [Keep a Changelog](https://keepachangelog.com/)
and use [Semantic Versioning](https://semver.org/).

Tags ship in this repo as `v<major>.<minor>.<patch>[-phase<N>]` where the
`-phase<N>` suffix identifies which build-plan phase landed at that
commit.

## [Unreleased]

### Security

- **Mesh inbound authentication (G-02).** `_on_lora_frame` now verifies
  every inbound envelope before it can touch the peer table: the Ed25519
  signature must verify against the presented public key, that key's
  fingerprint must equal the claimed `sender` (`identity.fingerprint_of`),
  and the key is TOFU-pinned (`PeerTable.pin_key`). Envelopes gained a
  transport-only `pub` field; `/notes/publish` now attaches it. Previously
  signatures were produced but never checked, so any party on the wire
  could forge a peer identity. Verification fails closed without the
  `cryptography` library.
- **SPA no longer phones home (G-07).** Removed the Google-Fonts `@import`
  and `preconnect` from the shipped React bundle (`www/portal/app/`), and
  added a `Content-Security-Policy` (`font-src/connect-src 'self'`) +
  `X-Content-Type-Options` backstop to the portal nginx server. Restores
  the "no phone-home / no outbound" invariant for served client code.
- **Split owner-token isolation (G-16).** The mesh→notes owner-token
  fallback is OFF by default (it collapsed the two trust domains) and now
  requires `rpi_hub_MESH_TOKEN_LEGACY_FALLBACK=1`.
- **IPv6 forward drop (G-20).** `install.sh` and `rpi-hub-ap.service` now
  apply an `ip6tables` FORWARD drop mirroring the IPv4 rule.

### Fixed

- **Single-dongle mutex is now cross-process (G-03).** The RTL-SDR is
  arbitrated by an advisory `flock` on `/run/rpi-hub/rtlsdr.lock` (new
  `config/tmpfiles.d/rpi-hub.conf`) held by the in-process `Tuner`, the
  SAME pipeline, and a new dump1090 drop-in — not just an in-process
  `threading.Lock`. Children spawn in their own session and are killed by
  process group. `/tune` and GPS sweeps now correctly 409 when another
  process holds the dongle.
- **Hybrid retrieval vector lane (G-01).** `install.sh` installs `hnswlib`
  (apt→pip) so the HNSW lane actually runs; `/api/retrieve/health` exposes
  `vector_ready`/`vector_status` so the BM25-only degradation is no longer
  silent.
- **Notes board 1024-entry cap (G-04)** implemented (FIFO prune in
  `storage.insert`); `rpi_hub_NOTES_DB` env var is now honoured.
- **Read-only root persistence (G-06).** The overlay upper is a bounded
  volatile tmpfs and persistent state (`/etc/rpi-hub`, `/var/lib/rpi-hub`,
  `/var/lib/dnsmasq`, `/var/lib/kiwix`) is bind-mounted from the lower
  disk — the mesh identity and owner tokens survive reboots again.
- **Mesh replay protection (G-05).** First-contact sequence numbers are
  recorded (no longer replayable once); the outbound counter persists
  across restarts via `StateDirectory=` so a restarted node isn't muted.
- **Dongle detection is passive (G-13).** `dongle_present()` uses
  `detect_rtlsdr.sh` (lsusb IDs, cached) instead of `rtl_test -t`, which
  opened/claimed the radio on every `/state` poll.
- **SAME unit hardware-gated (G-14).** `ExecCondition=detect_rtlsdr.sh` +
  `StartLimit*` stop it crash-looping when the binaries exist but no
  dongle is attached.
- **Assistant robustness.** Safety classifier widened (paracetamol,
  codeine, morphine, warfarin, … + misspellings) and now also scans
  retrieved passages, not just the query (G-08); prompt-injection control
  tokens are scrubbed from interpolated text (G-11); network clients catch
  `OSError`/`http.client.HTTPException` so a mid-read reset degrades to
  no-answer instead of a 500, and the llama timeout fits the 10s budget
  (G-15).
- **Index integrity.** Retrieve validates the manifest layout version and
  reads `embedding_dim` from it; mismatches refuse to serve (G-10). The
  indexer refuses to build a zero-vector index unless
  `--allow-stub-embeddings` is passed (G-12). Retrieve closes its SQLite
  connections (G-09).
- **Status API (G-19).** Probes run concurrently and are cached ~2s; a
  readiness probe requires 2xx (4xx no longer reads as "ready"); added a
  kiwix-serve probe; disk figures flag whether they describe the library
  or the root fs.
- **SAME pipeline JSON encoding (F4)** uses `jq` (with a safe fallback)
  instead of naive quote substitution.

### Changed

- Mesh `/notes/publish` independently bounds text to 280 chars.
- APRS scaffold described accurately as a "doc-only mention" in the
  Blueprint (G-21).
- Landing page (`www/portal/index.html`) redesigned with grouped tile layout
  (Core resources / Live services / System), a live status strip fed by
  `/api/status`, SVG icons, and clearer offline-state handling for optional
  services. The previous page is retained as `index-original.html` during
  review and will be removed before the next release.

## [v1.3.0-phase13] — 2026-06-13

### Added

- **Phase 13 — GPS Sky Survey.** Vendored `gps_sdr/` (GPS L1 C/A PCPS
  acquisition, numpy-vectorised) with a new `--json` machine-output mode.
  `Tuner` gains `start_gps()` (piped, finite child) and `finish()`;
  new `listen/rpi_hub_listen/gps.py` GPSSweeper runs
  `python3 -m gps_sdr --once --json` under the existing single-dongle
  arbiter with timeout/cancel semantics. New endpoints
  `GET /api/listen/gps` and `POST /api/listen/gps/sweep` (409 while audio
  tuned — sweeps never preempt audio; 503 without dongle;
  `rpi_hub_GPS_SIMULATE=1` bench path). Portal page `sky.html` + `sky.js`.
  `rpi-hub-listen.service` `MemoryMax` 96M → 320M (measured sweep child
  peak RSS ~43 MB). Eleven new tests incl. real-simulator e2e. Explicitly
  **not** a position/time fix — acquisition-only diagnostic; see
  `docs/PHASE13_GPS.md`. Pi Zero 2 W unsupported for this phase.

### Fixed (backported from rpi-pod v1.2.2)

- `install.sh` + `systemd/rpi-hub-ap.service` — six bugs fixed:
  - **Trixie/NM support**: new `ensure_nm_unmanaged()` writes
    `/etc/NetworkManager/conf.d/rpi-hub.conf` to release `wlan0` to
    hostapd; `configure_wlan0_static()` dispatches to either
    `ensure_dhcpcd_block` (Bookworm) or `ensure_nm_unmanaged` (Trixie+)
    depending on which network manager is active. The static AP IP is now
    assigned by an `ExecStartPre` `ip addr add` in the service unit
    rather than by dhcpcd.
  - **rfkill soft block**: `nmcli device disconnect wlan0` leaves a soft
    rfkill block; added `rfkill unblock wifi` in `ensure_nm_unmanaged()`
    and as the first `ExecStartPre` in `rpi-hub-ap.service` so every
    start clears any block regardless of install path.
  - **`tr | head` SIGPIPE**: `set -o pipefail` treated `head`'s early
    exit as a failure, aborting owner-token generation in phase 9. Fixed
    by wrapping `tr` in a subshell: `(tr -dc 'a-f0-9' </dev/urandom || true) | head -c 32`.
  - **`RemainAfterExit` re-run gap**: phase 1's idempotent re-run stopped
    hostapd/dnsmasq at the top but then called `systemctl start
    rpi-hub-ap.service`, which is a no-op when the unit is still "active"
    (oneshot + `RemainAfterExit=yes`), leaving the AP dead. Fixed by
    stopping `rpi-hub-ap.service` first and changing `start` → `restart`.
  - **`ExecStartPost` shell `||`**: the iptables idempotency check used
    `||` directly in a systemd exec line, which passes `||` as a literal
    argument to `iptables`. Wrapped in `/bin/sh -c '...'`.
  - **`hub.local` /etc/hosts**: added `192.168.4.1 hub.local` so the
    Pi's own browser can reach the portal without a DNS failure.



### Changed

- `mesh/rpi_hub_mesh/messages.py` — `verify()` now fails **closed** when
  `cryptography` is unavailable: returns `False` instead of accepting any
  correctly-sized signature. `sign()` raises `RuntimeError` in the same
  condition. Both paths gate on `rpi_hub_ALLOW_INSECURE_CRYPTO=1` to
  re-enable the dev stub explicitly. Closes `docs/GAP_ANALYSIS.md` §4
  item "P2 — fail-open vs fail-closed for missing crypto".
- `scripts/batman_setup.sh`, `scripts/readonly_root.sh` — added `-e` to
  `set -uo pipefail` so a failed `ip`/`iw`/`batctl`/`update-initramfs`
  call aborts the script rather than silently continuing. `readonly_root.sh`
  comment documents the intent. Closes `docs/GAP_ANALYSIS.md` §4 item
  "P4 — shell strict-mode invariant".
- New root-level `pyproject.toml` — ruff/black/mypy/pytest config for the
  full repo. Pins `ruff>=0.9,<1.0`, `black>=25.1,<26`, `mypy>=1.15,<2`;
  `per-file-ignores` suppresses `PLR2004` in tests. Intentional deferred
  imports annotated with `# noqa: PLC0415` at all 11 sites. `api/pyproject.toml`
  version constraints brought in line. New `requirements-dev.txt` for
  pip-install. Closes `docs/GAP_ANALYSIS.md` §4 item "P3 — lint-clean".
- `notes/rpi_hub_notes/main.py` — one-line comment on `PostNoteIn.text`
  `max_length=400` explaining the intentional slack over `TEXT_MAX=280`.
  Closes `docs/GAP_ANALYSIS.md` §4 item "P5 — documentation niceties".

### Fixed

- `models/fetch_models.sh` — added `-C -` for resume + `--retry-all-errors`
  + bumped `--retry` 3→5, mirroring the `ab8a014` fix already applied
  to `content/fetch.sh`. A real mid-stream hang on the qwen GGUF at
  940 MB / 84% would otherwise have wasted the partial download on
  every restart. Locked both sha256s from the verified workstation
  fetch (qwen `6a1a2eb…`, bge `ec38e8d…`); re-running now reports
  `cached` for both. Closes `docs/GAP_ANALYSIS.md` §2b row
  "lock sha256s after first fetch".
- `install.sh` — twelve error-catching gaps closed (commit `9a39c48`):
  unknown args now `die` instead of silent shift, `trap ERR` surfaces
  line + command on failure, `--pack=NAME` validated at parse time,
  `rpi_hub_COUNTRY_CODE` validated as `^[A-Z]{2}$`, `apt-get` failures
  get actionable diagnostics, `dhcpcd` + `rpi-hub-ap` start failures
  point at common causes and `journalctl`, new `nginx_reload_or_start`
  helper collapses six swallowed-error sites and surfaces the real
  reload error, phase 7 mesh fingerprint probe is now a 6×0.5 s retry
  loop matching phase 5, `rpi-hub-adsb-shield.timer` enable failure
  now warns instead of silently swallowing, `dnsmasq` reload rewritten
  as explicit `if` block. Dry-run harness at `/tmp/sigdr/dryrun.sh`
  walks `--phase=all` cleanly with `exit=0` and both new warning
  paths firing.

### Verified

- Pack PDF build pipeline end-to-end on a Bookworm workstation with
  chromium: `scripts/build_pack_pdfs.sh` renders all 16 cards in <30s,
  every `pack.yaml` `.print[].file` entry resolves to a non-empty PDF
  on disk. PDFs remain gitignored (one-time per-workstation step).
  `docs/GAP_ANALYSIS.md` §2c updated to note the verification + the
  chromium / google-chrome / chromium-browser / wkhtmltopdf
  auto-detection in the builder.

### Tests

- `tests/test_install_phase8.py` — two new static guards:
  `test_shield_extracted_into_own_function` asserts `adsb_shield.py`
  does not appear in the `phase8_adsb()` body; `test_phase8_calls_shield_unconditionally`
  asserts `phase8()` calls `phase8_adsb_shield`. Both fail if the shield
  block ever drifts back inside the decoder gate.
- New `tests/test_owner_token_timing.py` — parametrised over notes and
  mesh `main.py`: asserts `secrets.compare_digest` is used and that
  plain `==`/`!=` does not appear in `_require_owner`. Prevents silent
  regression to timing-leaking comparisons.
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
   end into `rpi-hub-mesh /notes/publish`, then verifies the resulting
  signed envelope against the mesh app's public key. Bridges the two
  FastAPI apps by intercepting `urllib.request.urlopen` (the call
  `notes/rpi_hub_notes/mesh_client.publish` makes) and re-emitting it
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

- `install.sh` — ADS-B privacy shield extracted into a dedicated
  `phase8_adsb_shield()` function that `phase8()` calls unconditionally,
  after `phase8_adsb()`. Previously the shield install block lived
  *inside* `phase8_adsb()`, after that function's early `return 0` when
  `dump1090-mutability` is absent — so on any Bookworm mirror that does
  not carry the decoder, the position-rounding timer silently never
  installed. The shield is decoder-independent (rounds whatever
  `aircraft.json` it finds). Closes `docs/GAP_ANALYSIS.md` §3b row
  "Unconditional `rpi-hub-adsb-shield` install in `phase8_adsb`".
- `notes/rpi_hub_notes/main.py`, `mesh/rpi_hub_mesh/main.py` — owner-
  token comparison changed from plain `!=` to `secrets.compare_digest()`
  to eliminate timing side-channels. The `not token_header` short-circuit
  is kept so a missing header still returns 401 without calling
  `compare_digest`. Behaviour is identical for callers.
- `mesh/rpi_hub_mesh/messages.py` — module-level `CRYPTO_AVAILABLE` flag
  added. When `cryptography` cannot be imported, a loud warning is
  logged at import time naming the insecure stub and instructing
  installation of `python3-cryptography` before deployment. Previously
  the downgrade was silent; a missing dependency would have made the
  whole mesh trust model fail open with no signal.

- Opt-in ADS-B position-rounding (`rpi-hub-adsb-shield`). The operator
  writes a precision (0–4 decimal places) into
  `/etc/rpi-hub/adsb-precision`; both `rpi-hub-adsb-shield.timer` and its
  oneshot service carry `ConditionPathExists=` so nothing runs until
  the file appears. When active, the timer ticks the script once per
  second; the script rounds per-aircraft `lat`/`lon` and atomically
  writes `aircraft.shielded.json` next to the raw output. nginx
  prefers the shielded copy via `location = /adsb/aircraft.json` with
  an `if (-f)` rewrite to a named internal location (safe-`if` pattern
  — static file selection only, no `proxy_pass` involved). New script
  `scripts/adsb_shield.py`, units `systemd/rpi-hub-adsb-shield.{service,timer}`,
  install/uninstall wiring in `install.sh:phase8_adsb` and
  `uninstall.sh:remove_listen`, docs in `docs/OVERVIEW.md §7.4`, tests
  in `tests/test_adsb_shield.py` (12 cases pinning the rounding +
  precision-file contracts). Closes `docs/GAP_ANALYSIS.md` §3b row
  "Opt-in ADS-B position-rounding flag".
- Split owner token into per-domain files:
  `/etc/rpi-hub/notes-owner-token` continues to gate `rpi-hub-notes`
   DELETE + wipe; `/etc/rpi-hub/mesh-owner-token` is the new file gating
  `rpi-hub-mesh` peer trust/block (`POST /api/mesh/peers/{fp}/{trust,block}`).
  `install.sh:ensure_owner_tokens` provisions both. For pre-v1.3
  deployments that landed when only the notes file existed,
  `rpi-hub-mesh` falls back to `notes-owner-token` so the upgrade is
  non-breaking — re-running `install.sh` provisions the dedicated
  mesh token and the fallback stops applying. Touch points:
   `install.sh`, `uninstall.sh`, `systemd/rpi-hub-mesh.service`
  (`Environment=rpi_hub_MESH_TOKEN_FILE=…`),
  `mesh/rpi_hub_mesh/main.py` (`OWNER_TOKEN_PATH` +
  `LEGACY_OWNER_TOKEN_PATH`), `notes/rpi_hub_notes/main.py` (comment
  only — path unchanged), `scripts/healthcheck.sh` (new mesh-token
  check), `docs/OVERVIEW.md` §5.5–§5.6. New
  `mesh/rpi_hub_mesh/tests/test_owner_token.py` pins the fallback
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
  `systemd/rpi-hub-listen-same.service:11-12`) and inline reference to
  the file-based ADS-B status probe semantics
  (`api/rpi_hub_status/system.py::_probe_adsb`).
- Portal CSS — renamed `.ask-noanswer` → `.svc-fallback` and
  `.board-status` (+ `--error`) → `.svc-status` so cross-page reuse
  no longer carries a misleading per-page prefix. Class structure is
  unchanged; `.ask-defer` stays as-is (genuine alert-card on both ask
    deferrals and NOAA SAME banners). Touch points: `rpi-hub.css`,
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
- `_probe_adsb()` in `api/rpi_hub_status/system.py` — file-based probe
  that returns `"ready"` + the live aircraft count when
  `aircraft.json` mtime is fresh (≤30s).
- `adsb` + `adsb_aircraft` fields on `GET /api/status`'s `services`
  block.
- `status.html` + `status.js` render an "ADS-B" row; "ready" rows show
  the live aircraft count inline.

### Changed

- `uninstall.sh` removes the dump1090 default override (only if it
   carries our rpi-hub marker) and disables the unit.

## [1.2.0] — 2026-05-18

Polish release closing two of the four non-hardware-gated items
deferred past v1.1.

### Added

- **Signed mesh envelopes.** `/notes/publish` now signs the outbound
  envelope with the real Ed25519 private key instead of the zero-byte
   stub. The keypair is delivered into `rpi-hub-mesh.service` via systemd
  `LoadCredential=`, so the running daemon has no filesystem access to
  `/var/lib/rpi-hub/keys`.
- **`rpi-hub-mesh-keygen.service`** (oneshot, `RemainAfterExit=yes`) —
   owns first-boot keypair generation. `rpi-hub-mesh.service` is
  `Requires=` + `After=` this unit, so the credential loader always
  sees a populated key directory.
- **`GET /api/mesh/identity.svg`** — server-rendered QR code of the
  local fingerprint, for the cross-hub trust workflow. Rendered by a
  hand-rolled pure-Python QR encoder (`mesh/rpi_hub_mesh/qrcode.py`):
  byte mode, ECC level M, versions 1-3, all 8 mask patterns evaluated.
- **`peers.html`** surfaces the QR inline beneath the fingerprint with
  a calm "scan with any QR reader" caption. The image element 404s
  silently if mesh is offline.

### Changed

- `rpi-hub-mesh.service` drops `ReadWritePaths=/var/lib/rpi-hub/keys`,
  `StateDirectory=rpi-hub/keys`, and the in-unit keypair-generation
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

- **Phase 7.1 scaffold** — `mesh/rpi_hub_mesh/lora_bridge.py` +
  `rpi-hub-reticulum.service`. Reticulum daemon wiring; degrades to
  `unavailable` cleanly when no LoRa hat is present.
- **Phase 7.3 scaffold** — `mesh/rpi_hub_mesh/wifi_bridge.py` +
  `rpi-hub-batman.service` + `scripts/batman_setup.sh`. BATMAN-adv
  setup script; polls `batctl o -nH` to surface Wi-Fi peers.
- **Phase 9.2** — `notes/rpi_hub_notes/mesh_client.py` calls
  `rpi-hub-mesh` on every local post; mesh service signs the envelope
  and fans it out to whichever radio bridges are up.
- **Phase 8.3 primitive** — `listen/rpi_hub_listen/audio_bridge.py`
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

- `rpi-hub-mesh.service` lazily attaches both radio bridges on first
  /health call so test clients don't spin up threads.
- Mesh peer table tags Wi-Fi peers with `BAT:` prefix so the UI
  distinguishes them from Ed25519-fingerprint peers.

## [1.0.0] — 2026-05-18

**The full nine-phase build.** Every phase from the original plan now
ships in a single image. Approved sequencing was
`1 → 2 → 3 → 4 → 5 → 6 → 9 → 8 → 7`.

### Added — Phase 7 — Mesh Networking

- `rpi-hub-mesh.service` on `127.0.0.1:8500` — FastAPI control plane with
  Ed25519 identity, peer table, replay protection, signed wire format.
- Keypair generation at first boot (`/var/lib/rpi-hub/keys/`, 0600).
- Fingerprint format: 24-char base32 of SHA-256(pubkey)[:15], grouped 6×4.
- Owner-token-gated `POST /peers/{fp}/trust` and `.../block`.
- `peers.html` + `peers.js` for the trust UI.
- `apt_install python3-cryptography` in `phase7()`.

### Added — Phase 8 — RTL-SDR Listen

- `rpi-hub-listen.service` on `127.0.0.1:8300` — control plane with
  single-listener dongle arbiter.
- `rpi-hub-listen-same.service` — `rtl_fm | multimon-ng | curl` pipeline
  parked on a NOAA WX frequency; POSTs decoded SAME headers to
  `/alerts/internal` (loopback-gated).
- SAME parser with subcounty-aware FIPS filtering, bounded alert ring,
  pack-aware NOAA presets.
- `listen.html` + `listen.js` with mode buttons, preset dropdown,
  red-banner alert promotion.
- Receive only. Transmit not present.

### Added — Phase 9 — Notes Board + Regional Packs

- `rpi-hub-notes.service` on `127.0.0.1:8400` — ephemeral SQLite over
  tmpfs (wipes on reboot), 280-char text + 24-char name limits,
  rate limiting (1/min + 10/hour per IP), owner-token DELETE + wipe.
- 32-hex owner token at `/etc/rpi-hub/notes-owner-token` (0600),
  generated once by `install.sh`.
- Five regional content packs: general-purpose, pacific-northwest,
  gulf-coast, mountain-west, urban-resilience.
- `install.sh --pack=<name>` flag; `scripts/apply_pack.sh` for the
  workstation-side staging step.
- `board.html` + `board.js`; `/print/` nginx alias for field cards.

### Added — Phase 6 — RAG Assistant *(Pi 5 only)*

- `rpi-hub-retrieve.service` on `127.0.0.1:8100` — hybrid BM25 + HNSW
  retrieval with reciprocal-rank fusion, per-article diversity cap.
- `rpi-hub-assist.service` on `127.0.0.1:8200` — safety classifier (six
  deferral rules), prompt scaffold for Qwen2.5 chat template,
  citation-validating post-processor (≥60% coverage floor).
- `rpi-hub-llama.service` — two llama.cpp instances (Qwen + bge-small).
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

Bare AP — hostapd + dnsmasq + `rpi-hub-ap.service`.

[Unreleased]: https://github.com/coreconduit/rpi-hub/compare/v1.2.1...HEAD
[1.2.1]: https://github.com/coreconduit/rpi-hub/releases/tag/v1.2.1
[1.2.0]: https://github.com/coreconduit/rpi-hub/releases/tag/v1.2.0
[1.1.0]: https://github.com/coreconduit/rpi-hub/releases/tag/v1.1.0
[1.0.0]: https://github.com/coreconduit/rpi-hub/releases/tag/v1.0.0
[0.8.0-phase8]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.8.0-phase8
[0.9.0-phase9]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.9.0-phase9
[0.6.0-phase6]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.6.0-phase6
[0.5.0-phase5]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.5.0-phase5
[0.4.0-phase4]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.4.0-phase4
[0.3.0-phase3]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.3.0-phase3
[0.2.0-phase2]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.2.0-phase2
[0.1.0-phase1]: https://github.com/coreconduit/rpi-hub/releases/tag/v0.1.0-phase1
