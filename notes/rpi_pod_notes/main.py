"""rpi-pod-notes — FastAPI app on 127.0.0.1:8400.

Endpoints (all proxied by nginx under ``/api/notes``):

* ``GET  /notes``                — list recent notes (default 100, max 200)
* ``POST /notes``                — create one note (rate-limited per IP)
* ``DELETE /notes/{id}``         — owner-only; requires X-Owner-Token
* ``POST /notes/wipe``           — owner-only; wipe entire board
* ``GET  /health``               — readiness

Owner moderation uses a bearer token written to
``/etc/rpi-pod/notes-owner-token`` at install time. The token never
leaves the device — the status page surfaces it to the local owner
shell, never over Wi-Fi.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from . import __version__, mesh_client, rate_limit, storage, validation

app = FastAPI(
    title="rpi-pod-notes",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Per-domain owner token: this file gates DELETE + wipe on notes.
# rpi-pod-mesh has its own file (`/etc/rpi-pod/mesh-owner-token`) for peer
# trust/block actions so the two trust domains can be rotated
# independently. See OVERVIEW §5.5–5.6.
OWNER_TOKEN_PATH = Path(os.environ.get("RPI_POD_NOTES_TOKEN_FILE", "/etc/rpi-pod/notes-owner-token"))


def _owner_token() -> str | None:
    try:
        token = OWNER_TOKEN_PATH.read_text().strip()
    except OSError:
        return None
    return token or None


def _client_ip(req: Request) -> str:
    # nginx sets X-Real-IP; fall back to the direct peer for tests.
    forwarded = req.headers.get("x-real-ip") or req.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = req.client
    return client.host if client else "0.0.0.0"


def _require_owner(token_header: str | None) -> None:
    expected = _owner_token()
    if not expected:
        # No token configured = moderation disabled. The endpoint stays
        # closed in that case; 503 is more informative than 401.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="owner moderation not configured",
        )
    if not token_header or not secrets.compare_digest(token_header, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class PostNoteIn(BaseModel):
    # 400 > TEXT_MAX (280) intentionally: sanitise() strips control chars and
    # whitespace before the 280-char cap, so the model accepts raw input slack.
    text: Annotated[str, Field(min_length=1, max_length=400)]
    name: str = ""


class NoteOut(BaseModel):
    id: int
    created_ts: float
    name: str
    text: str


class NoteListOut(BaseModel):
    notes: list[NoteOut]


class HealthOut(BaseModel):
    ready: bool
    note_count: int
    version: str


_CONN: object | None = None  # process-wide handle; set on first request


def _get_conn() -> object:
    global _CONN
    if _CONN is None:
        _CONN = storage.open_db()
    return _CONN


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    conn = _get_conn()
    import sqlite3 as _sql  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)
    row = conn.execute("SELECT COUNT(*) AS n FROM notes").fetchone()
    return HealthOut(ready=True, note_count=int(row["n"] if row else 0), version=__version__)


@app.get("/notes", response_model=NoteListOut)
def list_notes(limit: int = 100) -> NoteListOut:
    limit = max(1, min(limit, 200))
    conn = _get_conn()
    import sqlite3 as _sql  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)
    notes = storage.list_recent(conn, limit)
    return NoteListOut(notes=[NoteOut(**n.__dict__) for n in notes])


@app.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def post_note(req: Request, body: PostNoteIn) -> NoteOut:
    text = validation.clean_text(body.text)
    if text is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty after sanitisation")
    name = validation.clean_name(body.name)

    conn = _get_conn()
    import sqlite3 as _sql  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)

    ip = _client_ip(req)
    verdict = rate_limit.check(conn, ip)
    if not verdict.ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=verdict.reason,
            headers={"Retry-After": str(verdict.retry_after_s)},
        )

    note = storage.insert(conn, name=name, text=text, ip=ip)

    # Phase 9.2 wiring: hand the note to rpi-pod-mesh for fan-out. This
    # is best-effort — the local board is the canonical store; the
    # mesh is icing. Failure is silent (the mesh service may be off,
    # or absent on this hardware) and never blocks the user.
    mesh_client.publish(note.id, note.name, note.text)

    return NoteOut(id=note.id, created_ts=note.created_ts, name=note.name, text=note.text)


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    x_owner_token: Annotated[str | None, Header()] = None,
) -> Response:
    _require_owner(x_owner_token)
    conn = _get_conn()
    import sqlite3 as _sql  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)
    if not storage.delete_one(conn, note_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/notes/wipe")
def wipe_notes(
    x_owner_token: Annotated[str | None, Header()] = None,
) -> dict[str, int]:
    _require_owner(x_owner_token)
    conn = _get_conn()
    import sqlite3 as _sql  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)
    return {"wiped": storage.wipe(conn)}
