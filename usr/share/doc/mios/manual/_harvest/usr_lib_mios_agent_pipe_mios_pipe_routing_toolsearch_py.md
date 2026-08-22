<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Embedding TOOL/APP semantic-search core extracted verbatim from server.py (refactor R10 toolsearch wave). Owns the cosine-over-nomic-embed retrieval surface behind GET /v1/tool-search (verb + external-MCP-tool discovery, RAG-MCP progressive disclosure with namespace/tier filters + detail_level) and GET /v1/app-search (semantic match over the mios-apps inventory): the lazy fingerprint-keyed verb-embedding cache (_ensure_verb_embeddings) + its disk persistence (_load/_save_persisted_embeddings), the per-MCP-tool embedder (_mcp_embed_new_tools) + _tool_embedding lookup, and the app-inventory refresh/embed (_refresh_app_inventory). The two @app routes stay as THIN wrappers in server.py calling tool_search_logic/app_search_logic here. The cosine metric (_cosine) + the verb embed-text/fingerprint helpers (_verb_embed_text/_verb_embed_fingerprint) are OWNED here (native, maximally cohesive with the verb-embedding cache); only the per-vector embedder _embed_one stays server-resident (it drives the HTTP embed lane via _get_client) and is dependency-INJECTED via configure() alongside _VERB_CATALOG/_MCP_CLIENT_TOOLS/_MCP_CLIENT_LOCK/loads_lenient; this module NEVER imports server (one-way boundary, 98-drift-checks check 6). server.py re-imports every moved name under its original alias (and re-injects _cosine/_verb_embed_text/_verb_embed_fingerprint into the other planes that depend on them) so the importable surface is byte-identical.
AI-related: ./server.py, ./mios_config.py, ./mios_worker_tools.py, ./test_mios_toolsearch.py
AI-functions: _cosine, _verb_embed_text, _verb_embed_fingerprint, _tool_embedding, _mcp_embed_new_tools, _ensure_verb_embeddings, _load_persisted_embeddings, _save_persisted_embeddings, _refresh_app_inventory, tool_search_logic, app_search_logic, configure

<!-- mios-src:245f703cec87 from usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py:1-3 -->

