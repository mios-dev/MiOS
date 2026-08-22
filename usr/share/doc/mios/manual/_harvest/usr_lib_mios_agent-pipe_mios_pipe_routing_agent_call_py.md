<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Shared sub-agent completion-call primitive (council...

Shared sub-agent completion-call primitive (council secondaries + DAG nodes).

Extracted verbatim from ``server.py``. ``_call_agent_complete`` is the bounded
dispatch entry point (admission + per-lane semaphores + RR preemption + cost +
chrome strip); ``_call_agent_complete_inner`` is its best-effort non-streaming
/v1 call with the pipe-side secondary tool-loop, KV fork/paging bracket,
outbound auth, source harvest and the P3.2b failover-chain recursion.

The moved bodies are unchanged. ``_endpoint_is_llamacpp`` is imported directly
from its sibling module ``mios_endpoints``; every other server-side symbol the
two functions touch (the lane semaphores, the binding/priority helpers, the
secondary tool-loops, the KV helpers, the ContextVars, the header/trace helpers,
the agent registry and the config scalars) is injected via :func:`configure`
(one-way module boundary -- this module never imports ``server``). ``server.py``
re-imports both names under their original aliases so the public surface stays
byte-identical, and re-injects the agent registry on a live membership reload.

<!-- mios-src:8c690553850c from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:3-19 -->

### Open the circuit for a REMOTE agent that just failed a...

Open the circuit for a REMOTE agent that just failed a dispatch: mark it
    DOWN in _NODE_LIVE so the next turn prunes it (no repeated inline retries on a
    dead node -- reachability becomes a precondition, retries go off the hot path).
    No-op for local lanes (a transient local error must not strand a core agent for
    the whole TTL). Rejoins automatically when the TTL re-probe finds it back up.

<!-- mios-src:0e149845016e from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:288-292 -->

### WS-RES-GOV observe-only

WS-RES-GOV observe-only: record one dispatch's energy/$ cost into the
    ledger. No-op unless COST_ACCOUNTING_ENABLE; degrade-open (accounting must
    never break a turn). Token counts come from the tokenizer seam (energy is
    dominated by elapsed x watts; tokens matter only for a remote $/Mtok lane).

<!-- mios-src:65e58443f412 from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:308-311 -->

### Bounded entry point (/24): concurrent agent dispatches --...

Bounded entry point (/24): concurrent agent dispatches
    -- council secondaries AND DAG-level nodes -- acquire the PER-LANE semaphore
    for the engine/node they actually run on, so distinct hardware (dGPU, CPU,
    iGPU, accelerator, each remote node) all fire CONCURRENTLY and only same-lane
    agents queue. No nested agent calls, so no deadlock. `priority` feeds the
    capacity-aware _admit gate; default None -> lane-derived (_dispatch_priority)
    so slow/remote lanes self-shed under load ('all nodes
    enabled by default').

<!-- mios-src:1b0606db7c89 from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:380-387 -->

### Best-effort non-streaming /v1 call to a secondary fan-out...

Best-effort non-streaming /v1 call to a secondary fan-out agent.
    Returns (name, text); text='' -> dropped from the merge. A dead or
    absent endpoint (e.g. opencode :8633 when not served as /v1) just
    yields '' and is skipped, so fan-out degrades to the live agents.

 CPU-lane offload : a secondary always runs
    CONCURRENTLY with the GPU primary, so if the agent declares a CPU
    twin (a declared CPU/light engine binding -> the mios-llm-light lane) we
    dispatch THAT -- the secondary works on the light iGPU/CPU lane while
    the dGPU stays dedicated to the primary. No twin -> its own endpoint.

    Every lane speaks the OpenAI /v1 surface (MiOS is /v1-only): the call
    posts to {ep}/chat/completions with the thinking channel disabled
    (chat_template_kwargs enable_thinking=False) -- a qwen3 model left on its
    default thinking split dumps its answer into message.reasoning with EMPTY
    content, so a secondary would fold in nothing. Custom gateways (opencode
    :8633, hermes :8642) share the exact same /v1 path.

 P3.2b AUTO-FAILOVER ('remove SPOFs'): when a
    transport-level failure (unreachable endpoint, non-200, timeout)
    leaves THIS hop empty AND the agent declares a failover_agents chain
    (mios.toml SSOT), retry the SAME body against the next live agent in
    the chain. _failover_depth bounds the recursion + skips already-visited
    names. A semantically-empty answer (model returned content="") DOES NOT
    trigger failover -- the agent succeeded; the council merge handles
    quality. Only TRANSPORT failure flips us into failover.

<!-- mios-src:c61863c05f79 from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:571-596 -->

### Demand-page this conversation's llama.cpp KV around a...

Demand-page this conversation's llama.cpp KV around a completion: on a
    conversation SWITCH, page the resident one OUT (save=unload) and this one IN
    (restore=load); a same-conversation turn is a no-op (warm in-slot KV). Holds
    a per-(endpoint,slot) lock across the bracket so a concurrent conversation
    can't swap the slot mid-flight. No-op + zero overhead unless paging is on
    AND `ep` is a llama.cpp endpoint with /slots.

<!-- mios-src:6e26c4fdaa5f from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:948-953 -->

### WS-8

WS-8: fork `src_conv`'s saved llama.cpp KV into a NEW file for `dst_conv`
    so a swarm branch can page in the shared prefix independently. Drives the
    PURE plan from mios_kvfork over the existing _kv_slot_action primitive, under
    the per-(endpoint,slot) lock so a concurrent conversation can't swap the slot
    between the restore and the save. DEFAULT-OFF + degrade-open: returns
    {forked: bool, reason: str} and NEVER raises -- a disabled flag, a non-
    llama.cpp endpoint, a bad request, or a failed slot op all just mean the
    child starts cold (as today). After a successful fork the slot resident is
    the CHILD (it was just saved from the slot), so _KV_RESIDENT is updated to
    keep the demand-pager's bookkeeping honest.

<!-- mios-src:249c2e53c5a1 from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:992-1001 -->

### Interruptible chunked decode (WS-A12). SINGLE-OWNER of the...

Interruptible chunked decode (WS-A12). SINGLE-OWNER of the global priority
    gate: acquires once, releases once in `finally`, and across a preemption does
    a balanced release->re-acquire (held tracked precisely) so permit accounting
    can never drift. Returns the full assistant text. Degrade-open: ANY failure
    falls back to one completion of the whole budget; the partial is never lost.

<!-- mios-src:f0e0ec90733e from usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py:1077-1081 -->
