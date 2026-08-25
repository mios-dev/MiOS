<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Open a span under the current trace/parent (contextvars)...

Open a span under the current trace/parent (contextvars), record it on
    exit with duration + ok/error status. Near-no-op when tracing is disabled or
    no trace is active (degrade-open).

<!-- mios-src:b3c10a99920b from usr/lib/mios/agent-pipe/server.py:311-313 -->

### At chat_completions entry

At chat_completions entry: seed the dispatch depth FROM the incoming X-MiOS-Hop
    (so the bound crosses the HTTP hop) and record the Via chain. If our OWN id is
    already in the chain, force degrade-closed (no further fan-out) -> a re-entrant
    loop answers single-agent instead of recursing. Degrade-open on any error.

<!-- mios-src:fc796ad8d3ed from usr/lib/mios/agent-pipe/server.py:581-584 -->

### Canonical skill tags for an agent

Canonical skill tags for an agent: role + inference lane + declared
    strengths. SINGLE SSOT shared by the A2A AgentCard (publish side ->
    skill.tags) and _pick_fanout_agents (consume side -> routing key) so an
    agent's advertised capabilities and the key the orchestrator routes on
    can never drift. Clean human/agent-facing labels (NOT snake_case-split);
    the router expands sub-tokens for matching internally.

<!-- mios-src:3db845183ebd from usr/lib/mios/agent-pipe/server.py:1462-1467 -->

### Pipeline-side READ-ONLY capability runner ("all... skills...

Pipeline-side READ-ONLY capability runner ("all...
    skills and recipes fire on ALL endpoints"). For the refine-hinted verbs that
    are permission=read AND take NO required args (live system state), the
    PIPELINE runs them itself + injects the real output for EVERY agent -- so a
    system-state turn is grounded on the iGPU/phone too, not only the
    tool-looping primary. SAFETY: write/launch verbs + recipes are NEVER
    auto-fired here (binding no-live-launch rule); web verbs go to
    _web_research_enrich, KB search to _rag_enrich. Best-effort + bounded.

<!-- mios-src:9b2aa36feb47 from usr/lib/mios/agent-pipe/server.py:2054-2061 -->

### Data-driven action-vs-research split

Data-driven action-vs-research split: a routed [routing.domains] domain is
    an ACTION domain (decompose into EXECUTABLE tool steps, not research facets)
    iff ANY of its SSOT verbs is permission=='write'. No keyword/app/English
    literals -- the distinction is verb PERMISSION metadata from mios.toml, so a
 new write-verb in any domain becomes 'action' automatically.
    (swarm researched 'send a discord message' instead of performing it).

<!-- mios-src:e22ba496b5a5 from usr/lib/mios/agent-pipe/server.py:2554-2559 -->

### True if `url`'s host is LOCAL to the operator (loopback /...

True if `url`'s host is LOCAL to the operator (loopback / tailnet /
    private LAN / container DNS), False for a public/cloud host. Conservative:
    an unparseable or empty url is treated as local (it's not a cloud egress).

<!-- mios-src:34ce81a9651d from usr/lib/mios/agent-pipe/server.py:3378-3380 -->

### Re-read the agent/node registry + A2A peer registry from...

Re-read the agent/node registry + A2A peer registry from disk and refresh the
    LIVE module caches WITHOUT a restart (FED-G3). Removes 'restart to add an agent'.
    Degrade-open: a partial failure logs + still refreshes what it can.

<!-- mios-src:a73868ba8924 from usr/lib/mios/agent-pipe/server.py:3559-3561 -->
