"""Best-effort propagation of new notes to rpi-hub-mesh.

When ``rpi-hub-mesh.service`` is running, every locally-posted note is
POSTed to ``/api/mesh/notes/publish`` so the mesh daemon can sign and
fan it out. When the mesh service is absent, the call fails fast (≤
50ms) and the note just stays local — exactly the design rule:
notes-board is the one write path, and it works whether or not the
mesh exists.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

MESH_PUBLISH_URL = os.environ.get(
    "rpi_hub_MESH_PUBLISH_URL", "http://127.0.0.1:8500/notes/publish"
)
MESH_PUBLISH_TIMEOUT_S = float(os.environ.get("rpi_hub_MESH_PUBLISH_TIMEOUT_S", "0.5"))


def publish(note_id: int, name: str, text: str, ttl_s: int = 86400) -> bool:
    """Try to push the note onto the mesh. Returns True on 2xx."""

    payload = json.dumps(
        {"note_id": note_id, "name": name, "text": text, "ttl_s": ttl_s}
    ).encode("utf-8")
    req = urllib.request.Request(
        MESH_PUBLISH_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=MESH_PUBLISH_TIMEOUT_S) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False
