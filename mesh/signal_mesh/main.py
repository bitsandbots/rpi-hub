"""signal-mesh — FastAPI control plane on 127.0.0.1:8500.

Proxied by nginx at ``/api/mesh/``. The endpoint surface is small
because the actual radio I/O lives in the Reticulum daemon (LoRa) and
batctl/alfred (Wi-Fi mesh). This service owns identity, peer state, and
the trust UI; sub-phases 7.1–7.3 wire the radio layers into it.

Endpoints:

* ``GET /identity``     — local fingerprint + public key (for owner-to-owner trust setup)
* ``GET /identity.svg`` — fingerprint rendered as a printable QR code
* ``GET /peers``        — peer table
* ``POST /peers/{fp}/trust`` {display_name} — owner action
* ``POST /peers/{fp}/block`` — owner action
* ``GET /health``
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import __version__, identity, lora_bridge, messages, peers, qrcode, wifi_bridge

app = FastAPI(
    title="signal-mesh",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_PEERS = peers.PeerTable()
_BUNDLE: identity.IdentityBundle | None = None
_OUTBOUND_SEQ = 0  # per-process monotonic; persists for the unit's lifetime
OWNER_TOKEN_PATH = Path(os.environ.get("SIGNAL_MESH_TOKEN_FILE", "/etc/signal/notes-owner-token"))


def _next_seq() -> int:
    global _OUTBOUND_SEQ
    _OUTBOUND_SEQ += 1
    return _OUTBOUND_SEQ


# Lazily-attached radio bridges. Each one is started on the first
# /health call (so test clients don't spin up threads) and reused.
# Both degrade silently when their hardware is absent.
_LORA: lora_bridge.LoraBridge | None = None
_WIFI: wifi_bridge.WifiBridge | None = None


def _on_lora_frame(frame: bytes) -> None:
    """Inbound LoRa frame → peer-table upsert.

    The frame is the canonical envelope bytes emitted by another
    signal-mesh node. The full dispatcher (notes / presence / index)
    lands with the Reticulum daemon wiring; here we just bump
    last-seen so peers show up in /api/mesh/peers.
    """

    try:
        import json as _json

        env = _json.loads(frame.decode("utf-8", errors="ignore"))
    except (ValueError, UnicodeDecodeError):
        return
    if not isinstance(env, dict):
        return
    sender = str(env.get("sender") or "")
    if not sender:
        return
    seq = int(env.get("seq") or 0)
    if not _PEERS.accept_sequence(sender, seq):
        return  # replay
    _PEERS.upsert(sender, radio="lora")


def _on_wifi_peer(mac: str, tq: int, _next_hop: str) -> None:
    """BATMAN-adv originator → mesh peer.

    The BATMAN MAC is the fingerprint surface for Wi-Fi peers — we
    store it with a "BAT:" prefix so the UI can distinguish from
    Ed25519 fingerprints. Cross-linking when the same node appears on
    both radios is a future improvement.
    """

    fp = f"BAT:{mac}"
    _PEERS.upsert(fp, radio="wifi", last_rssi=tq)


def _ensure_bridges() -> None:
    global _LORA, _WIFI
    if _LORA is None:
        _LORA = lora_bridge.attach(_on_lora_frame)
    if _WIFI is None:
        _WIFI = wifi_bridge.attach(_on_wifi_peer)


def _get_bundle() -> identity.IdentityBundle:
    """Cached identity + private-key bundle for this unit's lifetime.

    Reads from ``$CREDENTIALS_DIRECTORY`` under systemd (production),
    falls back to ``/var/lib/signal/keys/`` for dev. The private bytes
    only live in this process's memory — they are not on the filesystem
    from the daemon's point of view (signal-mesh.service has no
    ReadWritePaths / ReadOnlyPaths to the key dir).
    """

    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = identity.load_from_credentials()
    return _BUNDLE


def _get_identity() -> identity.Identity:
    return _get_bundle().identity


def _require_owner(token_header: str | None) -> None:
    try:
        expected = OWNER_TOKEN_PATH.read_text().strip()
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="owner moderation not configured",
        )
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="owner moderation not configured",
        )
    if not token_header or token_header != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class IdentityOut(BaseModel):
    fingerprint: str
    public_key_b64: str
    version: str


class PeerOut(BaseModel):
    fingerprint: str
    display_name: str
    trust: str
    last_seen_ts: float
    last_rssi: int | None
    radio: str


class PeersOut(BaseModel):
    peers: list[PeerOut]


class TrustIn(BaseModel):
    display_name: Annotated[str, Field(min_length=1, max_length=48)]


class RadioStatusOut(BaseModel):
    state: str
    detail: str
    last_change_ts: float


class HealthOut(BaseModel):
    version: str
    fingerprint: str
    peer_count: int
    lora: RadioStatusOut
    wifi: RadioStatusOut


class PublishNoteIn(BaseModel):
    note_id: int = Field(ge=0)
    name: str = ""
    text: Annotated[str, Field(min_length=1, max_length=400)]
    ttl_s: int = Field(default=86400, ge=60, le=604800)


class PublishOut(BaseModel):
    queued: bool
    radios: list[str]


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    ident = _get_identity()
    _ensure_bridges()
    lora_st = (
        _LORA.status
        if _LORA is not None
        else lora_bridge.LoraStatus(state="unavailable", detail="not attached", last_change_ts=0.0)
    )
    wifi_st = (
        _WIFI.status
        if _WIFI is not None
        else wifi_bridge.WifiStatus(state="unavailable", detail="not attached", last_change_ts=0.0)
    )
    return HealthOut(
        version=__version__,
        fingerprint=ident.fingerprint,
        peer_count=len(_PEERS.all()),
        lora=RadioStatusOut(state=lora_st.state, detail=lora_st.detail, last_change_ts=lora_st.last_change_ts),
        wifi=RadioStatusOut(state=wifi_st.state, detail=wifi_st.detail, last_change_ts=wifi_st.last_change_ts),
    )


@app.post("/notes/publish", response_model=PublishOut)
def publish_note(body: PublishNoteIn) -> PublishOut:
    """Sign + fan-out a note to whichever radios are available.

    Called by signal-notes whenever a local user posts. Loopback-only:
    nginx does not expose ``/api/mesh/notes/publish`` (the proxy block
    rewrites only /api/mesh/identity, /peers, /health). signal-notes
    hits the upstream on 127.0.0.1:8500 directly.
    """

    bundle = _get_bundle()
    seq = _next_seq()
    envelope = messages.make_note(
        sender=bundle.identity.fingerprint,
        seq=seq,
        priv=bundle.private_key,
        note_id=body.note_id,
        name=body.name,
        text=body.text,
        ttl_s=body.ttl_s,
    )
    import json as _json

    wire = _json.dumps(envelope.__dict__, sort_keys=True).encode("utf-8") + b"\n"

    radios: list[str] = []
    _ensure_bridges()
    if _WIFI is not None and _WIFI.publish(wire):
        radios.append("wifi")
    # LoRa outbound lands with sub-phase 7.2 once Reticulum's outbound
    # API is wired through the bridge.
    return PublishOut(queued=len(radios) > 0, radios=radios)


@app.get("/identity", response_model=IdentityOut)
def get_identity() -> IdentityOut:
    ident = _get_identity()
    return IdentityOut(
        fingerprint=ident.fingerprint,
        public_key_b64=base64.b64encode(ident.public_key).decode("ascii"),
        version=__version__,
    )


@app.get("/identity.svg")
def get_identity_svg() -> Response:
    """Fingerprint as a QR code, for the cross-hub trust workflow.

    A second owner scans this with any phone camera; their reader
    surfaces the fingerprint text, which they then paste into their
    own /peers page to mark our node trusted. The endpoint serves
    image/svg+xml so a fresh page (or print preview) can render it
    without JavaScript.
    """

    fp = _get_identity().fingerprint
    svg = qrcode.to_svg(fp, module_px=8, quiet=4)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=60"},
    )


@app.get("/peers", response_model=PeersOut)
def list_peers() -> PeersOut:
    return PeersOut(
        peers=[
            PeerOut(
                fingerprint=p.fingerprint,
                display_name=p.display_name,
                trust=p.trust.value,
                last_seen_ts=p.last_seen_ts,
                last_rssi=p.last_rssi,
                radio=p.radio,
            )
            for p in _PEERS.all()
        ]
    )


@app.post("/peers/{fingerprint}/trust", response_model=PeerOut)
def trust_peer(
    fingerprint: str,
    body: TrustIn,
    x_owner_token: Annotated[str | None, Header()] = None,
) -> PeerOut:
    _require_owner(x_owner_token)
    peer = _PEERS.mark_trusted(fingerprint, body.display_name)
    if peer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PeerOut(
        fingerprint=peer.fingerprint,
        display_name=peer.display_name,
        trust=peer.trust.value,
        last_seen_ts=peer.last_seen_ts,
        last_rssi=peer.last_rssi,
        radio=peer.radio,
    )


@app.post("/peers/{fingerprint}/block", response_model=PeerOut)
def block_peer(
    fingerprint: str,
    x_owner_token: Annotated[str | None, Header()] = None,
) -> PeerOut:
    _require_owner(x_owner_token)
    peer = _PEERS.mark_blocked(fingerprint)
    if peer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PeerOut(
        fingerprint=peer.fingerprint,
        display_name=peer.display_name,
        trust=peer.trust.value,
        last_seen_ts=peer.last_seen_ts,
        last_rssi=peer.last_rssi,
        radio=peer.radio,
    )
