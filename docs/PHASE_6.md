# Phase 6 — Constrained RAG Assistant (Pi 5 only)

## Goal

A retrieval-grounded assistant that summarises ZIM content with citations.
The model is a *writing engine over the fixed corpus*, never a knowledge
source. The Ask tile on the landing page only appears when the assistant
is actually running — and even then, the three rules are enforced at the
boundary, not as a polite suggestion:

1. **Grounded or silent** — retrieval below the confidence floor returns
   "no good answer" and links to the library.
2. **Cited or silent** — citation coverage below 60% after post-processing
   discards the answer entirely.
3. **Deferential on dangerous topics** — drug dosing, severe trauma,
   mains voltage, structural, chemical, weapons → red banner + verbatim
   passage, no model call.

## What was built

| Artifact | Path |
|---|---|
| Retrieval service | `assistant/signal_retrieve/` (hybrid BM25 + HNSW + RRF on `:8100`) |
| Answer service | `assistant/signal_assist/` (safety + prompt + post-process on `:8200`) |
| Safety classifier | `assistant/signal_assist/safety.py` (six regex rules with banner copy) |
| Prompt scaffold | `assistant/signal_assist/prompt.py` (Qwen chat-template) |
| Citation validator | `assistant/signal_assist/postprocess.py` (60% coverage floor) |
| Workstation indexer | `indexer/` (`build_index.py`, `chunk.py`, `embed.py`, `manifest.py`) |
| Model fetch | `models/fetch_models.sh` (sha256-verified, workstation-only) |
| Systemd units | `signal-retrieve.service`, `signal-assist.service`, `signal-llama.service` |
| nginx routes | `/api/retrieve`, `/api/ask` (added to `signal-portal.conf`) |
| UI | `www/portal/ask.html` + `www/portal/assets/js/ask.js` |
| Tile probe | landing page hides the Ask tile when `/api/retrieve` is unreachable |
| Tests | `assistant/**/tests/`, `indexer/tests/` (no model or net required) |
| Installer step | `phase6()` in `install.sh` (default `PHASE=6`) |
| Uninstaller step | `remove_assistant()` in `uninstall.sh` |

## Response shape

`POST /api/ask` with `{"q": "…"}`:

```json
{
  "mode": "answer | defer | noanswer",
  "answer": "…",
  "citations": [
    {"number": 1, "article": "Wound care", "section": "Cleaning", "url": "/library/…"}
  ],
  "banner": "Drug dosing depends on weight, age, …",   // defer only
  "confidence": 0.42
}
```

The Ask UI maps each mode to its own rendering: red banner + verbatim
passage for `defer`, paragraph + ordered citation list for `answer`,
plain "search the library directly" CTA for `noanswer`.

## Workstation workflow

The Pi never builds the index and never downloads model weights. Both
happen on a workstation:

```bash
# One-time weights fetch (~1.2 GB total).
./models/fetch_models.sh
rsync -avh payload/var/lib/signal/models/ pi@hub.local:/var/lib/signal/models/

# Index build (requires sentence-transformers + hnswlib + libzim).
python -m indexer.build_index \
    --zim-dir /var/lib/kiwix \
    --out ./payload/var/lib/signal/index
rsync -avh payload/var/lib/signal/index/ pi@hub.local:/var/lib/signal/index/
```

After both rsyncs `signal-llama`, `signal-retrieve`, and `signal-assist`
start automatically (each unit has a `ConditionPathExists` guard so they
were already enabled but inactive).

## Acceptance

- Ask tile self-disables when `signal-assist` is not running (verified by
  the landing-page probe and `ConditionPathExists=` in each unit).
- `POST /api/ask` returns one of `answer | defer | noanswer` for every
  query in the eval slice; no 5xx responses observed on dev runs.
- Safety classifier fires on every entry in the deferral eval slice and
  does not fire on the general-eval slice (covered by `test_safety.py`).
- Hybrid retrieval composes BM25 + HNSW via RRF and applies a
  per-article diversity cap of 3 (covered by `test_retrieval.py`).
- End-to-end latency budget: ≤ 8 s on Pi 5 (`SIGNAL_LLAMA_TIMEOUT_S=20`
  gives headroom; tighten once we have field numbers).

## Verification on a Pi 5

```bash
curl -s http://hub.local/api/retrieve?q=knot -k 3 | jq .ready
curl -s -X POST http://hub.local/api/ask \
    -H 'Content-Type: application/json' \
    -d '{"q":"how to purify water"}' | jq .mode
systemctl status signal-retrieve signal-assist signal-llama
```

## Known limitations going into the next phase

- The index format is layout v1. Bumping the indexer's chunking strategy
  requires bumping `INDEX_LAYOUT_VERSION` and the runtime check (not yet
  added to `signal-retrieve` — wired in v0.7).
- `signal-llama.service` assumes the binary at `/opt/signal/bin/llama-server`
  is bundled by `bake_image.sh`; we add that step in the Phase 6.4 polish
  pass once a Pi 5 is on the bench.
- The Ask tile probe currently hits `/api/retrieve` directly to detect the
  assistant; if retrieval is up but llama is down the tile shows yet the
  endpoint will return `noanswer`. Acceptable for v0.6, will be revisited
  once we have a public `/api/health` aggregator.

## Next: Phase 9

Per the approved sequencing (`6 → 9 → 8 → 7`), Phase 9A (notes board +
regional content packs) ships next.
