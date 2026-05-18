# Phase 1 — Bare AP

## Goal

A Raspberry Pi broadcasts the open `SIGNAL_INFOHUB` SSID and hands out DHCP
leases in `192.168.4.0/24`. Nothing else — no captive portal yet, no library,
no DNS for the open internet (clients can connect, but name resolution will
fail until Phase 2).

## What was built

| Artifact | Path |
|---|---|
| Repo scaffold | `README.md`, `LICENSE`, `Makefile`, `.gitignore` |
| Pre-commit + CI | `.pre-commit-config.yaml`, `.github/workflows/*.yml`, `scripts/check_config_header.py` |
| Hostapd config | `config/hostapd/hostapd.conf` |
| Dnsmasq config | `config/dnsmasq/signal.conf` |
| Dhcpcd block | `config/dhcpcd/signal.conf` (appended to `/etc/dhcpcd.conf`) |
| Sysctl | `config/sysctl/signal.conf` (`ip_forward=0`) |
| Installer | `install.sh`, `uninstall.sh` |
| Service | `systemd/signal-ap.service` |

## How to verify on a Pi Zero 2 W

Starting from a fresh **Raspberry Pi OS Lite 64-bit (Bookworm)** image with
SSH enabled:

```bash
git clone https://github.com/coreconduit/signal.git
cd signal
sudo ./install.sh
sudo reboot
```

After reboot, from a phone or laptop:

1. **SSID is visible** — `SIGNAL_INFOHUB` appears in the Wi-Fi list. Open, no password.
2. **DHCP works** — joining the network gives an address in `192.168.4.10–250`,
   gateway `192.168.4.1`, lease 12h.
3. **Service is green** — on the Pi: `systemctl status signal-ap` shows
   `active (exited)` and the dependent `hostapd` + `dnsmasq` units running.
4. **No client packet leaves the AP** — on the Pi:
   ```bash
   sudo iptables -nvL FORWARD | grep wlan0
   ```
   shows the `DROP` rule with a packet counter that grows when clients try
   to browse the open internet.
5. **Country code is correct** — if you set `SIGNAL_COUNTRY_CODE=CA ./install.sh`,
   `grep country_code /etc/hostapd/hostapd.conf` should show `CA`.

## Known limitations going into Phase 2

- **DNS does nothing useful.** dnsmasq hands out the gateway as DNS server,
  but there is no wildcard rule — every name lookup returns NXDOMAIN. Browsers
  will sit on "no internet". This is intentional: Phase 2 lands the wildcard
  rule that maps every name to `192.168.4.1`, which is what triggers the
  captive-portal popup on iOS/Android/Windows.
- **No landing page.** Even with DNS, port 80 isn't serving anything yet.
  Phase 2 adds nginx.
- **No content.** `/var/lib/kiwix` does not exist. Phase 3 installs Kiwix
  and the content manifest.
- **Pi Zero 2 W only** has one Wi-Fi radio; running an AP and also being a
  client is not supported. This is fine — SIGNAL is intentionally an
  air-gapped device.

## Rollback

```bash
sudo ./uninstall.sh
```

Disables and removes the unit, drops the iptables rule, removes the dhcpcd
block, and unlinks the configs. Leaves the apt packages installed.

## Tag

`v0.1.0-phase1`
