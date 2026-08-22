<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_agentreg -- agent/node registry builders (R3...

mios_agentreg -- agent/node registry builders (R3 strangler-fig extraction).

Verbatim move of the mios.toml [agents.*] / [nodes.*] registry parsers out of the
server.py monolith. Pure config readers + constants come straight from
mios_config; the few server.py runtime symbols these parsers touch
(_is_remote_endpoint, _opt_int_mb, the logger, CATALOG_FAIL_MODE,
NODES_RESEARCH_ONLY) are injected once via :func:`configure` AFTER they are
defined in server.py. server.py keeps the module-load assignment of the result to
_AGENT_REGISTRY and the node-pool injection -- these functions only BUILD the
dict, they never own it.

<!-- mios-src:37e05abb35dc from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:3-13 -->

### Inject the server.py runtime helpers/flags the registry...

Inject the server.py runtime helpers/flags the registry builders + helpers read.

    Called from server.py possibly MORE THAN ONCE with a partial set: the builders'
    deps are injected as soon as they are defined, while the helpers' deps (the hot
    _AGENT_REGISTRY, _agent_binding / _endpoint_key, the EFFORT_DEFAULT / SWARM_MAX_WIDTH
    scalars and _ROLE_SYSTEM_DIR) are injected later -- once defined -- and _AGENT_REGISTRY
    is re-injected on a live membership reload (it is reassigned there). Each field gates
    on ``is not None`` so a partial call never clobbers an already-injected dep.

<!-- mios-src:332f18ec24ab from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:46-53 -->

### Fold an agent's bindings into an {engine: {endpoint...

Fold an agent's bindings into an {engine: {endpoint, model}} map.
    Precedence (low -> high): the primary endpoint/model as the agent's HOME
    engine (its lane, or 'gpu'); the legacy cpu_endpoint/cpu_model as
    engines['cpu']; explicit [agents.<name>.engines.<engine>] tables WIN. So
    legacy 2-lane configs keep working unchanged AND any agent can declare a
    binding on any engine. iGPU stays DISTINCT from cpu here (the operator lists
    it as its own engine), though _agent_lane still collapses them for fan-out
    diversity.

<!-- mios-src:413616d20c40 from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:83-90 -->

### Parse mios.toml [agents.*] sections into a registry dict....

Parse mios.toml [agents.*] sections into a registry dict.
    Returns {name: {endpoint, model, role, default, strengths}}.
    Read at module load + cached -- operator restarts agent-pipe
    to pick up changes (same pattern as ports/security/...).

    Fallback: when the TOML can't be read or has no [agents.*],
    returns a single hermes entry pointing at MIOS_AGENT_PIPE_
    BACKEND so the legacy path still works.

<!-- mios-src:f55f6f03ffff from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:112-119 -->

### Synthesise ONE canonical research-worker agent PER compute...

Synthesise ONE canonical research-worker agent PER compute NODE from the
 mios.toml [nodes.*] table -- "don't have separate CPU
    1,2,3 / dGPU 1,2,3 replicas -- there should just be a MiOS Modelfile dispatched
    as many times as needed to ANY node(s)".

    ONE canonical brain x N nodes -- not N hand-partitioned per-lane research
    workers, and never a raw base model (a raw base cold-loaded on a CPU-only lane
    was the loadavg runaway). Each [nodes.<name>] declares an endpoint + a CANONICAL
    Modelfile tag (mios-agent on GPU, mios-agent-cpu on CPU/light, mios-igpu) +
    lane; we inject `node:<name>` into the registry with research_only defaulting to
    the SSOT NODES_RESEARCH_ONLY and fanout=true, so
    the EXISTING capacity-aware fan-out / swarm-DAG logic (_pick_fanout_agents /
    _agent_dag_from_tasks, bounded by the P1 admission controller + per-lane / per-
    endpoint semaphores) dispatches the ONE worker brain across the pool by
    capacity. Mirrors the a2a:<pid> synthetic-agent injection.

    Layered read (vendor <- /etc <- ~/.config) via _toml_section so the operator
    overlay adds real REMOTE node endpoints (potato/phone/cluster) without baking
    tailnet IPs into the public vendor file. Degrade-open: no [nodes.*] -> 0 nodes
    injected, registry unchanged. Returns the count injected.

    Per-node fields (all but endpoint optional):
      endpoint    -- OpenAI /v1 URL; EMPTY = inert node, skipped.
      model       -- canonical Modelfile tag the node serves (default mios-agent).
      lane        -- gpu/cpu/igpu/mobile/... (semaphore + fan-out diversity bucket).
      health_gate -- true for a come-and-go remote node (auto-join/drop); local
                     nodes omit it (always live). Defaults true for non-local lanes.
      fanout      -- fan-out opt-out (default true).
      role/job/strengths -- optional metadata; sensible worker defaults applied.
    The light-lane model is additionally force-capped to the micro model at
    dispatch by _cap_cpu_lane_model (belt + suspenders).

