<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Pipeline-side WEB-RESEARCH enrichment

Pipeline-side WEB-RESEARCH enrichment: search -> multi-engine fetch -> judge.

Extracted verbatim from ``server.py``. ``_web_research_enrich`` runs the FULL
web toolchain itself (SearXNG metasearch with fan-out, concurrent web_extract +
crawl4ai + Firecrawl fetch race, a 2-hop article-link drill) under a
MODEL-driven satisfaction gate (``_judge_satisfied``) that is the load-bearing
anti-fabrication Definition-of-Done -- it decides when enough REAL evidence was
gathered instead of letting the swarm fabricate. The functions are unchanged;
``server.py`` re-imports every name under its original alias so the public
surface is byte-identical. Every server-side runtime helper, request contextvar
and ``WEB_RESEARCH_*``/``_JUDGE_*`` config constant the moved code reads is
dependency-injected via :func:`configure` (one-way module boundary -- this
module never imports ``server``); ``_loads_lenient`` is imported directly from
``mios_jsonsalvage``.

<!-- mios-src:60fb92b4b206 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:3-17 -->

### Resolve the anchor stopword screen from SSOT: a CSV env...

Resolve the anchor stopword screen from SSOT: a CSV env override (rendered from
    mios.toml by the userenv slot map) -> the layered mios.toml [search].anchor_stopwords
    -> empty (degrade-open: no baked list in code, never over-filter). Lowercased.

<!-- mios-src:078abb7955e8 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:184-186 -->

### Resolve the article-link scorer's mode + weights/thresholds...

Resolve the article-link scorer's mode + weights/thresholds from SSOT
    (mios.toml [web_research]) layered over the degrade-open defaults. Each key
    falls back INDEPENDENTLY, so a partial or malformed [web_research] table still
    yields the byte-identical structural ranking for every key it omits. Never
    raises (degrade-open): any read/parse error returns the full defaults.

<!-- mios-src:3502bb52559d from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:244-248 -->

### Structural 'real-headline' ranker...

Structural 'real-headline' ranker (link_rank_mode='heuristic', the default).
    Scores each (anchor_text, url) candidate by URL STRUCTURE ONLY -- path depth, a
    long hyphenated headline slug, a date/id digit, and a long anchor -- with NO
    hardcoded domain/keyword/topic list. Every weight/threshold/cutoff/top-N comes
    from `cfg` (SSOT via _link_rank_cfg); the default `cfg` reproduces today's ranking
    byte-for-byte. Returns the top-N article URLs, score-descending.

<!-- mios-src:c560d3298e3d from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:274-279 -->

### OPT-IN embedding-cosine link ranker...

OPT-IN embedding-cosine link ranker (link_rank_mode='embed'). STUB: no
    embeddings client is reachable from THIS module today (the embeddings lane lives
    behind the agent-pipe broker, not imported here), so this returns None to
    DEGRADE-OPEN to the structural ranker. The hook exists so enabling model ranking
    is an SSOT flip + a wired embed client -- never a fabricated/invented path. A real
    impl would cosine each candidate's anchor/url text against the turn's topical
    `anchor` (or query) embedding and return the top-N URLs.

<!-- mios-src:4bd17b806e25 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:314-320 -->

### Rank candidate article links per the SSOT link_rank_mode....

Rank candidate article links per the SSOT link_rank_mode. Default 'heuristic'
    = the structural ranker. A non-default mode is tried first and DEGRADES OPEN to
    the structural ranker on a None result or ANY error (operator binding: a mode flip
    never breaks the drill).

<!-- mios-src:85514a343616 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:326-329 -->

### Pipeline-side WEB-RESEARCH loop ("the MiOS pipeline ITSELF...

Pipeline-side WEB-RESEARCH loop ("the MiOS pipeline
    ITSELF loops for web use and web tools"). For a web-needing turn the PIPELINE
    runs the web toolchain itself: SearXNG web_search WITH FAN-OUT (multiple
    diverse sub-queries) then web_extract the top result pages for their REAL
    text, over WEB_RESEARCH_PASSES drill passes. The fetched content is injected
    as grounding for EVERY agent (primary + reasoning-only secondaries), so the
    swarm answers from actual stories instead of shallow homepage snippets,
    regardless of any single agent's tool-loop depth. Best-effort + bounded;
    '' when disabled / not a web turn / nothing fetched.

<!-- mios-src:5dbc814c4c6d from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:357-365 -->

### Record real (title,url) pairs from a web_search/extract...

Record real (title,url) pairs from a web_search/extract result list into BOTH
    the turn-scoped contextvar bucket AND the module-level registry (keyed by the
    turn key) so the parent finalize sees sources collected by child agents too.
    Degrade-open: odd shape / no turn key -> safe no-op.

<!-- mios-src:f96ab7882d52 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:832-835 -->

### OpenAI url_citation annotations (Chat/Responses parity)...

OpenAI url_citation annotations (Chat/Responses parity): one
    {type:'url_citation', url, title, start_index, end_index} per cited source.
    start/end are char offsets into `text` where the URL appears inline (so a UI
    renders a clickable cite); 0/0 when the source is a turn-source not inlined.
    This is OpenAI's canonical citation contract -- attaching it lets MiOS clients
 render web citations the same way ChatGPT does. web-tools hardening.

<!-- mios-src:b306aaabfe61 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:904-909 -->

### OpenAI grounding rule

OpenAI grounding rule: 'include only search results/citations that support
    the cited response text -- irrelevant sources permanently degrade user trust.'
    Keep a source only when its title shares a content word (>=4 chars) with the
    answer/query, OR its registrable-domain stem appears in them. DEGRADE-OPEN: if
    the filter would drop EVERYTHING (the answer echoed no source token), return the
    originals -- never strip citations to empty. Kills the off-topic-source bleed
 (a Fedora answer citing 'Shaolin monks'). web-tools hardening.

<!-- mios-src:903c4a53bef3 from usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py:931-937 -->
