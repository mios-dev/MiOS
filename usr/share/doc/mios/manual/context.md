<!-- AI-hint: Manual pages distilled from the source comments of context, sanitized, each passage anchored to the comment it came from. -->

# context

### mios_compact -- rolling-summary compaction planning (WS-A5...

mios_compact -- rolling-summary compaction planning (WS-A5, the AIOS
Context-Manager history-compaction layer).

Pure stdlib (measures tokens via mios_tokenize). server.py owns the actual
summary generation (an LLM call) + applying the plan; this module owns the
deterministic decision: given a history + a token budget, keep the most recent
messages (and pinned system messages) verbatim, and mark the oldest overflow for
summarization so the prompt fits.

Why keep-recent-verbatim
========================
Recent turns carry the live task state; summarizing them loses fidelity. Older
turns compress well into a rolling summary. So compaction always preserves the
last `keep_recent` non-system messages + every system message, and only the
OLDEST messages beyond the budget are folded.

<!-- mios-src:a51b0ea20546 from usr/lib/mios/agent-pipe/mios_pipe/context/compact.py:4-19 -->

### Decide the compaction split for `messages` under `budget`...

Decide the compaction split for `messages` under `budget` tokens.

    - System messages are kept verbatim when keep_system (they carry the
      contract/grounding).
    - The last `keep_recent` non-system messages are always kept (live state).
    - Older non-system messages are kept only while the running total fits the
      budget; the rest (OLDEST first) are marked to_summarize.
    needed=False (no-op) when the whole history already fits the budget.

<!-- mios-src:d0d1ebdb2522 from usr/lib/mios/agent-pipe/mios_pipe/context/compact.py:51-58 -->

### mios_ctxpack -- priority token-budget context packing...

mios_ctxpack -- priority token-budget context packing (WS-A5, the AIOS
Context-Manager assembly layer).

Pure stdlib (measures tokens via mios_tokenize). server.py owns WHAT the items
are (recalled knowledge, scratchpad checkpoints, tool previews, history) and the
budget; this module owns the SELECTION: keep the most important items that fit,
drop the rest, never exceed the budget.

Algorithm
=========
Stable greedy by priority: sort candidates by (priority desc, original-index
asc), admit each whose token cost still fits the remaining budget (skipping --
not stopping at -- an item too big to fit, so a smaller lower-priority item can
still be admitted), then re-emit the admitted set in ORIGINAL order. O(n log n).

<!-- mios-src:b1519b918772 from usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py:4-18 -->

### Select the highest-priority `items` whose total token cost...

Select the highest-priority `items` whose total token cost fits
    `budget - reserve`, returned in ORIGINAL order.

    text_of(item) -> str  (default: item["text"] for dicts, else str(item))
    priority_of(item) -> number, higher = keep first (default: item["priority"], else 0)
    reserve: tokens to hold back from the budget (e.g. for a system prompt).

<!-- mios-src:e1ff87b7b627 from usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py:51-56 -->

### Per-turn environment-grounding block builders (native <env>...

Per-turn environment-grounding block builders (native <env> system block).

Extracted verbatim from ``server.py``. Assembles the system-role grounding block
from host facts + config + the forwarded client/invocation environment. Every
function is moved byte-for-byte; ``server.py`` re-imports each under its original
``_``-prefixed name so the module's importable surface is unchanged.

Config constants come from ``mios_config``; the per-request ``_client_env_var``
ContextVar and the ``_current_date_str`` helper (both stay in ``server.py``) are
injected via :func:`configure` (one-way module boundary -- this module never
imports ``server``).

<!-- mios-src:371cad9fae1a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:4-15 -->

### A COMPACT live capability summary for identity grounding...

A COMPACT live capability summary for identity grounding: one line per
    catalog section listing the real verb names (from _VERB_CATALOG, i.e. the
    mios.toml [verbs.*] SSOT). The model then answers "what can you do?" from its
    ACTUAL tool surface instead of inventing capabilities. Names only + capped
    per section to keep the system block (and the RadixAttention stable prefix)
    short. Rare-tier verbs are omitted -- still dispatchable, just not advertised.
    No hardcoded English: re-derived from the catalog on every load.

<!-- mios-src:37a34aa81f04 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:64-70 -->

### One system-message block giving the agents the current...