<!-- mios-src:ee1a20c489d8 from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:185-215 -->

### Resolve an agent's COMPUTE LANE -- the distinct hardware it...

Resolve an agent's COMPUTE LANE -- the distinct hardware it runs on:
    'gpu' (the dGPU/4090), 'cpu' (the in-VM CPU), 'igpu' (an iGPU, e.g. the
    Windows llama.cpp node :11436), 'accelerator', or 'mobile' (a client node).
    DISTINCT lanes do NOT contend, so the council fires one agent PER LANE
 CONCURRENTLY and each gets its own _lane_sem ("iGPU
    fires WITH CPU cores as well as the rest of the engines/hardware/nodes").
    Explicit [agents.*].lane wins; else infer from endpoint/model. iGPU is now
    its OWN lane (was collapsed into 'cpu', which queued it behind CPU work).

<!-- mios-src:7e9e22fd90d0 from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:271-278 -->

### Render the sub-agent roster for the planner as JOBS, not...

Render the sub-agent roster for the planner as JOBS, not fixed roles
 ("no fixed roles -- MiOS-Agents are modelfiles for
    jobs and tools/skills/recipes"). Each agent is described by its `job`
    (mios.toml [agents.<name>].job, SSOT) -- what its Modelfile is BEST at --
    falling back to a blurb derived from role + strengths tags when no job is
    set. Every agent has GLOBAL access to all MiOS verbs/recipes/skills, so the
    planner routes purely by CAPABILITY + compute LANE (to spread work across
    CPU/GPU/iGPU concurrently), never by tool availability. Pulled from
    _AGENT_REGISTRY (mios.toml [agents.*] SSOT).

<!-- mios-src:9b8d6ea95585 from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:295-303 -->

### Per-role DEVELOPER overlay (OpenAI developer-message...

Per-role DEVELOPER overlay (OpenAI developer-message pattern), layered
    AFTER the /MiOS.md SYSTEM identity. Generated by mios-gen-role-system from the
    SSOT (thin: role + tool-focus pointer + live fleet, ~340 B). Degrade-open to ''
 so a missing/unreadable overlay never breaks dispatch..

<!-- mios-src:e53e0f502244 from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:323-326 -->

### Collapse a fan-out pool to DISTINCT (endpoint, model)...

Collapse a fan-out pool to DISTINCT (endpoint, model) targets + cap width
 ("all these hardcoded agents" / 16-agent explosion). Several
    pool members -- node-pool synthetics and/or research_only agents -- can resolve
    to the SAME endpoint+model -> N IDENTICAL dispatches = pure redundancy + idle
    thrash. Keep ONE agent per (endpoint, model) so the swarm fans across DISTINCT
    compute targets, not duplicates (model diversity on one endpoint is preserved --
    a different model => a different key). PREFER a node:* synthetic, then a
    first-class agent, over a plain research_only agent for the same target. Then cap to SWARM_MAX_WIDTH.
    Agents with no resolvable endpoint (a2a peers, bespoke gateways) are keyed by
    name so they're never collapsed.

<!-- mios-src:cece60dc3a86 from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:338-347 -->
