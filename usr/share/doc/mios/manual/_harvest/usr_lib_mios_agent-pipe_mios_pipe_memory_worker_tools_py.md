<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Tool-surface reranker

Tool-surface reranker: BM25 lexical arm + RRF fusion + greedy-MMR diversify.

Extracted verbatim from ``server.py`` (refactor R4). Holds the pure, deterministic
ranking core used to choose a sub-agent's intent-relevant tool subset: the
weak-lane tool-priority helpers, the lazy in-process BM25 lexicon over the verb
embed-text corpus, and the stage-2 retrieve->rerank (RRF-fuse cosine with BM25,
then greedy MMR), all degrade-open to plain cosine.

The worker-surface builders/selectors stay in ``server.py`` (their memo caches are
rebound at external invalidation sites). Server-side functions/catalog and the
rerank flags are injected via :func:`configure` -- this module never imports
``server`` (one-way boundary, 98-drift-checks check 6). ``server.py`` re-imports
every name under its original alias so the importable surface is byte-identical.

<!-- mios-src:187e7f82a46b from usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py:3-16 -->

### Rank a tool for the CAPPED surface a weak lane...

Rank a tool for the CAPPED surface a weak lane (iGPU/mobile) gets: the
    read/discovery tools a reasoning node actually needs come FIRST, so a small cap
    still yields a USEFUL toolset (every agent MUST get tools -- a weak device gets a
    CAPPED surface, never none). Lower = kept first.

    NO English name substrings: rank is driven by the verb's PERMISSION + the
    reranker's own core-tier signal (the RadixAttention stable-prefix set the module
    already classifies), both read from the verb catalog. rank-0 = the curated
    high-frequency READ verbs (perm=read AND tier=core) -- the SSOT replacement for
    the old keyword set. Degrade-open: when the core-tier signal is off/absent the
    read verbs fall to rank 1 (permission order alone), never a lexical gate.

<!-- mios-src:1479d1f92b97 from usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py:93-103 -->

### STABLE-PREFIX membership

STABLE-PREFIX membership: a tool belongs in the byte-identical core block iff
    its base verb is tier `core`. Intent-FREE + deterministic -> the core block never
    changes turn-to-turn (RadixAttention caches it). The `core` tier is the curated
    high-frequency set (~23: the *_search/web_* tools, system_status, mios_apps,
    launch/open, schedule, discord_send, tool_search). `common`/`rare` verbs, recipes,
    skills and MCP tools are NOT core -- they reach the model via the small per-turn
 cosine TAIL or tool_search (tier core+common == 69 tools drowned
    the 8B + regressed apps/recall selection; core-only == 23 keeps ~33 visible, near the
    working legacy 36). Reuses the existing `tier` field (no new catalog field).

<!-- mios-src:9f6fca09cf47 from usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py:134-142 -->

### P2 stage-2 over the cosine-sorted `scored` [(rel, tool...

P2 stage-2 over the cosine-sorted `scored` [(rel, tool, vec)]: over-fetch a top-K
    window, RRF-fuse the cosine rank with the BM25 lexical rank, then greedy-MMR diversify
    -> the top-n tools. DEGRADE-OPEN: rerank off / window already fits / confident cosine
    cut / any error -> the plain cosine top-n (never fewer than n).

<!-- mios-src:c8c5f24a5e86 from usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py:219-222 -->
