# Gap Analysis — v1.2.1

What this document is: an explicit, file-cited inventory of work the
codebase claims (in docs, in comments, in `Known limitations`
sections) but does **not** yet do, plus inconsistencies and surfaces
that are shipped but undocumented. Updated whenever a tag goes out.

> **Note on the destructive doc-cleanup pass that produced this file:**
> The per-phase `PHASE_<N>.md` and `V1.x.md` files were deleted in the
> same commit that introduced this gap analysis. Their per-phase
> "Known limitations going into Phase N+1" sections are subsumed
> here, with one row per surviving open item and a column citing the
> tag the limitation first appeared in (so the historic context is
> still reachable via `git show <tag>`).

---

## 1. Hardware-gated TODOs

Each of these is **deliberately deferred** until specific kit is on a
bench. The scaffold code ships so the integration is purely additive
when hardware arrives.

| Area | What's missing | Scaffold in repo | Hardware needed | First flagged |
|---|---|---|---|---|
| **Audio WS endpoint** (Phase 8.3) | FastAPI WebSocket route consuming `AudioFanout` | `listen/signal_listen/audio_bridge.py` (bounded-queue producer/many-consumers fanout) | Pi 4 + RTL-SDR dongle to tune buffer sizes | v1.1 |
| **LoRa link layer** (Phase 7.1) | Reticulum daemon wiring + bridge↔Reticulum I/O | `mesh/signal_mesh/lora_bridge.py`, `systemd/signal-reticulum.service` | RAK4631 USB hat | v1.0 |
| **Wi-Fi mesh data plane** (Phase 7.3) | BATMAN-adv kernel module config + ping validation | `mesh/signal_mesh/wifi_bridge.py`, `systemd/signal-batman.service`, `scripts/batman_setup.sh` | Second USB Wi-Fi adapter on non-overlapping channel | v1.1 |
| **Three-node mesh testbed write-up** | `docs/MESH_TESTBED.md` with 72-hour run results | none | Three Pi 4/5 + LoRa hats | v1.0 |
| **Pack PDFs** | Printable field cards for each regional pack | `packs/<name>/pack.yaml` schema + `scripts/apply_pack.sh` staging | Design pass, not hardware — listed here because it's the last remaining post-v1.2 software item not in code | v1.0 |
| **APRS scanner** (Phase 8.5) | Decoder + UI | schema only | Pi 4/5 + dongle parked on 144.39 MHz | v1.0 |

## 2. Documented claims with no shipped code

None as of v1.2.1.

Items previously in this section (signed mesh envelopes, QR
fingerprint generator, dump1090 install gate, ADS-B status surface)
all shipped in v1.2 → v1.2.1.

## 3. Code that's under-documented

Surfaces a fresh contributor would have to read source to discover:

| Surface | File:line | Why it's missing from docs |
|---|---|---|
| `peers.html` QR `<img>` `onerror` fallback | `www/portal/peers.html:38-46`, `www/portal/assets/js/peers.js:33-44` | Pattern is unique to peers page; the "tile-probe" doc only covers landing tiles |
| Polling cadence per page | `assets/js/status.js`, `listen.js`, `peers.js`, `board.js`, `adsb.js` | Each page picks its own (3s … 15s); no central rationale doc |
| Single-dongle mutual exclusion between `signal-listen-same` and `dump1090-mutability` | `docs/OVERVIEW.md` §7.4 calls it out; install.sh's logged hint only references one side | Documented in OVERVIEW from v1.2.1; not yet inline in the units |
| `signal-mesh-keygen.service` purpose | `systemd/signal-mesh-keygen.service` header | Header explains it; no top-level doc until OVERVIEW v1.2.1 |
| ADS-B file-based probe semantics (mtime + JSON) | `api/signal_status/system.py:_probe_adsb` | Documented in OVERVIEW v1.2.1 §5.1; not in the unit's comment header |
| Owner token shared across `signal-notes` and `signal-mesh` moderation | `/etc/signal/notes-owner-token` is reused | OVERVIEW v1.2.1 §5.6 mentions it; the original notes-board doc was the only place |

## 4. Frontend inconsistencies

Surfaced by the v1.2.1 frontend audit. None block the user — they're
polish items.

| Inconsistency | Pages affected | Suggested fix |
|---|---|---|
| Service-down UX pattern differs page-to-page | `ask.html` (silent fallthrough), `listen.html` (inline hardware banner), `peers.html` (image-error hide), `board.html` (inline error), `adsb.html` (calm status text), `status.html` (page-wide banner) | Pick one canonical pattern (probably "calm inline message in the page's primary status region"); apply to all |
| `<noscript>` copy and placement varies | All pages with one | Lift to a shared snippet; standardise tone |
| Polling cadence rationale absent | `status.js` 5s, `listen.js` 5s/15s, `peers.js` 10s, `board.js` 8s, `adsb.js` 3s | Document the rationale (or unify) in `assets/js/README.md` or in each file's header |
| `aria-live` vs `role="alert"` choice varies | `status.html` (no region), `ask.html` (`role="alert"`), `listen/peers/board/adsb` (`aria-live="polite"`) | Use `role="alert"` only for content that must announce immediately on appearance (banners on `defer`); use `aria-live="polite"` otherwise |
| ADS-B table lacks `<caption>` | `adsb.html` | Add `<caption class="sr-only">Aircraft in range</caption>` |
| `listen.html` hardware banner has no `aria-hidden` when not shown | `listen.html:39-41` | Add `aria-hidden="true"` initial state; flip on show |
| Status page footer says "Phase 4" while `<noscript>` references Phase 5 | `status.html` | Update footer to "v1.2.1 · signal-status" |

