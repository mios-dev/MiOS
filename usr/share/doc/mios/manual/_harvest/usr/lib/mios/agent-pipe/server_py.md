<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### 'MiOS' Agent Pipe -- standalone FastAPI service. Step 2 of...

'MiOS' Agent Pipe -- standalone FastAPI service.

Step 2 of the migration: ports the router + dispatch + agent-plane DB
writes from the OWUI Pipe class into this gateway-agnostic service.

Operator directive "mios discord chats not going through
MiOS-Agent(OWUI) paths when contacting through discord (uses only
MiOS-Hermes and doesn't have the same tool understanding and
environments details now!!!!)"

Architecture:

  OWUI                     ──┐
  Hermes Discord gateway   ──┼──> :8640 (this service)
  future Slack/Telegram    ──┘        │
                                       ▼
                              :8642 (hermes-agent)
                                       │
                                       ▼
                       mios-llm-light :8450 (raw /v1 inference)

Endpoints:
  GET  /health                  -> {status, version, backend, port}
  POST /v1/chat/completions     -> Router-classified chain:
                                     action=dispatch -> verb via broker
                                                       -> tool_call envelope
                                     action=chat    -> short-reply
                                     action=agent   -> proxy to backend
                                     (no verdict)   -> proxy to backend
  GET  /v1/models               -> proxy to MIOS_AGENT_PIPE_BACKEND
  POST /v1/embeddings           -> proxy to MIOS_AGENT_PIPE_BACKEND

Per the SSOT chain: every operator-tunable constant sources from
mios.toml -> userenv.sh -> MIOS_* env -> os.environ.get() with
sensible fallbacks. No hardcoded literals.

Skipped vs. the OWUI Pipe (deliberate for this commit; can be Step
2b if Discord needs them):
  * REFINE pass (CPU-LLM rewrite of the user message before forward)
  * CRITIC pass (post-backend verification + re-compose loop)
  * POLISH pass (final-answer cleanup)
  * NARRATION COLLAPSE (OWUI <think> wrapping)
These are quality-bonus features that add latency without changing
the tool-understanding parity Discord needs. They can be ported in
follow-up commits guided by operator feedback.

<!-- mios-src:8e220b2bb79a from usr/lib/mios/agent-pipe/server.py:3-48 -->

### Open a span under the current trace/parent (contextvars)...

Open a span under the current trace/parent (contextvars), record it on
    exit with duration + ok/error status. Near-no-op when tracing is disabled or
    no trace is active (degrade-open).

<!-- mios-src:b3c10a99920b from usr/lib/mios/agent-pipe/server.py:357-359 -->

### Liveness-probe + circuit-break an agent/node when it...

Liveness-probe + circuit-break an agent/node when it declares health_gate
 OR lives on a REMOTE endpoint (dead-node circuit-breaker:
    ai-local the phone had no explicit health_gate -> was dispatched while off ->
    'All connection attempts failed' retry storm that helped wedge the box). LOCAL
    lanes are never probed -- their failure is a separate, louder problem and
    probing only adds latency.

<!-- mios-src:855a2a330f4a from usr/lib/mios/agent-pipe/server.py:443-448 -->

### At chat_completions entry

At chat_completions entry: seed the dispatch depth FROM the incoming X-MiOS-Hop
    (so the bound crosses the HTTP hop) and record the Via chain. If our OWN id is
    already in the chain, force degrade-closed (no further fan-out) -> a re-entrant
    loop answers single-agent instead of recursing. Degrade-open on any error.

<!-- mios-src:fc796ad8d3ed from usr/lib/mios/agent-pipe/server.py:633-636 -->

### Force the micro model on a LOCAL light-lane (CPU/iGPU)...

Force the micro model on a LOCAL light-lane (CPU/iGPU) endpoint -- a big
    model can never cold-load multi-GB weights on a CPU-only daemon MiOS itself
 controls (runaway fix). No-op for non-light endpoints AND for
    REMOTE nodes: a remote node serves its OWN model catalog (a tailnet node
    whose port happens to be 11435/11436 need not serve the LOCAL micro tag), so
    it KEEPS its declared model -- exactly this function's long-standing intent
    ('remote keep their model'), which the bare port-substring match wrongly
    violated for any remote node on a CPU-hint port (the remote-cpu node, the
    iGPU/potato examples). LOCAL == localhost/127.0.0.1 (mirrors _load_node_pool's
    _is_local). The slow-lane num_predict cap (_is_slow_lane_ep) stays port-based
    and DOES still apply to a remote CPU -- a remote CPU is genuinely slow, so its
    output is still capped; only the wrong-model substitution is local-scoped.

<!-- mios-src:74a6abf4465c from usr/lib/mios/agent-pipe/server.py:1273-1284 -->

### [dispatch] -- multi-agent concurrent fan-out config (SSOT...

[dispatch] -- multi-agent concurrent fan-out config (SSOT in
    mios.toml; env override).

 mode (supersedes the earlier 'a couple, not all'):
      * 'council'   -- EQUAL WEIGHTING: every chat-eligible agent (every
                       [agents.*] without fanout=false, minus the primary)
                       is dispatched CONCURRENTLY each turn, up to
                       fanout_max, regardless of tag relevance. Lane-diverse
                       ordering runs CPU + GPU agents in parallel. This is
                       what stops the Hermes monopoly.
      * 'relevance' -- legacy: score the OTHER agents by skill-tag overlap
                       with the refined plan, engage only the top matches.
    fanout_max<=1 restores exact single-agent behaviour (zero fan-out).

