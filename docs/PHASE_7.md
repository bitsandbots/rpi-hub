# Phase 7 — Mesh Networking

## Goal

Two or more SIGNAL nodes form a self-healing mesh that shares the
library *index*, the notes board (with TTL + signature), and node
presence — **without ever requiring an internet uplink**. A single node
remains useful; a constellation of nodes is dramatically more so.

Two-radio architecture, intentionally kept separate so a failure on one
radio doesn't take down the other:

* **LoRa via Reticulum** (RAK4631 or similar USB hat) — long-range,
  low-bandwidth notes propagation and signed presence beacons.
  Multi-kilometer LOS, sub-kbps.
* **Wi-Fi via BATMAN-adv** (second USB Wi-Fi adapter on a non-overlapping
  channel from the client AP) — neighbourhood-scale library *manifest*
  sync. Mbit-class, but only line-of-sight.

## What was built

| Artifact | Path |
|---|---|
| Control plane | `mesh/signal_mesh/main.py` (FastAPI on `:8500`) |
| Identity | `mesh/signal_mesh/identity.py` (Ed25519, fingerprint 6×4 base32) |
| Peer table | `mesh/signal_mesh/peers.py` (trust state + replay protection) |
| Wire format | `mesh/signal_mesh/messages.py` (canonical JSON + Ed25519 signing) |
| Tests | `mesh/signal_mesh/tests/test_mesh.py` (identity, peers, sign/verify) |
| Systemd unit | `signal-mesh.service` (StateDirectory for keypair, ExecStartPre seeds it) |
| nginx route | `/api/mesh/` |
| UI | `www/portal/peers.html` + `www/portal/assets/js/peers.js` |
| Installer step | `phase7()` + `apt_install python3-cryptography` |
| Uninstaller step | `remove_mesh()` in `uninstall.sh` (keypair preserved) |

## What syncs / never syncs

| Syncs | Never syncs |
|-------|-------------|
| Library index pointers (manifest only, never ZIM bytes) | Client traffic |
| Notes-board entries with TTL (default 24 h) | Internet (no uplink, period) |
| Node presence + battery state | Identity data (only the public fingerprint is shared) |

## Identity & trust

* Ed25519 keypair generated on first boot at
  `/var/lib/signal/keys/ed25519.{priv,pub}` (priv 0600, pub 0644).
* Fingerprint format: SHA-256 of pubkey, first 15 bytes, base32, six
  groups of four characters (e.g. `AB12-CD34-EF56-GH78-IJ9K-LM0N`).
* The fingerprint is shown on `/peers.html`, on the SSH MOTD, and on
  `GET /api/mesh/identity` for owner-to-owner trust setup.
* Owner marks a peer trusted by hitting
  `POST /api/mesh/peers/<fp>/trust` with the owner token (the same
  token used by the notes board for moderation).

## Endpoints (proxied at `/api/mesh/...`)

```
GET   /api/mesh/identity                    → { fingerprint, public_key_b64, version }
GET   /api/mesh/peers                       → { peers: [{fingerprint, display_name, trust,
                                                          last_seen_ts, last_rssi, radio}, …] }
POST  /api/mesh/peers/{fp}/trust  {display_name}  → 200 PeerOut (owner-token required)
POST  /api/mesh/peers/{fp}/block             → 200 PeerOut (owner-token required)
GET   /api/mesh/health
```

## Wire format

All mesh messages share an envelope::

    { "kind": "presence|note|index",
      "sender": "<fingerprint>",
      "seq": <monotonic int>,
      "ts": <wall-clock advisory; not authoritative>,
      "body": {...},
      "sig": "<base64 Ed25519 over canonical(body)>" }

Replay protection uses per-peer monotonic sequence numbers — wall-clock
timestamps are advisory because field nodes may have no time source.

## Acceptance

- `signal-mesh.service` starts, ExecStartPre generates the keypair, and
  `GET /api/mesh/identity` returns a fingerprint within 1 s of unit
  start (covered by `phase7()` in install.sh's smoke probe).
- Peer table supports replay protection per peer (`test_mesh.py`).
- Sign/verify round-trip works in both the cryptography path and the
  stub fallback (`test_mesh.py`).
- Peers tile self-disables when `/api/mesh/identity` is unreachable.

## Known limitations (sub-phases shipped separately)

- **7.1 LoRa link layer** — the Reticulum daemon is not bundled in this
  commit. We ship the control plane that consumes its peer events; the
  Reticulum unit (`signal-reticulum.service`) lands once we have a
  RAK4631 on the bench to validate range numbers.
- **7.2 Notes propagation over LoRa** — `messages.make_note()` is
  ready; the daemon-to-control bridge wiring lands with 7.1.
- **7.3 Wi-Fi mesh index sync** — BATMAN-adv kernel module + batctl
  configuration ship as a follow-up after the Reticulum integration is
  stable.
- **7.4 Trust UI QR scan** — the page shows the local fingerprint as
  text. Adding a QR generator (server-side, since the browser shouldn't
  load remote libs) is a small follow-up; mark-trusted via the API
  works today.
- **7.5 72-hour three-node testbed** — requires three Pi 4/5 + LoRa
  hats + USB Wi-Fi adapters; the test plan lives in the build wizard
  and `docs/MESH_TESTBED.md` (a follow-up doc).

## Final port map (all phases shipped)

```
80/tcp    nginx           public          landing, /library, /api/*, /print
53/udp    dnsmasq         public          wildcard DNS → 192.168.4.1
67/udp    dnsmasq         public          DHCP
8000/tcp  signal-status   127.0.0.1       /api/status        (Phase 5)
8080/tcp  kiwix-serve     127.0.0.1       /library proxy     (Phase 3)
8100/tcp  signal-retrieve 127.0.0.1       /api/retrieve      (Phase 6)
8200/tcp  signal-assist   127.0.0.1       /api/ask           (Phase 6)
8201/tcp  llama-server    127.0.0.1       embedding model    (Phase 6)
8202/tcp  llama-server    127.0.0.1       generation model   (Phase 6)
8300/tcp  signal-listen   127.0.0.1       /api/listen        (Phase 8)
8400/tcp  signal-notes    127.0.0.1       /api/notes         (Phase 9A)
8500/tcp  signal-mesh     127.0.0.1       /api/mesh          (Phase 7)
```

Every internal service binds 127.0.0.1 only. The public surface is
always nginx on `:80`.

This is the v1.0 build.
