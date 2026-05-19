# Portal JS — polling cadences

Each page picks its own poll interval. The rationale is in the
phenomenon being observed, not in any central config — so document it
here rather than in code, where the value would look arbitrary.

| File | Cadence | Why |
|---|---|---|
| `status.js` | 5 s | Matches the signal-status systemd watchdog cycle; faster polling would surface transient blips that the unit itself does not treat as failure. |
| `listen.js` | 5 s state / 15 s spectrum | State (tune, alerts) is user-facing and cheap; spectrum is a few KB of JSON and rarely changes shape between sweeps. |
| `peers.js` | 10 s | Peer churn is bounded by radio beacon cadence (LoRa ~30 s, Wi-Fi mesh ~10 s); polling faster would render the same table. |
| `board.js` | 8 s | Notes are ephemeral and low-volume; 8 s keeps the board feeling live without thrashing tmpfs reads. |
| `adsb.js` | 3 s | Aircraft positions move fast; dump1090 rewrites `aircraft.json` once per second, so 3 s is the slowest cadence that still feels live on the table. |

No page polls under 3 s — anything faster either wedges Pi Zero 2 W
class hardware under heavy fetch concurrency or duplicates work the
upstream service has already throttled.
