"""rpi-hub-listen — RTL-SDR receive-only service (Phase 8).

Three sub-tiles in the Listen UI map to three modes the service can run
in at any time. The dongle is a single resource — exactly one mode is
active at a time, arbitrated here, not by killing rtl_fm and praying.

* **Weather** — parked on a NOAA WX frequency, decoding SAME alerts
  (EAS messages). The killer feature: when an alert lands it's pinned
  to the landing page for every connected phone and propagated to mesh
  peers if Phase 7 is active.
* **Broadcast** — FM band, presets and free-tune. Streams audio to the
  browser over WebSocket.
* **Bands** — ham band scanner, ADS-B (Pi 4/5 only), APRS.

Transmit is intentionally not available. The hardware (RTL-SDR Blog v4)
is receive-only by design.
"""

__version__ = "1.3.0"
