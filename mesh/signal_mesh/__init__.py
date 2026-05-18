"""signal-mesh — Reticulum + BATMAN-adv control plane (Phase 7).

Two-radio architecture, kept intentionally separate so a failure on one
plane doesn't take down the other:

* **LoRa via Reticulum** (RAK4631 or similar USB hat) — long-range,
  low-bandwidth notes propagation and signed presence beacons. Range:
  multi-kilometer line-of-sight.
* **Wi-Fi via BATMAN-adv** (second USB Wi-Fi adapter on a non-overlapping
  channel from the client AP) — neighbourhood-scale library *index*
  sync. ZIMs themselves never sync; the manifests do.

This service is the local control plane. It:

* generates an Ed25519 keypair on first boot at ``/var/lib/signal/keys/``
* maintains the peer list (last-seen, RSSI, trust state)
* signs outbound mesh messages and verifies inbound ones
* exposes ``/api/mesh/*`` for the peers UI

Mesh signature freshness uses per-node monotonic sequence numbers, not
wall-clock timestamps, because field nodes may have no time source.
"""

__version__ = "1.2.0"
