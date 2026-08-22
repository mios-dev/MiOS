<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### PER-TURN message-prep + agent-selection helpers...

PER-TURN message-prep + agent-selection helpers (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. These are the small cohesive turn-prep
helpers the chat router + responders call each turn: last-user-text extraction,
role-based sub-agent selection (with degrade-open on a dead gated node), the
generic agent surface label, the per-turn live-agent roster (health-probed +
TTL-cached), and the <think>-tag reasoning/answer split. Every server-resident
symbol -- the live agent registry, the node-liveness cache, the health-probe +
probe-auth helpers, the liveness TTL/connect scalars, and the think-tag regexes
-- is injected via :func:`configure` (one-way boundary -- this module never
imports ``server``). ``server.py`` re-imports each name under its original alias
so the importable surface stays byte-identical.

<!-- mios-src:2ff157824ebb from usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py:3-15 -->

### Inject server-side deps under their EXACT original names...

Inject server-side deps under their EXACT original names (one-way boundary).

    Called from ``server.py`` after every injected symbol is defined, and again
    from ``_reload_membership`` to re-bind ``_AGENT_REGISTRY`` after a live add/drop.
    Each keyword equals the module global it sets.

<!-- mios-src:a04f508515b4 from usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py:48-53 -->

### Set of agent names currently USABLE for dispatch ( "iGPU is...

Set of agent names currently USABLE for dispatch (
    "iGPU is down"). Non-health_gate agents are ALWAYS live -- they are local
    lanes whose failure is a separate, louder problem and probing them every
    turn only adds latency. Only health_gate client/Tailscale nodes (the iGPU,
    a phone) -- the ones that legitimately come and go -- are connect-probed,
    TTL-cached in _NODE_LIVE so an OUTAGE drops the node from the swarm roster
    WITHOUT re-probing every turn (it rejoins within the TTL once back up).
    Used to prune dead nodes before the planner/DAG assigns them a facet, so the
    freed concurrent lane re-routes to live compute instead of vanishing.

<!-- mios-src:df5db8813728 from usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py:61-69 -->

### Pick a sub-agent by role match. Order

Pick a sub-agent by role match. Order: exact-role -> default
    -> first registered. Returns (name, cfg).

 Degrade-open (install-robustness): if the chosen agent is a
    health_gate (come-and-go) node -- e.g. the :8643 hermes-worker bound to the
    heavy GPU lane, which is gated off by default -- that the liveness cache does
    NOT confirm reachable, blank its endpoint so the caller's `endpoint or
    BACKEND` falls back to the always-on local lane. Without this the PRIMARY
    dispatch went to a dead gated worker -> httpx "All connection attempts
    failed" -> 502 on EVERY turn on any host where that lane is down (a fresh
    dev VM, a CPU host). The worker is still used the moment the probe confirms
    it live (heavy lane enabled).

<!-- mios-src:e497f81c02cf from usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py:114-125 -->

### Split model output into (reasoning, answer). 'there SHOULD...

Split model output into (reasoning, answer).

 'there SHOULD be thinking -- as a dropdown' AND
    'thinking bleeding into the final response makes it look like it
    answered twice'. The fix is to CAPTURE the <think>-family reasoning
    (so it can go in a collapsed dropdown) instead of discarding it, and
    return the answer with the reasoning removed (clean main reply).
    Handles closed + unclosed + orphan tags across the qwen3 <think> and
    <thinking>/<thought>/<reasoning>/<reflection>/<scratchpad> variants.
    Tag-based only -- structural, no English content matching.

<!-- mios-src:446930282ae5 from usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py:151-160 -->

### Map registered sub-agent name -> casual MiOS-convention...

Map registered sub-agent name -> casual MiOS-convention label
    for SSE status emission + dropdown summaries. Operator binding:
    surface labels stay generic ('sub-agent' / role), the specific
    daemon name lives in event payloads + journal, not in the chat
    UI. Same agent can be renamed via mios.toml [agents.*] without
    leaking the old name to the operator's screen.

<!-- mios-src:ef2fdfc3553c from usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py:188-193 -->
