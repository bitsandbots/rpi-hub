"""rpi-hub-notes — the local-only ephemeral notes board (Phase 9A).

A tiny FastAPI service that backs the Board tile. Design rules baked
into the API surface, not enforced via convention:

* text only, ≤ 280 chars, plain-text rendering (URLs visible, never linkified)
* 1 post per IP per 60s, 10 posts per IP per hour
* ephemeral — SQLite lives in tmpfs, wiped on reboot
* owner-moderable via a token-gated DELETE endpoint
* optional profanity filter (off by default)
* if rpi-hub-mesh is running, notes propagate with TTL + signature
  (wired in Phase 9.2 once mesh lands)
"""

__version__ = "0.9.0"
