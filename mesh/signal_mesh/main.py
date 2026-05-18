"""signal-mesh — FastAPI control plane on 127.0.0.1:8500.

Proxied by nginx at ``/api/mesh/``. The endpoint surface is small
because the actual radio I/O lives in the Reticulum daemon (LoRa) and
batctl/alfred (Wi-Fi mesh). This service owns identity, peer state, and
the trust UI; sub-phases 7.1–7.3 wire the radio layers into it.

Endpoints:

* ``GET /identity`` — local fingerprint + public key (for owner-to-owner trust setup)
* ``GET /peers``    — peer table
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
from pydantic import BaseModel, Field

from . import __version__, identity, peers

app = FastAPI(
    title="signal-mesh",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_PEERS = peers.PeerTable()
_IDENTITY: identity.Identity | None = None
OWNER_TOKEN_PATH = Path(os.environ.get("SIGNAL_MESH_TOKEN_FILE", "/etc/signal/notes-owner-token"))


def _get_identity() -> identity.Identity:
    global _IDENTITY
    if _IDENTITY is None:
        _IDENTITY = identity.load_or_create()
    return _IDENTITY


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


class HealthOut(BaseModel):
    version: str
    fingerprint: str
    peer_count: int


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    ident = _get_identity()
    return HealthOut(
        version=__version__,
        fingerprint=ident.fingerprint,
        peer_count=len(_PEERS.all()),
    )


@app.get("/identity", response_model=IdentityOut)
def get_identity() -> IdentityOut:
    ident = _get_identity()
    return IdentityOut(
        fingerprint=ident.fingerprint,
        public_key_b64=base64.b64encode(ident.public_key).decode("ascii"),
        version=__version__,
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