One system-message block giving the agents the current date/time.

    The micros have no clock. Without this, relative dates ("tomorrow",
    "this weekend") were resolved by guessing off whatever dates appeared
    in retrieved text -- operator-flagged: "what's tomorrow at Tech Con"
    came back as TODAY's date and three other dates across one answer.
    This grounds the orchestrator's OWN system prompts (refine / polish /
    dispatch); it is NOT a pre_llm_call env-inject into the user message.

    Timezone/date/time come from the USER's Open WebUI client context when
    the pipe forwarded it (metadata.variables: CURRENT_TIMEZONE / CURRENT_DATE
    / CURRENT_TIME / CURRENT_WEEKDAY), so "today"/"tomorrow" match the
    OPERATOR's wall clock, not the server's (the VM is often UTC). Falls back
    to the process-local clock when no client context is present (Discord, raw
 API). "use detected environment details -- locations,
    timezones, locale, time".

<!-- mios-src:83b29bd77a9a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:104-119 -->

### The host's IANA timezone (e.g. 'America/New_York') -- a...

The host's IANA timezone (e.g. 'America/New_York') -- a REAL, always-
    available env detail (read once from /etc/localtime). Used as the coarse
    locale-of-last-resort for 'local' / 'near me' asks when no precise user
    location was forwarded or configured, so the agent grounds to the right
 REGION instead of fabricating unrelated cities (OWUI on
    phone answered 'local weather' for five random US cities, observing no env).

<!-- mios-src:1c1f53773b50 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:234-239 -->

### Client/session grounding -- the user's REAL location +...

Client/session grounding -- the user's REAL location + locale forwarded
    by the OWUI pipe (metadata.variables: USER_LOCATION / USER_LANGUAGE /
    USER_NAME). Like _temporal_grounding it grounds the orchestrator's OWN
    system prompts (refine / swarm / council / polish); NOT a pre_llm_call
    user-message inject. Returns '' when the client sent nothing (Discord, raw
 API, location-sharing off) so nothing is fabricated.
    "OWUI provides entire environment details ... USE them in the pipeline";
    the location is what lets 'near me' resolve instead of a placeholder.

<!-- mios-src:24eeb4ebff7a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:257-264 -->

### Non-negotiable identity grounding injected into EVERY...

Non-negotiable identity grounding injected into EVERY orchestrator prompt
    (refine / synthesis / polish / council / native-loop) via _env_grounding.

    The local backend models (granite/qwen) confabulate a cloud identity when
    asked "who are you / what model are you" -- a small model fills the gap with
    its training prior and claimed to "provide access to Claude (Fable 5 / Mythos
 5) with Constitutional AI" (operator-caught fabrication). MiOS is
    local-only; the /MiOS.md guard only reaches the native-loop path, so the
    verb-DAG synthesis/polish path needed its own copy. Kept terse + forceful;
    leads with the prohibition so it survives a long prompt.

<!-- mios-src:f835ba87f897 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:352-361 -->

### A fixed-shape, parseable <env> block of the LIVE per-turn...

A fixed-shape, parseable <env> block of the LIVE per-turn environment
 (research a small ~8B model reads structured key:value far more
    reliably than the prose helpers, which it routinely overrides). This is the
    CANONICAL 'every prompt env-grounded natively' mechanism -- a SYSTEM-role block
    refreshed each turn, NOT a pre_llm_call user-message inject (that is the banned
    hack). Values are LIVE this turn from the forwarded invocation env + host facts;
    an undetermined key is OMITTED (never fabricated). cwd/surface/location come
    ONLY from this turn's context, never recall. Reuses the SAME getters +
    location-chain as _client_grounding so the structured + prose views agree.

<!-- mios-src:ecf18a54098a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:433-441 -->

### Identity guard + self-architecture + temporal +...

Identity guard + self-architecture + temporal + client-environment grounding
    for the orchestrator's OWN system prompts (refine / synthesis / polish / swarm /
    council / native-loop). Single helper so every grounded prompt site threads the
    identity + arch + forwarded OWUI environment (time, timezone, location, locale,
    name) in one place. Leads with a STRUCTURED <env> block (research
    parseable key:value for small models) followed by the detailed prose guidance +
    anti-fabrication rules -- the prose is kept so nothing regresses.

<!-- mios-src:16c83df3c8e3 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:523-529 -->

### Resolve THIS request's bearer token to the account/owner...

Resolve THIS request's bearer token to the account/owner identity BOUND to its
    caller-key, or None when there is no token / no mapping / the resolver was not
    injected (degrade-open). The canonical shared + ingress keys resolve to the
    full-trust operator principal, which carries NO bound account -> None here, so a
    trusted gateway (OWUI) keeps speaking for its forwarded per-user identity. The
    per-key binding is the optional `account` (alias `owner`) field on the caller-key
    entry (see mios.toml [security].principal_bind_mode).

