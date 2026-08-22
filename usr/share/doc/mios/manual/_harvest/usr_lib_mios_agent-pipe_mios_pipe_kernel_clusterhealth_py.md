<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Cluster / scheduler / health route-handler logic (refactor...

Cluster / scheduler / health route-handler logic (refactor ROUTE-SURFACE wave).

Extracted VERBATIM from ``server.py``: the bodies behind the three deferred
liveness/observability endpoints -- ``/v1/cluster/health`` (per-agent + per-
endpoint probe), ``/v1/scheduler`` (AIOS-style per-lane concurrency + priority
posture), and ``/health`` (capability/health rollup). Each body is moved byte-
identically into a ``*_logic`` function; the ``@app`` routes stay in ``server.py``
as thin wrappers calling these through ``sys.modules`` so the HTTP + importable
surface is unchanged.

The live lane resolver is read through ``mios_lanes_resolver._lane_resolver_current()``
(via ``sys.modules``) inside ``cluster_health_logic`` -- the runtime-reassigned
singleton is never captured by value. Static config / DCI / SLO / secset symbols are
imported directly; every server-resident runtime dependency is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).

<!-- mios-src:1571b9c075f3 from usr/lib/mios/agent-pipe/mios_pipe/kernel/clusterhealth.py:3-18 -->

### Expand an agent name into the FULL failover chain ( 'remove...

Expand an agent name into the FULL failover chain (
    'remove SPOFs'): self -> declared failover_agents (mios.toml) -> self's
    cpu_endpoint as a last-resort virtual agent. Each entry is {name, endpoint,
    model, kind in {primary,failover,cpu-twin}}. Names already visited in the
    chain are skipped so a config loop can't recurse. Reads the injected-by-
    reference _AGENT_REGISTRY (the only server-side dep), so the move is
    behaviour-identical; the sole caller is cluster_health_logic below.

<!-- mios-src:7cc15e3f5be9 from usr/lib/mios/agent-pipe/mios_pipe/kernel/clusterhealth.py:272-278 -->

### AIOS-style scheduler observability

AIOS-style scheduler observability: live per-lane concurrency state
    (cap / in-flight / available / queued) across every hardware lane the
    swarm dispatches to. Proves the resource-aware concurrency is real +
    shows where contention is. Includes the priority-scoring shape used to
    rank turns.

<!-- mios-src:d9263915d926 from usr/lib/mios/agent-pipe/mios_pipe/kernel/clusterhealth.py:398-402 -->
