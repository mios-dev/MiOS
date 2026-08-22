<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_worker_tools (refactor R4 worker-tools reranker extraction). Pure stdlib, no server.py/DB/network/pytest. Drives the BM25/RRF/MMR ranking core through the configure() DI seam with a synthetic verb catalog + injected cosine: pins _tok tokenization, _ensure_verb_lexicon+_bm25 (a query scores the matching verb > a non-matching one, 0 for unindexed), _rank_positions ordering with stable-name tie-break, _fuse_then_diversify degrade-open paths (rerank-off / window-fits / confident-skip -> plain cosine top-n) and the greedy-MMR diversity pick (a near-duplicate high-cosine tool is dropped for a diverse lower-cosine one), plus _tool_priority/_priority_fallback_score/_is_core_tool. Deterministic; guards the extracted reranker so a later move can't silently change tool ordering/selection.
AI-related: ./mios_worker_tools.py
AI-functions: check, _cos, t_tok, t_bm25_lexicon, t_rank_positions, t_fuse_degrade, t_fuse_mmr, t_priority, t_priority_ssot, main

<!-- mios-src:c498ee96d0b2 from usr/lib/mios/agent-pipe/test_mios_worker_tools.py:1-4 -->

