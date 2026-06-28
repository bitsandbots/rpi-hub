"""rpi-hub-retrieve — hybrid BM25 + vector retrieval over the prebuilt index.

The index is *built on a workstation* (see ``indexer/``). The Pi only reads
it. This keeps the runtime memory budget bounded and the index
deterministic across deployments.

Public surface:

* ``GET /retrieve?q=...&k=8`` — returns ranked chunks with article metadata
  and a hybrid score. The endpoint is local-only (bound to 127.0.0.1) and
  reverse-proxied by nginx at ``/api/retrieve`` for the Ask UI.
* ``GET /health`` — readiness probe; reports whether the index is mounted
  and how many chunks it contains.
"""

__version__ = "0.6.0"
