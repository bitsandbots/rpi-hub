# rpi-hub — Offline Survival InfoHub

A self-contained Wi-Fi access point on a Raspberry Pi that serves a curated
knowledge library, a retrieval-grounded assistant, radio reception, mesh
networking, and a community notes board — **without any internet uplink**.

Built for emergency contexts, mutual-aid groups, disaster response, and
off-grid communities.

> Status: **v1.3.0-phase13 — Phases 1–9 + Phase 13 GPS Sky Survey shipped.**
> AP, captive portal, Kiwix library, CoreConduit frontend, status API,
> RAG assistant (Pi 5), ephemeral notes board, regional content packs,
> RTL-SDR Listen (NOAA / FM / ham / ADS-B), Reticulum + BATMAN-adv mesh
> control plane, signed mesh envelopes, QR fingerprint endpoint, and
> **GPS L1 C/A sky survey** (`gps_sdr`, `GPSSweeper`, `GET/POST /api/listen/gps`,
> `sky.html`) — acquisition-only diagnostic, no position fix.
>
> Canonical references:
>
> - [`docs/OVERVIEW.md`](./docs/OVERVIEW.md) — system reference (architecture, setup, API)
> - [`docs/GAP_ANALYSIS.md`](./docs/GAP_ANALYSIS.md) — hardware-gated items + future phases
> - [`Blueprint_Overview.html`](./Blueprint_Overview.html) — visual blueprint for operators
> - [`rpi-hub-wizard.html`](./rpi-hub-wizard.html) — interactive build checklist
> - [`CHANGELOG.md`](./CHANGELOG.md) — per-release notes

## What it is

- An open Wi-Fi network (`RPI-HUB-INFOHUB`) on a Raspberry Pi
- A captive portal that drops every connected client onto a local landing page
- A Kiwix-served library of Wikipedia, iFixit, survival guides, WikEM clinical reference, maps
- An optional small-model assistant (Pi 5 only) that summarizes the library with citations
- Optional RTL-SDR radio (NOAA alerts, FM, ham bands, ADS-B, GPS sky survey)
- Optional mesh networking between rpi-hub nodes (Reticulum + BATMAN-adv)
- Optional ephemeral notes board, owner-moderated

## What it isn't

- An internet bridge — there is no uplink and no captive portal "log in to Wi-Fi" trick
- A chat product — the assistant is a writing engine over the library, not a knowledge source
- A surveillance device — no telemetry, no phone-home, no outbound IP from production
- Transmit-capable — the radio is receive-only

## Hardware

| Phase | Minimum board | Add-ons |
|------:|---------------|---------|
| 1–5   | Pi Zero 2 W   | SD card |
| 6     | Pi 5 (4 GB+)  | NVMe or fast SD, ≥256 GB |
| 7     | Pi 4/5        | USB LoRa hat, second USB Wi-Fi adapter |
| 8     | Pi 4/5        | RTL-SDR Blog v3/v4, telescoping antenna |
| 13    | Pi 4/5        | + active GPS patch antenna (~$12, built-in LNA) for sky survey |

Per-tier capability matrix and add-on detail: [`docs/OVERVIEW.md`](./docs/OVERVIEW.md) §1 *Hardware tiers*.

## Install (Phase 1)

On a fresh **Raspberry Pi OS Lite 64-bit (Bookworm)** image:

```bash
git clone https://github.com/coreconduit/rpi-hub.git
cd rpi-hub
sudo ./install.sh
```

This installs `hostapd`, `dnsmasq`, links the configs, sets up
`rpi-hub-ap.service`, and enables it on boot. The captive portal and library
land in subsequent phases.

After reboot, look for `RPI-HUB-INFOHUB` on a phone — joining should give you
a DHCP lease in `192.168.4.0/24`.

## License

MIT. See [LICENSE](./LICENSE).

Model weights and ZIM content are fetched separately and carry their own
licenses; see [`docs/CONTENT_GUIDE.md`](./docs/CONTENT_GUIDE.md).
