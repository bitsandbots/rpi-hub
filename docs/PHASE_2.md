# Phase 2 — Captive Portal Redirection

## Goal

A client device joins `SIGNAL_INFOHUB` and, within a few seconds, sees a
"Sign in to network" sheet that loads the SIGNAL landing page. No URL
typing, no instructions — the OS connectivity check finds the portal on
its own.

This is purely a redirect layer. The library, assistant, and notes board
land in Phase 3+.

## What was built

| Artifact | Path |
|---|---|
| Wildcard DNS line | `config/dnsmasq/signal.conf` (adds `address=/#/192.168.4.1`) |
| Nginx site | `config/nginx/signal-portal.conf` → `/etc/nginx/sites-available/signal-portal` |
| Portal page | `www/portal/index.html` → `/var/www/signal-portal/index.html` |
| Installer | `install.sh` (`phase2()`, default `PHASE=2`) |
| Uninstaller | `uninstall.sh` (removes nginx site + www) |

## How it works

1. **Wildcard DNS.** Every name a client looks up — `captive.apple.com`,
   `connectivitycheck.gstatic.com`, `www.msftconnecttest.com`, `google.com`,
   `whatever.example` — resolves to `192.168.4.1`.
2. **Default nginx server.** Every HTTP request, no matter what `Host:`
   header it carries, returns `302 Found` to `http://hub.local/`.
3. **OS sees a non-success connectivity probe.** That trips the
   captive-portal heuristic: Apple's CNA, Android's `CaptivePortalLogin`,
   and Windows NCSI all decide "this network needs sign-in" and open
   their captive browser pointed at the redirect target.
4. **hub.local nginx block** serves the static landing page.

HTTPS probes (e.g. `https://www.google.com/generate_204`) fail at the TLS
layer because we hold no cert for those names. That is intentional — it
causes most clients to fall back to their HTTP probe within a few seconds.
See [CROSS_OS_TEST_MATRIX.md](CROSS_OS_TEST_MATRIX.md) for per-OS detail.

## How to verify on a Pi Zero 2 W

From a fresh Phase 1 install (or a clean image):

```bash
git pull
sudo ./install.sh          # defaults to PHASE=2
```

Then on a phone or laptop:

1. **Captive sheet opens.** Join `SIGNAL_INFOHUB`. Within ~10 seconds the
   OS should pop a sign-in sheet showing the SIGNAL landing page. See the
   matrix for per-platform timing.
2. **Page loads at `hub.local`.** Open `http://hub.local/` in a browser
   — should serve the landing page directly (no redirect chain).
3. **Foreign hosts redirect.** `curl -v http://example.com/` from a
   connected client should return `HTTP/1.1 302 Found` and
   `Location: http://hub.local/`.
4. **Wildcard DNS works.** From a client: `dig @192.168.4.1 example.com`
   returns `192.168.4.1` as the A record.
5. **No egress.** `sudo iptables -nvL FORWARD | grep wlan0` still shows
   the Phase-1 DROP rule with traffic. Phase 2 does not change forwarding.

## Known limitations going into Phase 3

- **No HTTPS portal.** Hitting `https://hub.local/` returns a TLS error
  because nginx isn't serving 443. Acceptable for a captive portal; users
  will land via the captive sheet (HTTP) and follow the same-origin link.
- **Static page only.** No interactivity; no library; nothing to actually
  *do* on the hub yet. Phase 3 adds Kiwix + content.
- **Some Android builds keep an "Internet may not be available" badge** on
  the Wi-Fi connection even after the captive sheet closes. This is
  expected — Android marks any network that fails the HTTPS probe as
  non-internet, but local connectivity to `hub.local` still works.
- **iOS may cache the CNA dismissal** for a few minutes after the first
  sign-in. Re-joining the network usually re-triggers; "Forget this
  network" guarantees it.

## Rollback

```bash
sudo ./uninstall.sh
```

Removes the nginx site, deletes `/var/www/signal-portal`, restores the
stock default site if Debian's copy is still on disk, then unwinds Phase 1.

## Tag

`v0.2.0-phase2`
