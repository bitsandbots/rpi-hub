"""rpi-POD assistant — retrieval-grounded answer service (Phase 6).

Two FastAPI apps live under this package:

* ``rpi_pod_retrieve`` (port 8100) — hybrid BM25 + vector retrieval over the
  workstation-built index in ``/var/lib/rpi-pod/index/``.
* ``rpi_pod_assist`` (port 8200) — wraps retrieval with a safety classifier,
  prompt scaffold, and llama.cpp HTTP client. Strips uncited claims before
  returning text.

The three rules are non-negotiable:

* **Grounded or silent** — no retrieval above threshold → refuse, link manual
  search.
* **Cited or silent** — every claim maps to a retrieved passage.
* **Deferential on dangerous topics** — drug dosing, severe trauma, high
  voltage, structural, chemical: verbatim passage + red banner, no model
  call.
"""
