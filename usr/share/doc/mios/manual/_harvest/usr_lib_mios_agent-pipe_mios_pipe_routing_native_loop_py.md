<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### NATIVE single-agent tool-loop responders (strangler-fig...

NATIVE single-agent tool-loop responders (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. ``_respond_native_loop_direct`` runs the
mios-heavy + full-tool-surface agentic loop (prefetch grounding -> secondary tool
loop -> failover -> polish -> relay ladder -> sources); ``_respond_local_state`` is
the deterministic local-READ fast-path. Both keep every heuristic/guard/comment
byte-identical. Sibling leaf helpers are imported directly; every server-side symbol
is injected via :func:`configure` (one-way boundary -- this module never imports
``server``). ``server.py`` re-imports both responders under their original aliases so
the importable surface stays byte-identical.

<!-- mios-src:b2a94ca96631 from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:3-13 -->

### Minimum candidate entities a section must carry before its...

Minimum candidate entities a section must carry before its grounding is
    judged; below this the signal is too thin to trust -> degrade-open. SSOT:
    [verity].antifab_min_entities -> MIOS_ANTIFAB_MIN_ENTITIES (live).

<!-- mios-src:8b66b16d3086 from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:69-71 -->

### FAB-01 guard body (extracted). SYNTHESIZED answer -> strip...

FAB-01 guard body (extracted). SYNTHESIZED answer -> strip all evidence
    blocks; RAW-evidence answer -> keep only success-JSON matching real tool
    output. Degrade-OPEN: disabled / empty / error -> return `ans` byte-identical.

<!-- mios-src:edb3339ecf0d from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:126-128 -->

### Structural, UNICODE-aware candidate entities (Law 7: NO...

Structural, UNICODE-aware candidate entities (Law 7: NO English word list).
    Bare registrable domains/hosts, digit-bearing tokens (years / versions /
    counts), and proper-noun-shaped word tokens (unicode upper-initial or all-caps).
    A caseless script (e.g. CJK) yields few/none -> callers see too-few entities
    and degrade-open rather than strip.

<!-- mios-src:9777487e9b59 from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:155-159 -->

### FAB-02 per-SECTION grounding. Split the answer structurally...

FAB-02 per-SECTION grounding. Split the answer structurally (blank lines +
    markdown heading boundaries) and drop ONLY a section that carries at least
    `min_entities` candidate entities AND whose grounded fraction (entities whose
    normalized form is a substring of the normalized fetched `corpus`) is below
    `ground_min`. A section with too few entities is always kept (degrade-open,
    covers caseless scripts). Returns (kept_text, stripped_any).

<!-- mios-src:27eedc41e152 from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:174-179 -->

### FAB-02 guard body (extracted). Degrade-OPEN: disabled /...

FAB-02 guard body (extracted). Degrade-OPEN: disabled / ungated / empty
    corpus / nothing stripped / error -> return `ans` unchanged. When it strips a
    fabricated section it keeps the grounded sections and appends `note` (a
    user-facing honest line -- output prose, NOT a decision gate).

<!-- mios-src:a0a4a5f4de9a from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:208-211 -->

### Inject server-side deps under their EXACT original names...

Inject server-side deps under their EXACT original names (one-way boundary).

    Called once from ``server.py`` after every injected symbol is defined. Each
    keyword equals the module global it sets; ``_worker_tools_core_cache`` is a live
    zero-arg getter for server's rebindable ``_WORKER_TOOLS_CORE_CACHE`` cache.

<!-- mios-src:45d7a7b2be09 from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:316-321 -->

### Have the micro-LLM EXTRACT the calculation the user is...

Have the micro-LLM EXTRACT the calculation the user is asking for as a short,
    self-contained Python 3 snippet that PRINTS the result (mirrors _formulate_web_query).
    The snippet runs PIPE-SIDE in the coderun sandbox so the answer is COMPUTED, not
    guessed. Code-only output; '' on empty/error -> degrade-open (no compute prefetch).

<!-- mios-src:b89be3241743 from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:1069-1072 -->

### For a HYBRID local+web turn, rewrite a vague...

For a HYBRID local+web turn, rewrite a vague SELF-referential question ("the
    theoretical specs of MY GPU") into a CONCRETE web query naming the components the
    local tools just IDENTIFIED -- so web_search finds the actual GPU/CPU spec pages,
    not dictionary definitions of "theoretical". Model-formulated (no templates);
    degrade-open to the raw user text on any error/empty (search still runs).

<!-- mios-src:8c1c0169397c from usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py:1104-1108 -->
