# Phase 8 — RTL-SDR Listen (Pi 4/5 for full; Zero 2 W: NOAA + FM only)

## Goal

A "Listen" tile that gives real situational awareness without the
hub ever transmitting. Three sub-tiles map to three RTL-SDR modes the
single-listener arbiter exposes:

* **Weather** — parked on NOAA WX, decoding SAME (EAS) alerts. When a
  banner-promoted alert fires, the landing page pins a red banner for
  every connected phone.
* **Broadcast** — FM band, presets + free-tune.
* **Bands** — ham band markers, ADS-B (Pi 4/5 only via dump1090), APRS
  (sub-phase 8.5 — schema only in v0.8).

## What was built

| Artifact | Path |
|---|---|
| Control plane | `listen/signal_listen/main.py` (FastAPI on `:8300`) |
| Dongle arbiter | `listen/signal_listen/dongle.py` (Tuner; single-listener) |
| SAME parser | `listen/signal_listen/same.py` (regex + event-code lookup) |
| Alert ring | `listen/signal_listen/alerts.py` (bounded deque) |
| Preset loader | `listen/signal_listen/presets.py` (pack-aware NOAA list) |
| SAME pipeline | `scripts/same_pipeline.sh` (rtl_fm \| multimon-ng \| curl) |
| Tests | `listen/signal_listen/tests/` (SAME parse, alert ring, presets) |
| Systemd units | `signal-listen.service`, `signal-listen-same.service` |
| nginx route | `/api/listen/` (with `/alerts/internal` 404 guard) |
| UI | `www/portal/listen.html` + `www/portal/assets/js/listen.js` |
| Installer step | `phase8()` in `install.sh` |
| Uninstaller step | `remove_listen()` in `uninstall.sh` |

## Endpoints (proxied at `/api/listen/...`)

```
GET   /api/listen/state                   → { mode, frequency_hz, label, dongle_present }
GET   /api/listen/presets?mode=weather    → { mode, presets: [{label, frequency_hz}, …] }
POST  /api/listen/tune  {mode, frequency_hz, label}  → 200 state
POST  /api/listen/stop                    → 200 state (idle)
GET   /api/listen/alerts                  → { alerts: [{event_code, event_label, fips_codes,
                                                          duration_minutes, station,
                                                          received_ts, expires_ts,
                                                          promote_banner}, …] }
```

`POST /alerts/internal` is the SAME pipeline's write path. nginx returns
404 for that URL so a remote client cannot reach it; the app also gates
on the peer being a loopback caller. The pipeline runs locally and POSTs
each parsed `ZCZC-…` line via curl.

## Pack-aware presets

When a regional pack (Phase 9B) writes
`/var/lib/signal/listen/noaa-presets.yaml`, the service reads it on every
`/presets?mode=weather` request and surfaces the operator's preferred
NOAA stations first. Default falls back to the canonical seven WX
frequencies (162.400–162.550 MHz).

## Acceptance

- Listen tile self-disables when `signal-listen.service` is unreachable.
- Listen page surfaces "no dongle" cleanly when `rtl_test` reports
  nothing — the rest of the hub keeps working.
- SAME parser round-trips on synthetic alert lines (covered by
  `test_same.py`) and on multimon-ng-prefixed lines.
- Active alerts pin the red banner on the Listen page within the next
  15s alert poll.

## Hardware

| Item | Notes |
|---|---|
| RTL-SDR Blog v4 | ~ $30. Receive only. Earlier v3 dongles also work but lack the v4's HF improvements. |
| Telescoping antenna kit | ~ $15. Tune length to the band you're parked on. |
| External antenna pigtail | Optional. SMA + jumper for a roof antenna. |

Transmit capability is **not present** and is not on the roadmap.

## Known limitations going into the next phase

- WebSocket audio bridge (sub-phase 8.3 polish) is not in this commit.
  The UI controls the dongle but doesn't yet stream audio to the
  browser. We want a Pi 4 + dongle on the bench before tuning sample
  rates / buffer sizes.
- dump1090 / ADS-B (sub-phase 8.4) is installed but no UI is wired yet.
- APRS scanner (sub-phase 8.5) — schema only.
- The SAME pipeline parks on 162.400 by default. Operators with a
  regional pack get the right station; bare installs may need to edit
  `Environment=SIGNAL_SAME_FREQ_HZ=` in the unit.

## Next: Phase 7

Per the approved sequencing (`6 → 9 → 8 → 7`), Phase 7 (mesh
networking — Reticulum + BATMAN-adv) ships last.