<!-- mios-src:ff8dc1247235 from usr/lib/mios/agent-pipe/server.py:1477-1489 -->

### Canonical skill tags for an agent

Canonical skill tags for an agent: role + inference lane + declared
    strengths. SINGLE SSOT shared by the A2A AgentCard (publish side ->
    skill.tags) and _pick_fanout_agents (consume side -> routing key) so an
    agent's advertised capabilities and the key the orchestrator routes on
    can never drift. Clean human/agent-facing labels (NOT snake_case-split);
    the router expands sub-tokens for matching internally.

<!-- mios-src:3db845183ebd from usr/lib/mios/agent-pipe/server.py:1541-1546 -->

### The verified owner/tenant for THIS turn's dispatch, or...

The verified owner/tenant for THIS turn's dispatch, or None. Reuses the V2
    principal-binding owner: under [security].principal_bind_mode=enforce the
    _client_env owner is already RECONCILED to the token-bound account (the spoofable
    claim overridden), so this returns the verified tenant; otherwise the forwarded
    owner. None (a system/daemon/seeding dispatch with no forwarded principal) -> the
    per-tenant gate never caps it. Consulted ONLY when TENANT_QUOTA_ENABLE; degrade-
    open: any error -> None (no per-tenant cap). Mirrors mios_knowledge._request_
    principal so the tenant key agrees with owner_user row-scoping.

<!-- mios-src:dd28ae032739 from usr/lib/mios/agent-pipe/server.py:1976-1983 -->

### Pipeline-side READ-ONLY capability runner ("all... skills...

Pipeline-side READ-ONLY capability runner ("all...
    skills and recipes fire on ALL endpoints"). For the refine-hinted verbs that
    are permission=read AND take NO required args (live system state), the
    PIPELINE runs them itself + injects the real output for EVERY agent -- so a
    system-state turn is grounded on the iGPU/phone too, not only the
    tool-looping primary. SAFETY: write/launch verbs + recipes are NEVER
    auto-fired here (binding no-live-launch rule); web verbs go to
    _web_research_enrich, KB search to _rag_enrich. Best-effort + bounded.

<!-- mios-src:9b2aa36feb47 from usr/lib/mios/agent-pipe/server.py:2141-2148 -->

### Data-driven action-vs-research split

Data-driven action-vs-research split: a routed [routing.domains] domain is
    an ACTION domain (decompose into EXECUTABLE tool steps, not research facets)
    iff ANY of its SSOT verbs is permission=='write'. No keyword/app/English
    literals -- the distinction is verb PERMISSION metadata from mios.toml, so a
 new write-verb in any domain becomes 'action' automatically.
    (swarm researched 'send a discord message' instead of performing it).

<!-- mios-src:e22ba496b5a5 from usr/lib/mios/agent-pipe/server.py:2641-2646 -->

### Generative compute-need judge ("MATH(AND OTHER PYTHON...

Generative compute-need judge ("MATH(AND OTHER PYTHON
    CAPABILITIES) ... natural language!!! not verbs/keywords"). Decide, BY MEANING not
    keywords, whether fully + CORRECTLY answering needs a calculation a language model
    cannot do reliably in its head -- multi-digit/exact arithmetic, statistics, unit/
    currency conversion, counting, or a date/time difference. A small model both
    mis-computes in-head AND won't reliably call the (now ambient) sandbox tool, so the
    PIPE runs the math itself (mirrors the web prefetch). True only on a confident yes;
    degrade-CLOSED (error/None -> False = no compute prefetch, unchanged behaviour).

<!-- mios-src:fa6a8d52a398 from usr/lib/mios/agent-pipe/server.py:2662-2669 -->

### A2A-discoverable agent directory (roadmap DATA-01 / T-059)....

A2A-discoverable agent directory (roadmap DATA-01 / T-059).

    Returns the roster of every registered ``[agents.*]`` entry as an
    ``(author, name, version)`` tuple plus its A2A card link, so a discovering
    peer QUERIES this endpoint instead of reading a static file. Reuses the
    A2A AgentCard as the SSOT: ``author`` = the card provider organization,
    node ``version`` = the card version, and each entry links back to the
    node's well-known AgentCard -- a REMOTE peer (kind in
    remote-http/a2a/edge/node/mobile) advertises its OWN card + a2a base,
    while a local sub-agent is a skill of THIS node's single card. Open
    discovery surface (see _AUTH_OPEN_PATHS). Degrade-open: an unreadable
    registry or card yields an empty roster, never a 500.

<!-- mios-src:b9fb8897a488 from usr/lib/mios/agent-pipe/server.py:3325-3337 -->

### True if `url`'s host is LOCAL to the operator (loopback /...

True if `url`'s host is LOCAL to the operator (loopback / tailnet /
    private LAN / container DNS), False for a public/cloud host. Conservative:
    an unparseable or empty url is treated as local (it's not a cloud egress).

<!-- mios-src:34ce81a9651d from usr/lib/mios/agent-pipe/server.py:3486-3488 -->

### Re-read the agent/node registry + A2A peer registry from...

Re-read the agent/node registry + A2A peer registry from disk and refresh the
    LIVE module caches WITHOUT a restart (FED-G3). Removes 'restart to add an agent'.
    Degrade-open: a partial failure logs + still refreshes what it can.

<!-- mios-src:a73868ba8924 from usr/lib/mios/agent-pipe/server.py:3667-3669 -->
