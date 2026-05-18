# SIGNAL — Offline Survival InfoHub

A self-contained Wi-Fi access point on a Raspberry Pi that serves a curated
knowledge library, a retrieval-grounded assistant, radio reception, mesh
networking, and a community notes board — **without any internet uplink**.

Built for emergency contexts, mutual-aid groups, disaster response, and
off-grid communities.

> Status: **Phase 1 — Bare AP**. See [the full plan](./docs/PLAN.md) and the
> interactive [build wizard](./signal-wizard.html) for phase-by-phase scope
> and acceptance criteria.

## What it is

- An open Wi-Fi network (`SIGNAL_INFOHUB`) on a Raspberry Pi
- A captive portal that drops every connected client onto a local landing page
- A Kiwix-served library of Wikipedia, WikiHow, medical references, maps
- An optional small-model assistant (Pi 5 only) that summarizes the library with citations
- Optional RTL-SDR radio (NOAA alerts, FM, ham bands, ADS-B)
- Optional mesh networking between SIGNAL nodes (Reticulum + BATMAN-adv)
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
| 8     | Pi 4/5        | RTL-SDR Blog v4, telescoping antenna |

Detailed hardware notes in [`docs/HARDWARE.md`](./docs/HARDWARE.md).

## Install (Phase 1)

On a fresh **Raspberry Pi OS Lite 64-bit (Bookworm)** image:

```bash
git clone https://github.com/coreconduit/signal.git
cd signal
sudo ./install.sh
```

This installs `hostapd`, `dnsmasq`, links the configs, sets up
`signal-ap.service`, and enables it on boot. The captive portal and library
land in subsequent phases.

After reboot, look for `SIGNAL_INFOHUB` on a phone — joining should give you
a DHCP lease in `192.168.4.0/24`.

## License

MIT. See [LICENSE](./LICENSE).

Model weights and ZIM content are fetched separately and carry their own
licenses; see [`docs/CONTENT_GUIDE.md`](./docs/CONTENT_GUIDE.md).
