<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Tiered pgvector KNOWLEDGE memory

Tiered pgvector KNOWLEDGE memory: store + recency-weighted recall + eviction.

Extracted verbatim from ``server.py``. The store/recall/evict functions are
unchanged; ``server.py`` re-imports every name under its original alias so the
public surface is byte-identical. Pure eviction SQL/plan logic lives in
``mios_evict``; the Postgres+pgvector client is ``mios_pg``; the write-time
memory-poisoning scan is ``mios_memguard``. Every server-side runtime helper,
request contextvar and ``KNOWLEDGE_*``/``EMB_*`` config constant the moved code
reads is dependency-injected via :func:`configure` (one-way module boundary --
this module never imports ``server``).

<!-- mios-src:b382d8f44c00 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:3-13 -->

### Effective cosine floor for a recall query. A...

Effective cosine floor for a recall query. A self-referential ask about
    the user's own stored state (a possessive pronoun present) uses the LOWER
    preference floor, because the question template cosines below a stored
    statement of the same fact. Signal is purely structural (possessive present),
    never raises the floor above the default, and is tunable off by setting
    recall_pref_min_score == recall_min_score in mios.toml [knowledge].

<!-- mios-src:587d187df8ee from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:185-190 -->

### Bounded multiplicative recency factor in [1 - rank_age...

Bounded multiplicative recency factor in [1 - rank_age, 1.0] for a recalled
    row: 1.0 when brand-new, -> (1 - rank_age) as age >> half-life. rank_age == 0
    (default) -> 1.0 (inert). See KNOWLEDGE_RECALL_HALFLIFE_DAYS for the rationale.

<!-- mios-src:ec113ee80f31 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:247-249 -->

### Blended recall score SHARED by every tiered-recall path...

