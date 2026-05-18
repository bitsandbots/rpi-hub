"""signal-assist — the answer-writing service on 127.0.0.1:8200.

Wires three layers together:

1. **Safety** (:mod:`safety`) — keyword + regex deferral list. Queries
   that match return a verbatim source passage with a red banner and no
   model call.
2. **Retrieval** — proxies the question to signal-retrieve at 8100.
3. **Model** (:mod:`llama_client`) — POSTs the prompt scaffold to a local
   llama.cpp server running Qwen2.5 1.5B Instruct (Q4_K_M). Output is
   post-processed (:mod:`postprocess`) to strip uncited claims and any
   model-invented URLs.

Three failure modes the endpoint handles by *not* answering:

* No retrieval results above the confidence floor → "I can't answer this
  reliably — open the library and search directly".
* Safety classifier hit → red banner + verbatim passage.
* Citation coverage below 60% post-processing → same as no-results.

The boundary stays in :mod:`main`; everything else is unit-testable
without a model or a network.
"""

__version__ = "0.6.0"
