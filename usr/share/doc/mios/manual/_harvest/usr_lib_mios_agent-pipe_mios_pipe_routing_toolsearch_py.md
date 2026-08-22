<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Embedding-backed tool/app semantic search for the...

Embedding-backed tool/app semantic search for the agent-pipe surface.

Extracted verbatim from ``server.py`` (refactor R10). Holds the cosine retrieval
core for ``GET /v1/tool-search`` (native verbs + external MCP tools, RAG-MCP
progressive disclosure) and ``GET /v1/app-search`` (the installed-app inventory):
the lazy, fingerprint-keyed verb-embedding cache and its disk persistence, the
per-MCP-tool embedder, and the app-inventory refresh/embed loop. Both routes stay
in ``server.py`` as thin wrappers calling :func:`tool_search_logic` /
:func:`app_search_logic` here.

The cosine metric (``_cosine``) and the verb embed-text / fingerprint helpers are
owned here now (maximally cohesive with the verb-embedding cache). Only the
per-vector embedder ``_embed_one`` stays server-resident -- it drives the HTTP
embed lane via the injected client -- and is injected via :func:`configure`,
together with the HTTP client factory, the verb catalog, the MCP-client registry +
lock, and the lenient JSON loader. This module never imports ``server`` (one-way
boundary, 98-drift-checks check 6); ``server.py`` re-imports every moved name under
its original alias (and re-injects the cosine / verb-embed helpers into the other
planes that depend on them) so the importable surface is byte-identical.

<!-- mios-src:9775108b1e1e from usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py:3-22 -->

### Hash over every embeddable verb's (key, embed-text). Any...

Hash over every embeddable verb's (key, embed-text). Any rename / desc edit /
    example change flips it -> the persisted cache is rebuilt instead of serving stale
    vectors (the old gap-fill loader only added NEW verbs; it never noticed a changed
    description, so a re-described verb kept its old embedding forever).

<!-- mios-src:58734c591ff4 from usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py:119-122 -->

### Embed every registered MCP tool not yet in _MCP_EMBEDDINGS...

Embed every registered MCP tool not yet in _MCP_EMBEDDINGS (best-effort, off the
    hot path -- called at the end of a server probe). Degrade-open: an embed outage just
    leaves the tool on its name-keyword priority fallback, never breaks the surface.

<!-- mios-src:f9ef7e47179a from usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py:146-148 -->

### Find verbs + external MCP tools by natural-language query...

Find verbs + external MCP tools by natural-language query (cosine over the verb
    and MCP embeddings; substring fallback when embeddings are down). P3 progressive
    disclosure: optional `namespace` (e.g. browser_/duckdb_/pg_) and `tier`
    (core/common/rare) FILTERS to scope a large catalog, and `detail_level` --
    full (name+sig+desc+tier+namespace, the back-compat default) | brief (name+desc+tier)
    | names (name only) -- to trade tokens for breadth. Embeddings cached after first use.

<!-- mios-src:8ea023df4574 from usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py:498-503 -->