<!-- mios-src:dce689bf9d35 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:559-565 -->

### Normalise the per-request client/session context the OWUI...

Normalise the per-request client/session context the OWUI pipe forwards.

    Primary source is metadata.variables (OWUI's own convention; keys carry
    the {{ }} braces, e.g. "{{USER_LOCATION}}"). We also accept a top-level
    `variables` dict and directly-placed known keys (non-OWUI callers), plus
    the standard OpenAI `user` field as a last-resort display name. Returns a
    flat dict {location, timezone, date, time, datetime, weekday, language,
    user_name, user_email} with empty strings for anything not provided.

<!-- mios-src:fbeef67db77a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:583-590 -->

### Current 4-digit year. Prefers the USER's client date (the...

Current 4-digit year. Prefers the USER's client date (the env-detected
    value the OWUI pipe forwarded) so a query anchors to the OPERATOR's NOW,
    falling back to the live system clock. NEVER hardcode the year (operator
 "use env detect for current values for all AI functions / fall
    back to embedding the current year").

<!-- mios-src:462d85580302 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:737-741 -->

### mios_kvfork -- KV-cache FORK primitives for the MiOS...

mios_kvfork -- KV-cache FORK primitives for the MiOS agent-pipe (WS-8, the
AIOS context-manager "fork" capability that extends the existing demand-paging
KV layer, server.py `_kv_paging` / `_kv_slot_action`).

Purpose
=======
The llama.cpp /slots layer already lets us SAVE a conversation's KV to disk and
RESTORE it (`_kv_slot_action`). A SWARM that wants to branch several parallel
cognitive paths from a SHARED PREFIX (e.g. "from this researched context, spawn
3 sub-agents that each take a different angle") needs a FORK: copy a parent
conversation's saved KV file to a NEW child-conversation filename so each branch
pages in the same prefix independently and diverges without clobbering the
parent. That is the RadixAttention prefix-sharing workload, done on the cheap
disk-file prototype (no vLLM/LMCache yet).

Why this lives here (pure, DB-free, sibling module)
---------------------------------------------------
Pure stdlib (re / typing) so it unit-tests in isolation, in the
mios_sched / mios_evict / mios_hitl style. This module owns ONLY the reusable
mechanism: the filesystem-safe filename derivation (kept byte-identical to
server.py `_kv_filename` so a forked child's file is the one `_kv_paging` later
restores), the fork-request validation, and the SLOT-ACTION PLAN. server.py owns
the wiring (the SSOT flag, the async `kv_fork()` that drives `_kv_slot_action`
against a live llama.cpp endpoint, the contextvar, the /v1 observability).

llama.cpp has NO native "copy slot file" verb. A fork is therefore expressed as
a two-step plan over the EXISTING save/restore primitive:

    1. restore  <- parent file   (page the shared prefix INTO the slot)
    2. save     -> child file     (write the slot back out under the new name)

After step 2 the child conversation owns an independent KV file seeded with the
parent's prefix; subsequent turns on the child page IN that file and diverge.
The plan is data only -- the caller (server.py) runs it under the per-slot lock
so a concurrent conversation can't swap the slot between the two steps.

Everything degrades open: a malformed request returns a non-fatal reason and the
caller proceeds without forking (the child simply starts from a cold/empty KV,
exactly as it would today).

<!-- mios-src:6516b5d1056a from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:4-43 -->

### Validate a fork request. Returns (ok, reason). DEGRADE-OPEN...

Validate a fork request. Returns (ok, reason). DEGRADE-OPEN contract: the
    caller treats ok=False as 'skip the fork, proceed cold' -- never an error.

    Rejects:
      * an empty/None source or destination (nothing to fork / nowhere to put it)
      * a source and destination that sanitise to the SAME KV file (a self-fork
        is a no-op that would needlessly rewrite the parent's own file).

<!-- mios-src:962dc2464cfb from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:74-81 -->

### Build the ordered slot-action plan that forks `src_conv`'s...

Build the ordered slot-action plan that forks `src_conv`'s saved KV into a
    new file for `dst_conv`. Two steps over the existing save/restore primitive:

        ("restore", <src token>, <src file>)   # page the shared prefix IN
        ("save",    <dst token>, <dst file>)    # write the slot OUT under dst

    PURE: returns data only; the caller runs the steps (under the per-slot lock)
    via `_kv_slot_action`. Order matters and must be preserved. Call only after
    validate_fork() returns ok -- this does not re-validate (it sanitises, so a
    bad input yields a 'default'/'default' no-op plan rather than raising).

<!-- mios-src:2fb25ef2d788 from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:97-106 -->

### Collapse the two step results into one fork verdict. A fork...

Collapse the two step results into one fork verdict. A fork SUCCEEDS only
    if the SAVE landed (the child file now exists). A failed RESTORE is tolerated
    but noted: the child is then seeded from whatever was already resident in the
    slot rather than the intended parent prefix -- degraded, not fatal.

    Returns (forked, reason). `forked=False` => the caller should let the child
    start cold (its next turn pages in nothing, as today).

<!-- mios-src:1cbbaa9b2af5 from usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py:116-122 -->

### mios_kvgc -- KV slot-file GC planning (WS-A4, the AIOS...

mios_kvgc -- KV slot-file GC planning (WS-A4, the AIOS Context-Manager KV
lifecycle layer).

Pure stdlib. The agent-pipe pages each conversation's KV to disk and (WS-8) can
FORK a parent's KV into child files for a swarm fan-out. Without a GC those
files accumulate. plan_gc() is the deterministic decision: given the current
slot files (path/mtime/size), a TTL and a total-size cap, and a protected set
(the active slot / current conversation), return which to evict. The caller
deletes them (or relies on the tmpfiles age-out backstop).

<!-- mios-src:3d8f6b3bf4d6 from usr/lib/mios/agent-pipe/mios_pipe/context/kvgc.py:4-12 -->

### Decide which KV files to evict. files

Decide which KV files to evict.

    files: iterable of {"path": str, "mtime": float, "size": int}.
    ttl_s: evict any non-protected file older than this (0 -> no TTL pass).
    max_bytes: after the TTL pass, if the surviving total still exceeds this,
               evict oldest-first until it fits (0 -> no size cap).
    now: current epoch seconds (passed in -> pure/deterministic).
    protect: paths that are NEVER evicted (the active slot / live conversation).

<!-- mios-src:8a7d91922954 from usr/lib/mios/agent-pipe/mios_pipe/context/kvgc.py:41-49 -->

### P2.1 ("council not fan-out"): per-secondary role lens...

P2.1 ("council not fan-out"): per-secondary role
    lens prompt so a council DOES NOT send the same prompt to N models. Each
    secondary gets a small system message identifying its angle (its role +
    declared strengths from mios.toml [agents.*]) so the council answers from
    DIVERSE perspectives instead of duplicating one answer N times. SSOT-
    derived (no hardcoded per-agent text); empty when the agent has neither
    a role nor strengths -- harmless fall-back to identical-prompt mode.

<!-- mios-src:17120f99c511 from usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py:12-18 -->

### Render a compact system-message prefix from a refined plan....

Render a compact system-message prefix from a refined plan.
    Injected at the head of `messages` when proxying to a sub-
    agent so the agent receives MiOS-Agent's intent + suggested
    tools/skills/outcome -- NOT as free-form prose, but as a
    structured marker block the agent's own system prompt can
    parse.

    Format kept tight (~150-250 tokens) so even a 4K-context
    micro-model has plenty of room for the conversation itself.

<!-- mios-src:61db4666603a from usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py:96-105 -->

### Render a short user-facing preamble surfacing what's in the...

Render a short user-facing preamble surfacing what's in the
    queue. Goes at the TOP of the polished reply so the operator
    sees the queue state up front (and the polished response for
    the active task comes immediately below).

<!-- mios-src:5012dd72a750 from usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py:157-160 -->

### mios_promptver -- versioned registry for the agent-pipe hop...

mios_promptver -- versioned registry for the agent-pipe hop prompts (WS-LIFECYCLE-VER).

The completeness critic flagged it: MiOS versions skill/recipe PACKAGES (WS-A17)
but the LIVE refine/synthesis/polish/swarm/council/native-loop system prompts
carry no version stamp, no A/B, no rollback. That is the missing PREREQUISITE for
the self-improve ACT half (WS-11): you cannot safely auto-edit a prompt without a
way to identify the live version + roll it back.

This module is the PURE substrate:
  * content_hash() -- stable sha256[:12] of a prompt's text.
  * PromptRegistry.register(name, content) -- stamp a version that bumps ONLY on
    a content change (idempotent for an unchanged prompt); bounded history.
  * rollback(name) -- restore the previous content as a NEW (forward) version.
  * snapshot() -- content-free {name -> version/hash/len/history} for /v1/prompts.

server.py registers the live prompt constants at import + exposes the surface;
this owns the deterministic versioning logic.

<!-- mios-src:784582ea411c from usr/lib/mios/agent-pipe/mios_pipe/context/promptver.py:4-21 -->

### mios_tokenize -- the MiOS agent-pipe tokenizer seam (WS-A5...

mios_tokenize -- the MiOS agent-pipe tokenizer seam (WS-A5, the AIOS
Context-Manager token-accounting layer).

Pure stdlib so it unit-tests in isolation. Before WS-A5 the pipe estimated
tokens with bare `len(x) // 4` expressions duplicated across _fit_context, the
usage estimate, and several `[:N]` char slices -- inconsistent, and impossible
to upgrade to a real tokenizer in one place. This module is that one place.

Default backend
===============
HeuristicBackend implements the SAME ~4-chars/token approximation the pipe
already used (CHARS_PER_TOKEN = 4), so swapping the inline `// 4` for
count_text()/count_messages() is byte-for-byte behaviour-preserving.

The heuristic is a DELIBERATE, offline-safe default -- NOT a placeholder pending
a fix. The agent-pipe carries no tokenizer dependency (it must import + run with
pure stdlib, in CI and on a bare host), so the ~chars/token estimate is the
shipped measure. It is intentionally APPROXIMATE: token counts here size context
budgets and the client-visible usage estimate, where a few-percent error is
immaterial; they never gate correctness. When a real tokenizer IS provisioned
(tiktoken / a vendored HF tokenizer / the model's own tokenizer), an accurate
backend is registered via set_backend() -- the provided wiring seam -- without
editing any call site, and everything degrades back to the heuristic if that
asset is absent. server.py selects the backend from the [ai].tokenizer_backend
SSOT (only "heuristic" ships today; an unknown name logs + falls back).

<!-- mios-src:0758ca1a1d24 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:4-29 -->

### Exact OpenAI-BPE token counts via tiktoken (optional...

Exact OpenAI-BPE token counts via tiktoken (optional dependency). This is the
    OpenAI-native counter -- it matches what an OpenAI client expects from the usage
    object the pipe reports. Offline-safe: the encoding blob loads from the baked
    TIKTOKEN_CACHE_DIR (set here from the SSOT cache_dir when the process has not
    already set it), so no network is touched at runtime; with neither a cached blob
    nor network the constructor raises and the caller degrades-open to the heuristic.

    The encoding name is SSOT ([ai].tokenizer_encoding) -- never defaulted in code --
    so there is no restated literal here.

<!-- mios-src:4162f1ffe678 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:52-60 -->

### Install an accurate-count backend (must expose .name +...

Install an accurate-count backend (must expose .name + .count(text)->int) --
    the provided wiring point for an exact tokenizer once one is provisioned, so the
    heuristic default is an intentional seam, not a forgotten wire. Degrade-safe: a
    None/invalid backend is ignored (the heuristic stays), so calling this can never
    make measurement worse than the offline default.

<!-- mios-src:e64dc75cf6ee from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:115-119 -->

### Construct the token-counting backend named ``kind``, or...

Construct the token-counting backend named ``kind``, or None if it cannot be
    built (optional dependency or asset absent) so the caller degrades-open to the
    heuristic. NEVER raises.

    ``kind`` selects the IMPLEMENTATION via a small backend registry (a dispatch to
    code, like a plugin name -- NOT a content/keyword gate); the actual parameters
    (encoding / path / cache_dir) are SSOT-supplied ([ai].tokenizer_*). server.py
    owns the wiring: it reads the SSOT selector + params and installs the result via
    set_backend().

<!-- mios-src:ab2ca8730788 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:126-134 -->

### Estimated tokens of a chat prompt

Estimated tokens of a chat prompt: every message's content + (optionally)
    the serialized tool surface, measured through the ACTIVE backend.

    The contents + the tool JSON are concatenated and counted ONCE so a real
    tokenizer sees the full text (not a per-message char//N that would bypass it).
    Under the heuristic this is byte-identical to the pre-WS-A5 _fit_context estimate
    `(sum(len(content)) + len(json.dumps(tools))) // 4` -- len(concat)//4 equals
    (sum(len(content)) + len(tools_json))//4 because the parts are joined verbatim.

<!-- mios-src:be235b09b59c from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:166-173 -->
