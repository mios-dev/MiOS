<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: BM25/RRF/MMR tool reranker + tool-priority ranking helpers extracted verbatim from server.py (refactor R4 worker-tools wave). Pure, deterministic ranking core for the per-child tool surface: _tool_priority/_priority_fallback_score/_is_core_tool (weak-lane priority + RadixAttention stable-prefix core membership), _stable_name/_tok tokenizer, the lazy in-process BM25 lexicon (_ensure_verb_lexicon + module-owned _VERB_LEXICON/_VERB_LEXICON_LOCK) and Okapi _bm25, _rank_positions, and the stage-2 _fuse_then_diversify (cosine-rank RRF-fused with the BM25 lexical rank, then greedy-MMR diversify, degrade-open to plain cosine). The worker-surface BUILDERS/SELECTORS (_worker_tools_surface[_async]/_select_child_tools/_tool_pref_block) STAY in server.py because their caches (_WORKER_TOOLS_*_CACHE) are rebound at external invalidation sites -- rebindable scalars cannot be shared across the one-way module boundary. Server-side deps (_VERB_CATALOG, _resolve_verb_key, _cosine, _verb_embed_fingerprint, _verb_embed_text) and the rerank flags (TOOL_RERANK/RERANK_*) are dependency-INJECTED via configure(); this module NEVER imports server. server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./test_mios_worker_tools.py
AI-functions: _tool_priority, _priority_fallback_score, _is_core_tool, _stable_name, _tok, _ensure_verb_lexicon, _bm25, _rank_positions, _fuse_then_diversify, configure

<!-- mios-src:01709c0e2cba from usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py:1-3 -->

