<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### DAG execution entrypoints (refactor R8). Extracted VERBATIM...

DAG execution entrypoints (refactor R8).

Extracted VERBATIM from ``server.py`` -- the planned-DAG execution brain that
runs a topological DAG of agent/verb nodes with retry, grounding, work-steal
deepen and live per-node emit. The five execute_dag entrypoints
(``_execute_dag_node``, ``_execute_dag_saturated``, ``execute_dag``,
``_execute_dag_bounded``, ``_execute_dag_emitting``) are moved byte-identically;
their later consolidation is a SEPARATE task. ``server.py`` re-imports every name
under its original alias so the module's public surface is byte-identical.

Sibling functions (``_call_agent_complete``, ``_web_research_enrich``,
``_dag_levels``, the SSE node emitters, ``_env_grounding``, ``_action_hash``, the
RBAC filters, ``_toml_section``) are imported directly; every other server-side
symbol they touch (the config scalars, ``_AGENT_REGISTRY``, the ContextVars, the
broker ``dispatch_mios_verb``, the agent-call/scratchpad/db/a2a/worker-tool
helpers) is injected via :func:`configure` (one-way boundary -- this module never
imports ``server``).

<!-- mios-src:f74d2fcf415b from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:3-20 -->

### A fast swarm node that finished its primary BEFORE the...