## 5. Test-coverage gaps

| Surface | What's untested | Risk if it regresses |
|---|---|---|
| FastAPI `/identity.svg` endpoint | No endpoint-level test (FastAPI testclient not installed on the dev image we ship; tests live in CI) | Operator scans a corrupted QR → can't paste fingerprint |
| `signal-mesh-keygen.service` integration | Only `identity.load_or_create()` is unit-tested; the systemd unit's ordering vs. `signal-mesh.service` isn't exercised | First boot ships with keys but daemon fails to load them |
| QR encoder round-trip through a real decoder | We assert structural invariants but never decode our own output | A QR that "looks right" but is unreadable by phone cameras |
| `phase8_adsb()` in install.sh | No automated test (would need fake `lsusb` in CI) | Detector regression silently disables dump1090 enablement |
| End-to-end `POST /api/notes` → `signal-mesh /notes/publish` signing path | `test_publish_note_signs_with_real_key_when_available` covers the signing in isolation; no test that drives the cross-service hop | Notes fail to fan out to mesh without a journalctl entry |
| Read-only root | `scripts/readonly_root.sh` has no test harness | Toggling overlayfs on a live device with no recovery path |

## 6. Security / sandbox surface

Already audited in v1.0 polish and v1.2 (LoadCredential rewiring).
Outstanding items:

- The `X-Owner-Token` is shared between `signal-notes` (DELETE / wipe)
  and `signal-mesh` (peer trust / block) via `/etc/signal/notes-owner-token`.
  Convenient but conflates two trust domains. Pre-v2 consideration: separate tokens.
- `signal-mesh` sandbox permits `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`.
  Once LoRa / BATMAN bridges land, we may need to add `AF_NETLINK` (BATMAN uses
  netlink). Plan for that in the v1.3 pre-flight.
- The captive portal's wildcard DNS + nginx `302` is HTTP-only by design.
  Document that anyone needing HTTPS for in-portal logins should bring
  their own ACME bootstrap (out of scope for the offline build).
- ADS-B aircraft positions are PII-adjacent for some operators. The
  `aircraft.json` mtime+content is exposed via `/adsb/` to anyone on
  the SSID. Future flag: an opt-in obfuscation layer that rounds
  positions to a configurable precision.

## 7. Tooling

| Gap | Detail |
|---|---|
| No CI-side QR decoder check | Would catch encoder regressions across SVG renderers |
| No Lighthouse runner in CI | Phase 4 acceptance is "Lighthouse mobile ≥ 95"; verified manually only |
| No image-bake validation in CI | `scripts/bake_image.sh` is Linux-only and chroot-heavy; we run it manually |
| No upgrade path test | Going from `v1.1.0 → v1.2.0 → v1.2.1` via `install.sh` against a long-running deployment is not exercised; could break the LoadCredential rewiring on a node that still has the v1.1 unit semantics in memory |

## 8. Source-of-truth dependencies

| Document | Status | Where it currently lives |
|---|---|---|
| `docs/OVERVIEW.md` | **Canonical** v1.2.1 reference (this doc's sibling) | New as of v1.2.1 |
| `CHANGELOG.md` | **Canonical** per-release notes | Root |
| `CLAUDE.md` | **Canonical** working guidance for Claude | Root |
| `README.md` | **Canonical** top-of-funnel intro | Root |
| `signal-wizard.html` | **Canonical** build checklist UI | Root |
| `Blueprint_Overview.html` | **Canonical** visual blueprint (operator) | Root, new as of v1.2.1 |
| `docs/CONTENT_GUIDE.md` | **Canonical** library content workflow | docs/ |
| `docs/CROSS_OS_TEST_MATRIX.md` | **Canonical** captive-portal probe matrix | docs/ |
| `Project_SIGNAL_*.docx` (3 files) | **Frozen pre-implementation specs** — useful historical context, may diverge from shipped state | Root |

The per-phase `PHASE_<N>.md` and `V1.x.md` files were retired in the
v1.2.1 docs-consolidation pass. The information they carried is now
in `OVERVIEW.md` (current state) + `CHANGELOG.md` (release history) +
this gap analysis (open work). Their pre-removal content remains in
git history under the corresponding release tags.

---

## How to use this doc

- **Filing a new gap**: add a row to §1, §3, §4, or §5 with a
  file:line citation. Don't write speculation here — only items
  cross-referenced to code or to a shipped doc.
- **Closing a gap**: delete the row in the same commit that closes
  it, and add a line to the corresponding `CHANGELOG.md` entry.
- **Spotting drift**: when a tag ships, sweep this doc for any
  hardware-gated row whose hardware is now plausible to acquire, and
  promote it to the active backlog.
