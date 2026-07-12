<!-- AI-hint: Design + research basis for MiOS agent-memory temporal weighting (recency decay) and the volatile-turn anti-stale-recall gate in the agent-pipe knowledge store/recall. Operator directive 2026-06-22: "data/time of requests should be weighed appropriately in an AIOS environment". Implemented in usr/lib/mios/agent-pipe/server.py (_recency_mult, _turn_volatile_var) + mios_pg.py (recall projection) + mios.toml [knowledge].
     AI-related: ../../../../usr/lib/mios/agent-pipe/server.py, ../../../../usr/lib/mios/agent-pipe/mios_pg.py, ../../../mios.toml, ../../../postgres/schema-init.sql -->
# Temporal weighting of agent recall + anti-stale-recall (2026-06-22)

**Operator directive:** *"data/time of requests should be weighed appropriately in
an AIOS environment — research properly."* Triggered by two live fabrication
failures via the `@`/`mios` CLI and OWUI:

1. **Stale cwd from recall.** `@ what folder are we in?` answered `/` ("retrieved
   from persistent cross-session memory") while the user had `cd afs` and was in
   `/afs`. A prior turn's cwd Q+A had been cached and resurfaced as current.
2. **Wrong-location local grounding.** Cobourg weather / local news grounded to
   New York / Chicago sources (a stale or unscoped snapshot).

Both are the **same root**: ephemeral, point-in-time facts (cwd, location,
weather, "latest" news) were stored as durable knowledge and recalled later as if
still true. The blended recall rank also had **no recency term** — the SSOT knob
`rank_age` existed but was `0.0` and never wired into `_blended`.

## Research basis (cited)

- **Generative Agents (Park et al. 2023)** — retrieval = `recency + importance +
  relevance` (all weights 1), where `recency = 0.995^(hours_since_last_access)`,
  min-max normalized; the recency clock **resets on access**.
  https://arxiv.org/abs/2304.03442
- **LangChain `TimeWeightedVectorStoreRetriever`** — `score = (1-decay_rate)^hours
  + similarity`, default `decay_rate=0.01` → half-life ≈ 69 h; `hours` from
  `last_accessed_at`, refreshed on retrieval.
- **Ephemeral vs durable** — the convergent pattern is a two-tier split: durable
  semantic facts persist; volatile/working state gets a TTL or stays session-only.
  OpenAI: *"Volatile or context-dependent preferences should remain as notes,
  often with recency weighting … or a TTL."* Anthropic **just-in-time**: keep
  references and **re-fetch live state via tools** rather than caching it. Zep /
  Graphiti **bi-temporal**: stamp `observed_at`, invalidate (don't overwrite)
  superseded facts, so *"the agent never has to choose between a stale and a
  current fact."*
- **AIOS reference kernel (Mei et al., 2403.16971, COLM 2025)** — the canonical
  AIOS Scheduler / Context Manager / Storage retrieval has **no recency / temporal
  weighting term at all** (recency appears only as LRU-K *eviction*, never in
  retrieval ranking). This is a genuine, citable gap MiOS now closes.

## Implementation (SSOT-gated, model-classified — no hardcoded keyword lists)

**1. Bounded multiplicative recency decay** (`_recency_mult`, both recall paths
— live pgvector `_recall_knowledge_pg` + the legacy datastore `_blended` fallback):

```
score = (cosine + w_outcome·outcome + w_hot·hot + w_access·log1p(access)) · M
M     = (1 − rank_age) + rank_age · 0.5^(age_days / recall_halflife_days)
```

Cosine stays **dominant**; recency only breaks near-ties toward fresher rows. With
`rank_age=0.3` a fully-stale row keeps 70% of its score (freshest ~1.43× edge —
the research-recommended floor). `rank_age=0` → `M=1.0` (inert/backward-compatible).
`age_days` from `last_access` (refreshed on recall, per Park/LangChain), fallback
`ts`. The live pgvector recall now fetches a **candidate pool** (not just top-K) so
the rerank has rows to reorder; `mios_pg.build_recall` projects `ts, last_access`.

**2. Volatile-turn anti-stale-recall gate** (`_turn_volatile_var`) — the keystone.
A turn the **refine model** classified as `local_state` / `news` /
`needs_location` (live system state, current-events, or location-bound) is a
point-in-time snapshot. Such a turn:
- **skips recall injection** (`_recall_knowledge` returns "" early) — answered from
  the **live env block + tools**, never cached memory; and
- **skips the durable store** (`_store_knowledge` returns early) — never persisted
  to poison a future recall.

This is **model-classified** (refine flags), not a query keyword check — honoring
the operator's binding "nothing hardcoded" rule. It fixes the cwd failure even
while a stale row still sits in the table (the recall is simply not consulted).

**3. "As of …" stamping** — every recalled row is labelled with how long ago it was
recorded (`_humanize_age`), and the recall header instructs the model to treat an
older stamp on any live-state claim as possibly STALE and re-verify — never assert
a recalled live value as current (Zep bi-temporal "as of").

**4. Location splice** — a location-sensitive web query (refine `needs_location`
PRIMARY, SSOT `[routing].location_sensitive_phrases` FALLBACK) gets the user's
**real resolved location** spliced into the search string, so the engine returns
local hits instead of generic/foreign ones.

## SSOT knobs — `mios.toml [knowledge]` / `[routing]`

| Knob | Default | Meaning |
|---|---|---|
| `rank_age` | `0.3` | recency-decay swing (0 = inert; floor = 1−swing) |
| `recall_halflife_days` | `7.0` | age at which half the swing is removed |
| `store_skip_volatile` | `true` | skip store+recall for volatile (model-classified) turns |
| `routing.location_sensitive_phrases` | 13 phrases | SSOT fallback behind `needs_location` |

## Verification (live, 2026-06-22)

- `@ what folder are we in?` (forwarded cwd `/mnt/c/MiOS/afs`) → *"We are currently
  in the folder `/mnt/c/MiOS/afs`."* Journal: `local_state=True` →
  `recall SKIPPED (live-only)` + `store SKIPPED (anti-stale-recall)`.
- `What is the weather and local news right now?` (location `Cobourg, ON, Canada`)
  → *"Current Weather in Cobourg, ON, Canada"* via Environment Canada /
  Northumberland News (local sources). Journal: `recall SKIPPED` + `store SKIPPED`.