A fast swarm node that finished its primary BEFORE the global barrier (i.e.
    it computed faster than its peers) keeps producing ADDITIONAL, DISTINCT
    coverage -- new angles / items / facets -- until the barrier fires (every
    node's primary done): it does NOT idle. The intent is "wait for ALL nodes to
    complete; the faster lanes just do another pass from ANOTHER facet -- everything
    concurrent, every source every turn". The slowest node trips the barrier and
    never enters here.

    EARLY-EXIT (A8, SSOT [dispatch].deepen_early_exit, default OFF): when enabled,
    each pass first asks the per-node Definition-of-Done judge whether the node's
    CURRENT answer already satisfies its sub-query; if so the node STOPS deepening so
    the heaviest compute is not spent re-answering an already-good node and the freed
    lane lets slower nodes finish sooner. Default off -> runs to the bound (no
    behaviour change). Degrade-open: the judge is bounded by DEEPEN_JUDGE_TIMEOUT_S
    and ANY timeout / error / absent judge falls THROUGH to the deadline-bound loop
    -- it can only ever STOP early on a clean 'satisfied', never under-compute.

 DETAIL-FILL ("also can loop to gather data in detail-fill
    passes"): when DEEPEN_FETCH is on AND the node carries a web-capable refined
    plan (a web/news turn), each pass FIRST fetches MORE web data on the facet
    (bounded by DEEPEN_WEB_TIMEOUT_S; the fan-out diversifies sub-queries so each
    pass surfaces fresh stories) and APPENDS the new stories to the shared
    grounding -- so the loop ENRICHES the facts, not just re-reasons them. The
    enriched grounding flows to the final synthesis. A non-web turn (no refined /
    no web hint) just reasons over the grounding in hand (no contention).
    Hard-bounded by DEEPEN_MAX_ITERS + DEEPEN_DEADLINE_S + the barrier.

<!-- mios-src:54837a11a10f from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:257-282 -->

### Execute ONE DAG node -- an `agent` delegation OR a `tool`...

Execute ONE DAG node -- an `agent` delegation OR a `tool` verb --
    and return its node_result (standard tool_call shape + node_id + _act).
    READS the shared maps (a snapshot of completed levels) but does NOT
    mutate them; execute_dag merges results after each level so concurrent
    same-level nodes never race on writes. ReWOO #E<id> refs in args (verb)
    or in the prompt (agent) resolve against the completed-level outputs.
    When `frag_q` is supplied (the streaming DAG paths), an agent node STREAMS
    its reasoning LIVE onto that queue as ("SF", name, fragment) events so the
    emitting wrapper renders the agents' actual thinking into the dropdown --
    not just engage/done status pings (operator: 'no thinking blocks').

<!-- mios-src:3e398e5884d3 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:500-509 -->

### CONTINUOUS READY-QUEUE DAG executor ("nothing in the...

CONTINUOUS READY-QUEUE DAG executor ("nothing in the
    pipeline is idle until synthesis"). A node dispatches the MOMENT its own deps
    finish -- NOT at a topological-LEVEL barrier -- so a fast node's lane picks up
    the next ready node immediately instead of idling for the slowest node in its
    level. REAL concurrency is bounded by the global/endpoint/lane semaphores in
    _call_agent_complete (saturate to capacity, never over). A finished AGENT node
    deepens until the GLOBAL barrier (all primaries done) so no lane idles while
    the swarm finishes. Same recording / emit / ReWOO-#E / dedup semantics as the
    level path; dependents of a FAILED node are SKIPPED (independent branches keep
    running -- more robust than the level path's whole-DAG fail-fast). Gated by
    SWARM_SATURATE.

<!-- mios-src:66cc141b875c from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:685-695 -->

### Execute the DAG. SWARM_SATURATE -> the continuous...

Execute the DAG. SWARM_SATURATE -> the continuous ready-queue
    (_execute_dag_saturated, "nothing idle until synthesis"); else the legacy
    concurrent topological-LEVEL path below (the proven fallback).

    LEVEL path: every node whose deps are satisfied runs in PARALLEL
    (asyncio.gather), so independent
    sub-tasks -- including agent-delegation nodes routed to DIFFERENT sub-
    agents -- run concurrently across the CPU + GPU lanes (operator
 "separate prompts per refinement step -> sub-agents...
    concurrent Compute"). A level only starts once all earlier levels
    finish, so ReWOO #E<id> refs always resolve. Reflexion-retries failed
    verb nodes; fail-fast when a level has an unrecoverable failure.
    Returns aggregate {success, node_results[], summary}.

<!-- mios-src:7878ed757105 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:825-837 -->

### Non-streaming execute_dag with a hard TURN_DEADLINE_S...

Non-streaming execute_dag with a hard TURN_DEADLINE_S wall-clock backstop
 (runaway fix) PLUS client-disconnect cancellation (T21,
) when `request` is provided: a non-streaming caller that hangs up
    stops the swarm IMMEDIATELY rather than churning DAG+deepen to the deadline.
    The STREAMING path self-bounds on disconnect in _execute_dag_emitting; this
    closes the non-streaming gap. On timeout/disconnect, wait_for/cancel stops the
    executor -> _execute_dag_saturated's CancelledError handler cancels in-flight
    node tasks so they stop dispatching. Returns a partial result. Degrade-open:
    request=None or REQUEST_CANCEL_ENABLE=false -> deadline-only (unchanged).

<!-- mios-src:2b3e11b58b95 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:976-984 -->

### Run execute_dag while LIVE-yielding per-node endpoint...

Run execute_dag while LIVE-yielding per-node endpoint emitter bytes
 ("endpoint emitters for each ai endpoint/node") AND
    the agents' streamed REASONING. Yields ("event", sse_bytes) as each DAG
    node ENGAGES + finishes, then a final ("result", dag_result). Agent nodes
    carry their registry endpoint / lane / model; verb nodes show 'verb
    · <tool>'. Agent nodes also stream their thinking ("SF", name, frag onto
    the shared queue) which is buffered per-agent and checkpoint-flushed as
    reasoning_content deltas -- so the think dropdown shows the facets ACTUALLY
    reasoning, not just engage/done pings (operator: "no thinking blocks
    populating it"). The 0.25s poll lets the drainer notice the DAG finishing
    even if the sentinel is lost to an unexpected raise -- then `await task`
    re-raises it (parity with a plain `await execute_dag`).

<!-- mios-src:64113c46dc5d from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:1026-1037 -->

### Pull the most-useful single field out of a JSON-ish blob so...

Pull the most-useful single field out of a JSON-ish blob so a
    ReWOO bare `#E<id>` ref doesn't paste the whole multi-line dump
    into a downstream arg. Trace failure: mios_apps returns NDJSON
    (one app per line). #En1 substituted the FULL stdout into
    open_app(name=...), producing args like
    `{"category":"linux-flatpak","name":"devel",...}\n{"...":"..."}\n`
    which mios-launch can't resolve to anything.

    Resolution order:
      1. Single JSON object -> prefer `name`, then `launch`, then
         `title`, then `id`, then `path`, then first string field.
      2. NDJSON (one object per line) -> use the FIRST object's
         best field via the same rule.
      3. Not JSON -> return the first line, capped at 1024 chars
         (matches the prior naive behavior for plain-text upstream).

<!-- mios-src:82521d11cd42 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:1143-1157 -->

### ReWOO-style substitution

ReWOO-style substitution: replace `#E<node-id>` tokens in arg
    values with the captured stdout of the upstream node. Two forms
    supported:

                           the upstream output (handles JSON objects
                           + NDJSON streams; falls back to first line
                           for plain text). Caps at 1024 chars.
                           JSON output. Use this when the planner
                           knows which field it needs (e.g.,
                           open_app(name='#En1.launch') to use the
                           launch line from a mios_apps row).

    Per ReWOO (Xu et al. 2023): the planner emits #E<id> placeholders
    and the worker substitutes them with actual outputs at execute
    time. Removes the per-step LLM re-plan that other frameworks
    need.

    Only handles string args (the common case for shell verbs).
    Object / list args pass through unchanged.

<!-- mios-src:9cfa00c17b14 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:1197-1215 -->

### AIOS gap5 L2

AIOS gap5 L2: dynamically size num_ctx to FIT the actual prompt+tool weight.
    FAST lanes: raise toward WORKER_TOOL_CTX_MAX only as needed (never shrink, never
    trim the contract). SLOW lanes: leave pinned at want_ctx (Layer 1 already shrank
    their surface). Returns num_ctx. Degrade-open: CTX_FIT off / any error ->
    want_ctx (today's static value).

<!-- mios-src:64e9b709a8ea from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:1257-1261 -->

### True only for a node on a FAST lane (DEEPEN_LANES...

True only for a node on a FAST lane (DEEPEN_LANES: dGPU/accelerator) -- the
    work-stealing lanes that do EXTRA coverage passes until the barrier (operator
 "dGPU and accelerators that compute faster should just do another
    pass from another facet"). A SLOW lane (CPU/iGPU/phone) does its ONE grounded
    pass and then its primary trips the barrier for the fast lanes; it must NOT
    deepen (it can barely finish one pass) -- the runaway/abandon source the
    operator hit with local-cpu.

<!-- mios-src:cf5656338a51 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:1274-1280 -->

### No-op on the /v1 plane. A llama.cpp / llama-swap generation...

No-op on the /v1 plane. A llama.cpp / llama-swap generation ABORTS the moment
    the client connection closes (unlike a legacy un-abortable backend), so a
    cancelled / deadline-exceeded turn releases the lane on its own -- there is no
    /v1 model-unload primitive to call and none is needed. Kept as a gated hook
    (RUNAWAY_REAP_ENABLE) should a future backend ever need an explicit reap; never
    raises into a turn.

<!-- mios-src:2244d79395b0 from usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py:1288-1293 -->
