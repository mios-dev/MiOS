<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for mios_toolsearch -- the embedding tool/app semantic-search core extracted from server.py (refactor R10). Stubs the injected deps (embed_one/cosine/verb catalog/MCP registry) with NO network or DB, pre-populates the module embedding caches so _ensure_verb_embeddings short-circuits, and asserts: cosine ranking + cap on /v1/tool-search, namespace/tier filters + detail_level shaping, external-MCP-tool inclusion, the substring fallback when embeddings are unavailable, _tool_embedding lookup precedence, and app_search_logic cosine ranking with _refresh_app_inventory stubbed.
AI-related: ./mios_toolsearch.py, ./server.py
AI-functions: _run, _cos, test_tool_search_ranks_and_caps, test_tool_search_filters_and_detail, test_tool_search_includes_mcp, test_tool_search_substring_fallback, test_tool_embedding_lookup, test_app_search_ranks, test_cosine_known_vectors, test_verb_embed_text_shapes, test_verb_embed_fingerprint_deterministic_and_stale

<!-- mios-src:169c51dead01 from usr/lib/mios/agent-pipe/test_mios_toolsearch.py:1-3 -->

