"""SQLite storage for the notes board.

The DB lives on tmpfs (mounted by the systemd unit) so a reboot wipes
state — that's the spec, not a bug. We still use WAL because the writer
runs in the FastAPI worker and a passing health probe shouldn't block
inserts.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

# Default location. The systemd unit mounts /run/rpi-hub-notes (tmpfs) and
# points BIND_DB at it. Tests use a tmp_path.
DEFAULT_DB = Path("/run/rpi-hub-notes/notes.sqlite")


@dataclass(frozen=True)
class Note:
    id: int
    created_ts: float
    name: str  # may be empty — display-name only, never an account
    text: str


def open_db(path: Path | None = None) -> sqlite3.Connection:
    if path is None:
        path = DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_ts REAL NOT NULL,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            ip TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS notes_created ON notes(created_ts);
        CREATE INDEX IF NOT EXISTS notes_ip_created ON notes(ip, created_ts);
        """
    )
    return conn


def insert(conn: sqlite3.Connection, name: str, text: str, ip: str) -> Note:
    now = time.time()
    cursor = conn.execute(
        "INSERT INTO notes (created_ts, name, text, ip) VALUES (?, ?, ?, ?)",
        (now, name, text, ip),
    )
    note_id = int(cursor.lastrowid or 0)
    return Note(id=note_id, created_ts=now, name=name, text=text)


def list_recent(conn: sqlite3.Connection, limit: int = 100) -> list[Note]:
    rows = conn.execute(
        "SELECT id, created_ts, name, text FROM notes "
        "ORDER BY created_ts DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        Note(
            id=int(r["id"]),
            created_ts=float(r["created_ts"]),
            name=str(r["name"]),
            text=str(r["text"]),
        )
        for r in rows
    ]


def delete_one(conn: sqlite3.Connection, note_id: int) -> bool:
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    return (cur.rowcount or 0) > 0


def wipe(conn: sqlite3.Connection) -> int:
    cur = conn.execute("DELETE FROM notes")
    return cur.rowcount or 0


def count_by_ip_since(conn: sqlite3.Connection, ip: str, since_ts: float) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM notes WHERE ip = ? AND created_ts >= ?",
        (ip, since_ts),
    ).fetchone()
    return int(row["n"]) if row else 0
