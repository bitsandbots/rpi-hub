# Cross-OS Captive Portal Test Matrix

This matrix is the spec we test Phase 2 against. Each row is one OS family
and the probe URLs its captive-portal detector hits. The "Pass" column is
what the device should do when joined to `RPI-POD-INFOHUB`.

## Probe URLs by platform

| Platform | Probe URL | Native expectation | What we serve | Outcome |
|---|---|---|---|---|
| **iOS / iPadOS / macOS** (CNA) | `http://captive.apple.com/hotspot-detect.html` | HTML body `<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>` | `302 → http://hub.local/` | Captive sheet opens, follows redirect, renders landing page |
| **iOS / iPadOS / macOS** (CNA, alt hosts) | `http://www.apple.com/library/test/success.html`, `http://www.airport.us/library/test/success.html`, `http://www.thinkdifferent.us/...` | same as above | `302 → http://hub.local/` | same |
| **Android 7+** | `http://connectivitycheck.gstatic.com/generate_204`, `http://www.google.com/generate_204` | `HTTP/1.1 204 No Content`, empty body | `302 → http://hub.local/` | "Sign in to network" notification; tapping opens captive browser at hub.local |
| **Android (legacy)** | `http://clients3.google.com/generate_204` | `204 No Content` | `302 → http://hub.local/` | same |
| **Android (newer)** | `http://connectivitycheck.android.com/generate_204` | `204 No Content` | `302 → http://hub.local/` | same |
| **Windows 10 / 11** (NCSI) | `http://www.msftconnecttest.com/connecttest.txt` | body `Microsoft Connect Test` | `302 → http://hub.local/` | "Action needed" toast; clicking opens Edge at hub.local |
| **Windows 10 / 11** (NCSI alt) | `http://www.msftconnecttest.com/redirect` | redirect to portal page | `302 → http://hub.local/` | same |
| **Windows 7 / 8** (legacy NCSI) | `http://www.msftncsi.com/ncsi.txt` | body `Microsoft NCSI` | `302 → http://hub.local/` | same (older Action Center prompt) |
| **Firefox** (any OS, when network has captive flag) | `http://detectportal.firefox.com/canonical.html` | body containing `<html>...success...` | `302 → http://hub.local/` | Address bar shows "Log in to network" banner; click opens portal tab |
| **GNOME / NetworkManager** | `http://nmcheck.gnome.org/check_network_status.txt` | body `NetworkManager is online` | `302 → http://hub.local/` | NM marks connection as "captive portal"; nm-applet offers login |
| **Chromium / ChromeOS** | `http://www.gstatic.com/generate_204` | `204 No Content` | `302 → http://hub.local/` | Same Android-style sign-in flow |

## Behaviour notes

### iOS / iPadOS
- The captive sheet is a sandboxed WebKit view; cookies and local storage
  in it are NOT shared with Safari. Anything we want persistent must live
  on the portal page once the user clicks "Done" and the sheet hands off.
- iOS retries the probe periodically. If our nginx is down, the sheet may
  show "No Internet Connection"; bringing nginx back up fixes it on retry.
- "Use Without Internet" in the sheet leaves the device joined but skips
  the portal. Users can still reach `http://hub.local/` from Safari.

### Android
- 14+ may evaluate the HTTPS probe (`https://www.google.com/generate_204`)
  before the HTTP one. Our box has no cert for that name, so TLS fails and
  Android falls back to HTTP within a few seconds. Expect a small delay
  before the "Sign in" notification appears.
- The captive portal browser is `com.android.captiveportallogin` — a
  stripped-down WebView. JavaScript runs, but features like service
  workers are limited. Keep the landing page simple HTML.
- After the user dismisses the captive browser, Android may keep showing
  a "Connected, no internet" badge on the Wi-Fi name. This is expected.

### Windows
- NCSI uses two channels: HTTP probe AND DNS probe (`dns.msftncsi.com`,
  which expects to resolve to `131.107.255.255`). Our wildcard DNS returns
  `192.168.4.1` instead — Windows treats that mismatch as additional
  evidence of a captive network, which is what we want.
- The captive browser on Windows 10/11 is Edge in a kiosk-like mode.

### Firefox
- Only triggers the "Log in to network" UI when the underlying OS has
  already flagged the network as captive. On a system where the OS-level
  probe failed (e.g. a desktop Linux without NM), Firefox does its own
  check and shows the banner independently.

### Linux desktops
- GNOME / NetworkManager: works as described above.
- KDE Plasma / NM: same NM probe, same result.
- Headless Linux (no NM): no captive-portal UI. User must manually browse
  to `http://hub.local/`. Document this in field-card content.

## Manual test procedure

For each platform in the table, perform these steps and record the result
in the test log (`tests/phase2-results.md` — to be created when first run):

1. Disable mobile data / wired Ethernet on the device.
2. Forget any prior `RPI-POD-INFOHUB` association.
3. Join `RPI-POD-INFOHUB`.
4. Start a stopwatch when the join confirms.
5. Record:
   - **t_sheet** — seconds until captive sheet / notification appears.
   - **t_render** — seconds until the rpi-POD landing page is fully rendered.
   - **dismiss_behaviour** — what happens when the user closes the sheet.
6. From a terminal on the device (if available):
   ```bash
   curl -v -H "Host: captive.apple.com" http://192.168.4.1/hotspot-detect.html
   curl -v -H "Host: connectivitycheck.gstatic.com" http://192.168.4.1/generate_204
   curl -v -H "Host: www.msftconnecttest.com" http://192.168.4.1/connecttest.txt
   ```
   All three should return `HTTP/1.1 302 Found` with `Location: http://hub.local/`.

## Pass criteria

A row passes when:
- **t_sheet ≤ 15 s** on a 2.4 GHz join (Pi Zero 2 W radio).
- **t_render ≤ 3 s** after the sheet opens.
- Landing page is visually correct (responsive, dark-mode aware, no
  missing assets).
- Dismissing the sheet does not break subsequent visits to `http://hub.local/`.

## Known failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| No sheet on iOS | iOS cached a "Success" response from a prior network with the same SSID | Forget the network on the device; rejoin |
| Android shows "no internet" but no sign-in notification | HTTPS-first probe blocked but HTTP probe didn't fire — usually a stale captive portal state | Forget network; toggle Wi-Fi off/on |
| Windows endless "Identifying network..." | NCSI is firewalled outbound from the client | Lift firewall; not something we can fix from the AP |
| Sheet opens but page is blank | nginx down or `/var/www/rpi-pod-portal/index.html` missing | `systemctl status nginx`, `nginx -t`, redeploy |
| Sheet opens but loops forever | The portal page does an HTTPS request that fails | Keep `index.html` HTTP-only — no third-party scripts |
