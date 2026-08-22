<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### SWARM brain (refactor R8). Extracted VERBATIM from...

SWARM brain (refactor R8).

Extracted VERBATIM from ``server.py`` -- the multi-agent fan-out + synthesis
core. ``_agent_dag_from_tasks`` builds a CONCURRENT per-agent DAG from refine's
``multi_task`` array; ``_respond_agent_dag`` executes that DAG concurrently and
SYNTHESISES the agents' outputs into one polished answer. The nested
``_synthesise`` holds the anti-fabrication logic (raw research is the only ground
truth, honest-when-empty, punt-drop, closed-loop replan, audit envelope) moved
byte-identically. ``server.py`` re-imports both names under their original alias
so the importable surface is byte-identical; every server-side symbol is injected
via :func:`configure` (one-way boundary -- this module never imports ``server``).

<!-- mios-src:83210d579b3b from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:3-14 -->

### Re-route any DAG `agent` node assigned to a node that is...

Re-route any DAG `agent` node assigned to a node that is currently DOWN
    onto a LIVE agent, preserving swarm width under an outage (operator
 "iGPU is down"). Universal chokepoint: runs on the FINAL DAG
    regardless of which planner built it (multi_task / _plan_swarm / the
    decompose_intent fallback). Spreads like _agent_dag_from_tasks -- prefer an
    UNUSED live agent so the facets still fan out across DISTINCT engines, only
    reusing a live agent when none are left. The default agent (Hermes, dGPU) is
    never health_gate, so a live target always exists. Mutates nodes in place;
    returns [(node_id, from, to), ...] for the log/emit. No-op when `live` is
    empty/None (degrade open -- never strand a turn on a bad probe).

<!-- mios-src:e0e0e9e16b3e from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:200-209 -->

### Build a CONCURRENT per-agent DAG from refine's multi_task...

Build a CONCURRENT per-agent DAG from refine's multi_task array:
    one agent node per independent task, routed to the task's target_agent
    (a registry key as-is, else role-matched via _pick_agent, else the
    default agent), all deps=[] so they run in PARALLEL. This is refine's
    OWN decomposition -- each sub-task already carries a target_agent hint
    -- so no extra planner LLM call is needed. Realises the operator's
    "separate prompts per refinement step -> sub-agents ... concurrent
    Compute" directly. Returns {summary, nodes}.

<!-- mios-src:7c4653cf5dd7 from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:234-241 -->

### Execute a per-agent DAG concurrently and SYNTHESISE the...

Execute a per-agent DAG concurrently and SYNTHESISE the agents'
    outputs into ONE polished answer (multi_task -> parallel sub-agents).
    The per-node audit envelope rides the reasoning channel; the polished
    synthesis is the operator-facing answer -- same answer/dropdown split
    as the agent + council paths. Streaming emits LIVE per-node endpoint
 statuses as the DAG runs, before the synthesis.

<!-- mios-src:f651a0ddde80 from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:347-352 -->

### Empty-DAG safety net

Empty-DAG safety net : the swarm grounded nothing,
        so re-answer via the ALWAYS-UP light-lane native loop (it does its own web
        grounding + cites REAL urls). Returns (text, sources) on success, else
        (None, []) -> the caller keeps the original DAG `main`. Degrade-open: never
        raises, never recurses (the native loop never re-enters the DAG).

<!-- mios-src:d065a657be05 from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:610-614 -->

### CASUAL swarm grounding ("ridiculous runtimes"): run...

CASUAL swarm grounding ("ridiculous runtimes"): run
        web_search ONCE on the user query and inject the SAME grounding into EVERY
        agent node, so the nodes reason over shared facts instead of each running a
        redundant per-node web_search tool-loop (6 nodes re-searching the same
        single-intent query contended on the dGPU + SearXNG, so even hermes blew
        the per-node deadline). _web_research_enrich self-gates on the web signal,
        so a pure-local query is a no-op. Breadth preserved -- all nodes still fire,
        they just share ONE search. Nodes flagged _no_tools so they don't re-search.

<!-- mios-src:c89aab48459e from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:724-731 -->

### Dedicated SWARM decomposer ('AI SWARM', Layer B): a...

Dedicated SWARM decomposer ('AI SWARM', Layer B):
    a narrowly-scoped planner call that splits a request into independent
    {agent, task} assignments for CONCURRENT dispatch. More reliable at
    emitting AGENT assignments than the general verb-DAG planner (which
    skews toward verb nodes). Returns task dicts shaped for
    _agent_dag_from_tasks ({target_agent, refined_text, title}), or [].

    `history` (recent chat turns) is fed to the planner so a TERSE follow-up
    inherits the established subject instead of the model inventing one
 (a terse "do deep research on it" follow-up lost the
    subject established in prior turns and the planner fabricated unrelated
    routes + constraints that searched garbage).

<!-- mios-src:6527119da2be from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:885-896 -->

### Generate ADDITIONAL distinct sub-topic facets so each live...

Generate ADDITIONAL distinct sub-topic facets so each live node works its
 OWN angle instead of the backfill round-robining a handful (
    "diversify the backfill facets per node"). MODEL-generated -- NO hardcoded angle
    list; self-gates to [] when the request genuinely has no more real angles (a
    thin ask -> the backfill round-robins as before). Each item is a CLEAN
    web-search phrase (the TOPIC, not an imperative). Returns up to (target_n -
    len(existing)) NEW facets, deduped against the existing ones.

<!-- mios-src:d547878ece46 from usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py:979-985 -->
