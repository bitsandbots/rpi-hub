"""Workstation-side index builder for the assistant.

The indexer reads ZIM files and produces the artifacts ``rpi-hub-retrieve``
serves at runtime::

    chunks.sqlite       # FTS5 + plain table
    vectors.hnsw        # HNSW graph (cosine)
    vectors.ids         # int32 array: HNSW label → chunk id
    manifest.yaml       # builder version, embedding model, chunk count

It never runs on the Pi: building Wikipedia-no-images requires a working
PyTorch / transformers stack and many GB of working RAM. The output
directory is rsynced to the Pi at ``/var/lib/rpi-hub/index/``.

This module exposes the *pure* helpers (chunking, manifest writing) so
they can be unit-tested without the heavyweight deps. The CLI entry
point :mod:`build_index` wires them up with embedding + HNSW build calls
that import optional libraries lazily.
"""
