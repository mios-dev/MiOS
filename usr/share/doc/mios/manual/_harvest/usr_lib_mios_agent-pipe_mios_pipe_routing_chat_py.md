<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### CHAT-COMPLETIONS router-brain (strangler-fig refactor...

CHAT-COMPLETIONS router-brain (strangler-fig refactor capstone).

Extracted VERBATIM from ``server.py``. :func:`chat_completions_logic` is the
per-turn orchestrator that routes a request through the precedence vision ->
client-tools -> OS fast-path -> trivial-chat -> memory/local-state -> native
loop -> multi-task -> council/swarm -> polish, keeping every heuristic, guard
and comment byte-identical. The dispatched responders are imported directly
from their siblings; every server-resident helper/scalar/ContextVar plus the
live verb catalog and agent registry are injected via :func:`configure` under
their exact original names (one-way boundary -- this module never imports
``server``). ``server.py`` keeps the route + ``chat_completions`` handler as a
thin wrapper reaching this logic through ``sys.modules`` so the importable
surface stays byte-identical.

<!-- mios-src:97d94589de0e from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:3-16 -->

### Inject server-side deps under their EXACT original names...

Inject server-side deps under their EXACT original names (one-way boundary).

    Called from ``server.py`` after every injected symbol is defined; re-called by
    ``_reload_membership`` with ``_AGENT_REGISTRY`` on a live agent add/drop. Each
    keyword equals the module global it sets; unknown keys are ignored.

<!-- mios-src:9a804c054c4c from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:285-290 -->

### Cap each system-prefix block for a SLOW lane ("add per-lane...

Cap each system-prefix block for a SLOW lane ("add
    per-lane context trimming") so a slow-prefill node (iGPU / phone / remote
    accelerator) finishes within its read budget instead of being abandoned
    mid-compute by the big ~7K pipeline web-research block. The gist survives
    (top stories / top RAG hits lead each block); the tail is dropped. gpu + cpu
    (local) keep the FULL prefix. Returns the list unchanged for a fast lane.

<!-- mios-src:a3e8a0e9c572 from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:329-334 -->

### Generate the conversational reply for an intent=chat turn....

Generate the conversational reply for an intent=chat turn.

    Separate from refine because the JSON classifier reliably tags chat
 but does NOT reliably emit a `reply` field (operator test
    greetings classified chat with reply=None -> the turn fell through to
    Hermes, which then tried a nonexistent 'chat' verb). think=False on
    the micro lane; plain prose, GENERATED in the user's language (never
    a canned/hardcoded string).

<!-- mios-src:a680be076e74 from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:383-390 -->

### Generative knowledge-gap judge ("use web tools for...

Generative knowledge-gap judge ("use web tools for
    knowledge gaps EVERY TURN"; NO keyword lists). For a LOCAL-STATE turn, decide
    whether FULLY answering ALSO requires facts that exist only OFF this machine --
    published/theoretical specs, benchmarks, capabilities, ratings, reviews, prices,
    or whether an installed version is the latest. Inspecting the machine yields its
    own identity/state (which GPU/CPU/app it HAS, live usage) but NOT such external
    facts, so a small model collapses "the theoretical specs of MY GPU" to local-only
    and then DROPS or FABRICATES the external half. A focused yes/no (constrained
    enum, thinking-off) is far more reliable than asking the big refine call to juggle
    local+web. True only on a confident yes; degrade-CLOSED (error/None -> False =
    unchanged pure-local behaviour, so 'what's open'/'list my games' never web-search).

<!-- mios-src:6650d49a0b9d from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:507-517 -->

### Write one row per refined multi-task entry to the CANONICAL...

Write one row per refined multi-task entry to the CANONICAL pg `kanban`
    table. Returns the same list augmented with `hermes_task_id` so the
    dispatcher + polish can refer to each row by id.

    WS-A3: this was the legacy `kanban_shadow` shadow-queue, which silently
    no-op'd once the legacy backend (:8000) was retired (and whose pg mirror targeted a
    `kanban_shadow` table that doesn't exist) -- so the multi-task queue was
    invisible. It now upserts the canonical pg `kanban` (id/title/status/detail
    jsonb) via a PARAMETERIZED statement (psycopg binds values; never spliced),
    giving every agent a single pg-visible queue. Hermes (or whichever sub-agent
    picks up a task) syncs its native kanban entry back via the existing path.

<!-- mios-src:55eb2de9c647 from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:560-570 -->

### Aggregate-budget admission for a NEW turn. Returns...

Aggregate-budget admission for a NEW turn. Returns (allowed, reason).

    HARD-HALTS (allowed=False) when the conversation OR the autonomous-source
    token ceiling is already exhausted within the window, or when the concurrent
    autonomous in-flight cap is reached. On ADMIT it debit-on-admits a
    conservative per-turn estimate to both relevant buckets and (for an
    autonomous turn with a turn_token) registers the turn in-flight -- so the
    NEXT turn for an exhausted bucket is refused, which is the runaway tripwire
    (it stops the SOURCE re-firing). DEGRADE-OPEN: any error -> allowed.

    The check is BEFORE this turn's real tokens are known; the rolling window
    ages the estimate out, so the ceiling bounds the RATE of turns per window.

<!-- mios-src:8ba7b380b78d from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:687-698 -->

### Drop an autonomous turn's in-flight token (best-effort...

Drop an autonomous turn's in-flight token (best-effort; degrade-open).
    Idempotent. The autonomous turn registers in-flight in _budget_admit; this
    is the PROMPT release for paths that have a clean terminal point. The
    leak-proof backstop is _budget_prune_inflight (TTL): the streaming path
    returns its generator BEFORE the turn truly ends, so there is no single
    reliable removal point in the giant handler -- the TTL guarantees no slot
    leaks even when no explicit release fires.

<!-- mios-src:f6dfbf590edb from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:735-741 -->

### OpenAI Responses API (Tier-2, additive). A THIN facade...

OpenAI Responses API (Tier-2, additive). A THIN facade: translates the
    Responses request to a chat/completions call against THIS server's own full
    pipeline (self-proxy -> reuse refine/route/swarm/polish, no duplication), then
    reshapes the answer into the Responses items model. /v1/chat/completions is
    untouched. Minimal v1: text/message `input` -> one output_text message item +
    usage; `instructions` -> a system message. Streaming/items/hosted-tools TODO.

<!-- mios-src:d1292eac08c0 from usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py:1433-1438 -->
