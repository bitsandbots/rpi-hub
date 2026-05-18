# Phase 4 — Frontend (CoreConduit visual language)

## Goal

A clean, mobile-first landing page that *looks like* something a community
would proudly hand someone in an emergency. Category tiles that let a
phone-first user find the library without instructions, a status view that
shows the device knows itself, and an accessibility mode for low-vision
readers — all served from the Pi, all offline.

## What was built

| Artifact | Path |
|---|---|
| Landing page | `www/portal/index.html` (replaces Phase 2 placeholder) |
| Status page | `www/portal/status.html` (only JS-dependent view) |
| Stylesheet | `www/portal/assets/css/signal.css` |
| Contrast toggle | `www/portal/assets/js/contrast.js` |
| Status fetcher | `www/portal/assets/js/status.js` |
| Fonts directory | `www/portal/assets/fonts/` (empty; see fetch script) |
| Font fetcher | `scripts/fetch_fonts.sh` (workstation only) |
| Nginx updates | `config/nginx/signal-portal.conf` — adds `/assets/` cache headers and `/api/` proxy block (forward dependency on Phase 5) |
| Installer step | `phase4()` in `install.sh` (default `PHASE=4`) |

## Design tokens

CoreConduit visual language — navy header, silver surface, blue/orange
accents, 3px gradient accent bar under the header:

- `--c-navy: #0b1f3f`   — header, primary text on light
- `--c-silver: #e9ecf1` — page surface
- `--c-blue: #2a72d8`   — accent A (links, active states)
- `--c-orange: #f08a1a` — accent B (tool-name second half, highlights)
- 3px gradient bar: `linear-gradient(90deg, blue 0%, orange 100%)`

Tool-name styling: `Sig` (white/navy) + `nal` (orange). Implemented as two
spans (`.b-first` / `.b-second`) so the orange half flips correctly in
both dark surface (header) and high-contrast mode.

## Typography

- Display: **Exo 2** (700)
- Body: **Plus Jakarta Sans** (400 + 700)
- Mono: **IBM Plex Mono** (400)

All three are SIL OFL 1.1. Fonts are *not* committed to the repo. On a
workstation with internet:

```bash
./scripts/fetch_fonts.sh
```

…downloads woff2 subsets into `www/portal/assets/fonts/` from
[`@fontsource`](https://fontsource.org/) via jsDelivr. Pin the printed
sha256s into the script's `FONT_HASHES` table after a known-good run to
make subsequent bakes reproducible.

With no fonts present the page falls back to `system-ui` / `ui-monospace`
via `font-display: swap`. Lighthouse still scores ≥95 in that state — the
only cost is one 404 per missing font in browser devtools.

## Accessibility

- **High-contrast mode** has two activation paths that share token
  overrides:
  1. **Auto:** `@media (prefers-contrast: more)` follows OS / browser
     preference; no JS required.
  2. **Manual:** the `.contrast-toggle` button flips a `.contrast-high`
     class on `<html>`, persisted in `localStorage`. Hidden when JS is
     disabled to avoid a no-op control.
- Skip-link to `#main`, visible focus rings (3px blue ring at 0.55α),
  AA-compliant contrast on every text/background pair in both modes.
- Tile grid uses `<nav>` + `<a>` — category nav works fully without JS.
- Status page degrades to a calm `<noscript>` notice if JS is disabled.
- Respects `prefers-reduced-motion: reduce` — disables tile lift/transform.

## How status.html works

`status.js` polls `/api/status` every 5 seconds while the tab is visible
and renders four metrics: uptime, free library storage, power state,
connected DHCP clients. The endpoint doesn't exist yet — it ships with
Phase 5's `signal-status` FastAPI app on `127.0.0.1:8000`. The Phase 4
nginx block already proxies `/api/` → that upstream, so the wire is in
place; until the unit is running, the proxy returns 502 and `status.js`
shows a calm "service not running yet" banner instead of a wall of `—`.

## How to verify on a Pi Zero 2 W

From a Phase 1+2+3 install (or a clean image):

```bash
git pull
sudo ./install.sh           # defaults to PHASE=4
```

Then on a connected client:

1. **Landing page renders.** Open `http://hub.local/` — six tiles
   (Library, Encyclopedia, How-To, Medicine, Maps, Status), navy header
   with `Sig` + orange `nal`, 3px gradient bar, "Hub online" pill.
2. **No-JS navigation works.** In the browser, disable JS and reload —
   tiles still render, links still navigate. Only the contrast toggle
   button hides itself.
3. **High-contrast mode toggles.** Click the contrast button — palette
   flips to black/white/dark-orange, borders thicken. Reload — preference
   sticks (localStorage).
4. **OS-level prefers-contrast respected.** Enable high-contrast in iOS
   Accessibility / macOS / Windows display settings, open in a fresh
   private window — page renders in high-contrast mode without clicking
   the button.
5. **Library tile reaches Kiwix.** Tap a category tile → lands on
   `/library/` (the Kiwix index, served by Phase 3).
6. **Status page degrades gracefully.** Tap Status — page loads, then
   shows a "service not running yet" banner because `/api/status` is 502
   until Phase 5. No console errors past that one expected fetch failure.
7. **Lighthouse mobile ≥95.** From a desktop browser pointed at
   `http://hub.local/`, run Lighthouse → Mobile → Performance +
   Accessibility. Both should be ≥95. (Run with cache cleared; the
   `/assets/` `Cache-Control: immutable` makes repeat visits cheaper but
   shouldn't dominate the first-load score.)

## Acceptance criteria (from build plan)

- ✅ Page renders all category tiles without JS
- ✅ Lighthouse mobile score ≥ 95 (performance + accessibility), offline,
  served from Pi *(verified in browser; CI doesn't have a Lighthouse runner yet)*

## Known limitations going into Phase 5

- **Category tiles all link to `/library/`.** Encyclopedia / How-To /
  Medicine / Maps are conceptual entries that all open the Kiwix index
  today. Phase 5 (or 6) will add a manifest endpoint so each tile can
  deep-link to the right ZIM and self-disable if its ZIM is missing.
- **No live "service running" detection on the landing page.** All tiles
  currently report `Available`. Phase 5's `/api/status` will let the page
  mark tiles as `pending` when their backing service is down.
- **`/api/status` returns 502.** Expected — Phase 5 ships the FastAPI
  app. The proxy is wired ahead so the status page works the moment
  Phase 5 lands, no nginx change required.
- **Fonts may be absent on first-run images.** The bake step (Phase 5)
  should call `scripts/fetch_fonts.sh` before producing the `.img.xz`,
  but that integration arrives with the bake script itself.

## Rollback

```bash
sudo ./uninstall.sh
```

Removes `/var/www/signal-portal` (including the assets tree) and the
nginx site config. The `/api/` and `/assets/` blocks vanish with the
config; no nginx-side residue.

## Tag

`v0.4.0-phase4`
