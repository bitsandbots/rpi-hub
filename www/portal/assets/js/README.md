# Portal JS conventions

## Canonical `<noscript>` block

Every portal page that fetches data carries the same byte-identical
`<noscript>` snippet inside its intro section. The canonical copy is
below; if you change it on one page, change it on all of them or the
GAP §3a "drift risk" row re-opens.

```html
<noscript>
  <p style="max-width:36rem;margin:1rem 0;padding:1rem;background:#fff6e6;border-left:4px solid #b3640d;">
    This page polls a local API and renders results with JavaScript.
    Static fallback: visit <a href="/library/">/library</a> for the
    offline knowledge base.
  </p>
</noscript>
```

Pages that carry this block as of v1.2.1:
`ask.html`, `board.html`, `listen.html`, `peers.html`, `adsb.html`,
`status.html`. The landing page `index.html` deliberately does not —
its tile probes degrade gracefully without JS and the tiles
themselves are server-rendered links.

## Canonical service-down UX classes

Three classes, three roles. Pick the one whose role matches the state
you want to surface; do not invent a fourth.

| Class | Visual | Use for | Pages today |
|---|---|---|---|
| `.svc-status` | Inline one-line message, can toggle `.svc-status--error` (red) | Transient form feedback, loading states, "service unreachable" one-liners | `board.html` (form), `peers.html`, `adsb.html` |
| `.svc-fallback` | Soft padded card, supports `.btn` CTA | Service-down or no-result states where a workaround link helps the user (e.g. "Open the library") | `ask.html` (no-answer, error), `listen.html` (hw-missing) |
| `.ask-defer` | Heavy red-bordered card, `role="alert"`, structured (`__banner` / `__passage` / `__cta`) | Genuine alerts — assistant deferring to a verbatim safety passage, active NOAA SAME banner | `ask.html` (deferral), `listen.html` (NOAA banner) |

`status.html` is the deliberate exception: a page-wide
`.api-banner` covers the device-health outage case (documented at
`www/portal/status.html:88-95`). Per-page outages still use one of
the three classes above.

## Polling cadences

Each page picks its own poll interval. The rationale is in the
phenomenon being observed, not in any central config — so document it
here rather than in code, where the value would look arbitrary.

| File | Cadence | Why |
|---|---|---|
| `status.js` | 5 s | Matches the rpi-hub-status systemd watchdog cycle; faster polling would surface transient blips that the unit itself does not treat as failure. |
| `listen.js` | 5 s state / 15 s spectrum | State (tune, alerts) is user-facing and cheap; spectrum is a few KB of JSON and rarely changes shape between sweeps. |
| `peers.js` | 10 s | Peer churn is bounded by radio beacon cadence (LoRa ~30 s, Wi-Fi mesh ~10 s); polling faster would render the same table. |
| `board.js` | 8 s | Notes are ephemeral and low-volume; 8 s keeps the board feeling live without thrashing tmpfs reads. |
| `adsb.js` | 3 s | Aircraft positions move fast; dump1090 rewrites `aircraft.json` once per second, so 3 s is the slowest cadence that still feels live on the table. |

No page polls under 3 s — anything faster either wedges Pi Zero 2 W
class hardware under heavy fetch concurrency or duplicates work the
upstream service has already throttled.