Blended recall score SHARED by every tiered-recall path (knowledge pgvector,
    knowledge legacy fallback, agent_memory) so the tiers rank CONSISTENTLY instead of each
    re-deriving the blend. Cosine SIMILARITY (the row's ``score``) stays dominant; the
    outcome / tier / access signals are each added with their ``[knowledge]`` rank_*
    SSOT weight, and the whole is scaled by the bounded recency multiplier
    (``_recency_mult``, driven by ``[knowledge]`` rank_age / recall_halflife_days). A
    stale-but-relevant hit still wins on cosine; the blend only re-orders near-ties.

    DEGRADE-OPEN: a row missing a signal column reads it as absent via ``.get()`` and
    that term contributes its NEUTRAL value (no ``satisfied`` -> outcome 0; no ``tier``
    -> hot 0; no ``access_count`` -> access 0; no ``last_access``/``ts`` -> recency 1.0),
    so a tier like agent_memory -- which carries only cosine + ts -- ranks on exactly
    the signals it has and never crashes. Any error falls back to pure cosine.

<!-- mios-src:6946733db188 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:263-275 -->

### Compact, auditable source list for a stored answer: the...

Compact, auditable source list for a stored answer: the verbs the
    turn invoked + any URLs they touched (web_search / web_extract args +
    result previews). A recalled answer then carries WHERE it came from
    instead of being an unattributed assertion.

<!-- mios-src:b69551e94a16 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:292-295 -->

### Persist a finished Q+A (with derived sources + a query...

Persist a finished Q+A (with derived sources + a query embedding for
    recall) to the global knowledge table, fire-and-forget. NEVER raises -- a
    storage failure must not affect the answer the operator already received.

    P2: `satisfied` (the turn's Definition-of-Done verdict, or None when not
    available in scope) is stored as an outcome signal the blended recall rank
    can weight. None -> the field is simply omitted (degrade-open).

<!-- mios-src:5ba13de2aac3 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:319-325 -->

### Embed the question (so recall is a cheap cosine) then write...

Embed the question (so recall is a cheap cosine) then write the row.
    Embedding is best-effort: a miss just stores the row without `emb` -- still
    persisted + auditable, just not semantically recallable.

    P2 tiering fields are seeded at write time: access_count/recall_hits at 0
    (so the page-in bump's `(field ?? 0) + 1` has a base + plain reads are
    NULL-safe), tier='warm' (neutral default; hot/cold transitions are a
    deferred P2 pass), and `satisfied` (omitted by _db_create when None).

<!-- mios-src:01a5b6733049 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:348-355 -->

### WS-9c native pgvector recall (used when...

WS-9c native pgvector recall (used when DB_BACKEND='postgres'). Returns the
    injectable block, '' on a clean miss, or None to fall through to the
    legacy fallback path on any error (degrade-open). #59 WS-5: scoped to the request
    principal when [pgvector].rls_mode == 'enforce' (else unfiltered).

<!-- mios-src:8c17e2b9c5e4 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:413-416 -->

### Semantic recall of PRIOR stored answers relevant to...

Semantic recall of PRIOR stored answers relevant to `query`: embed the
    query, cosine it against the query-embeddings of recent knowledge rows,
    return the top-K above a threshold as an injectable context block (or '' on
    miss). Best-effort, never blocks the turn -- the read half of the
 store/recall loop. Recalled answers are framed as
    PRIOR/own knowledge that may be outdated, never as fresh ground truth.

<!-- mios-src:c68cbcb0f334 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:478-483 -->

### WS-A3

WS-A3: best-effort COUNT over the EVICTABLE knowledge set via parameterized
    Postgres (mios_pg). Degrade-open -> 0. (Was SurrealQL via _db_post, which
    no-op'd under db_backend=postgres -> eviction never ran.)

<!-- mios-src:39fe6d2c33a2 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:582-584 -->

### One K-LRU + TTL eviction sweep. DRY-RUN (evict_enable off)...

One K-LRU + TTL eviction sweep. DRY-RUN (evict_enable off) only COUNTS +
    LOGS what it WOULD remove; otherwise it DELETEs (bounded by the batch).
    Degrade-open: any DB error -> no-op. Returns a small report (observability/
    tests).

<!-- mios-src:16c8e40746a6 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:626-629 -->

### 59 WS-5: the owner to scope knowledge recall to, or None to...

#59 WS-5: the owner to scope knowledge recall to, or None to disable
    filtering. Active ONLY when [pgvector].rls_mode == 'enforce' AND the chat
    surface forwarded a principal (user_name/user_email). Default ('off') -> None
    -> recall SQL is byte-identical to pre-RLS. Legacy/shared rows (owner_user IS
    NULL) stay visible (see build_recall), so flipping to enforce never blanks the
    existing single-user knowledge base. Degrade-open: any error -> None.

<!-- mios-src:a3f0971490c4 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:761-766 -->

### T-068

T-068: the owner fed to the DB-side `SET LOCAL mios.owner_user` -- the
    principal the chat surface forwarded for THIS request. This is the V2 owner only
    RECONCILED against the token-bound account when [security].principal_bind_mode=
    enforce; under the default 'off' (or 'verify') it is the raw, SPOOFABLE forwarded
    body/header `user`. Returns None when no principal was forwarded (single-user /
    daemon / seeding).

    UNLIKE _rls_owner (the app-side recall WHERE-filter, gated by [pgvector].rls_mode),
    this is UNGATED here: the DB-side SET LOCAL emission is gated INSIDE mios_pg, which
    emits it ONLY when [pgvector].rls_enable is on AND the principal is enforce-verified
    (mios_pg._owner_scope's P2-1 gate -- so an UNVERIFIED owner can never falsely DB-scope
    rows). Callers pass the best-known owner and mios_pg decides. None -> mios_pg emits
    no SET LOCAL -> the schema policy stays permissive (degrade-open: a system/daemon
    path is NEVER locked out).

<!-- mios-src:900dc25a2291 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:779-792 -->

### Semantic recall of the agent's SELF-EDITED durable facts...

Semantic recall of the agent's SELF-EDITED durable facts (agent_memory:
    fact/scope, written by remember/memory_update with embed-on-write). Embed the
    query, HNSW-cosine against the fact embeddings, return top-K above threshold
    as an injectable block (or '' on miss). Default-OFF; degrade-open -> ''.

<!-- mios-src:4ee216285bb7 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:803-806 -->

### Look up a phrase in the operator's PKG. Returns the first...

Look up a phrase in the operator's PKG. Returns the first
    matching app_install record as a dict, or None if no match.
    Tries alias first (operator-defined shortcuts), then a fuzzy
    short_name match on app_install.

<!-- mios-src:d57864a9d419 from usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py:850-853 -->
