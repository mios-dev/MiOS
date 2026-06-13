<!-- AI-hint: Defines MiOS's convergence from bespoke logic onto standardized agentic protocols (MCP for tools, the OpenAI tool-call loop for execution, A2A/ACP for multi-agent coordination/delegation) so the local agent stack coordinates reliably and executes real tool calls via the `mios-mcp-server` and `agent-pipe`/Hermes orchestration. Status: Phases 1, 2, 4 shipped; 3 and 5 are cleanups.
     AI-related: mios-mcp-server, mios-mcp, mios-agent-pipe, hermes-agent, mios-opencode-gateway, mios-web-search, mios-sysview, mios-discord-send, mios-mcp.service -->
# MiOS Agentic Standards Roadmap (MCP · OpenAI tool-loop · A2A/ACP)

> **Where this fits in MiOS.** MiOS is one thing built two ways at once: an
> immutable, bootc/OCI-shaped Fedora workstation (the whole OS is a single
> container image you `bootc upgrade` like a `git pull` and `bootc rollback`
> like a Ctrl-Z) that is *also* a local, self-replicating, agentic AI operating
> system. The AI half lives behind one OpenAI-compatible endpoint: front-ends
> (Open WebUI, the Discord gateway, the `mios` CLI) hit **agent-pipe** (`:8640`),
> which refines → routes → fans out a council/swarm → dispatches tool/verb
> calls → polishes; **MiOS-Hermes** (`:8642`) is the OpenAI-compat gateway that
> runs the tool-loop; **pgvector** (`:5432`) is the unified agent memory; the
> **inference lanes** (`mios-llm-light` `:11450` primary + embeddings, the gated
> `mios-llm-heavy`/`-heavy-alt` GPU lanes) do the generation. This doc is the
> roadmap for making the COORDINATION between those parts ride open agentic
> standards instead of bespoke plumbing — so the system that ships in the image
> behaves the same on any hardware, fully local, with no cloud-AI dependency
> (Architectural Law 5).

Operator directive 2026-05-22: "NOTHING hardcoded anywhere; fix in code to
OpenAI-API standards and patterns for multi-agentic solutions using
open-source tools, locally hosted. Research, then refine to specs — ACPs,
MCP, etc." Roadmap requested ("you sequence it, I pick").

## Why
Most recurring failures trace to NON-STANDARD, hardcoded plumbing (the
exception: Hermes already runs a full standard tool-loop with its full
capability set inside the MiOS pipeline — see Phase 2):
- the executor model sometimes **narrates** "I posted to Discord" instead of
  emitting the `tool_call` it is able to → occasional reliability tuning, not
  a missing loop;
- **bespoke verb dispatch** + a (rejected) keyword detector;
- **fan-out by hardcoded strength tokens** (`event`/`what`/`happened` →
  daemon telemetry flood);
- **validation by a soft prompt rule** on a small model (misses the lie).

The fix is convergence onto the Linux-Foundation Agentic-AI standards:
**MCP** for tools, the **OpenAI tool-call loop** for execution, **A2A**
Agent Cards for coordination, **ACP** for delegated runs. All open-source,
all local, no cloud-AI dependency (Architectural Law 5). Each standard maps to
one part of the stack above: MCP is the tool surface agent-pipe/Hermes consume,
the tool-loop is what Hermes runs, A2A is how the agent-pipe fleet discovers and
delegates across peers (the `[a2a]` roster / `mios-a2a-discover`).

## What already exists (build ON this)
- `agent-pipe` (`mios-agent-pipe.service`, `:8640`) — OpenAI
  `/v1/chat/completions` endpoint (the standard surface) + the
  refine/route/council/polish orchestrator.
- `mios-mcp-server` — MCP stdio server (JSON-RPC 2.0, spec 2025-06-18);
  renders `[verbs.*]` SSOT as MCP tools; `tools/call` → agent-pipe
  `/v1/dispatch` → launcher broker. `mios-mcp.service`.
- `mios-opencode-gateway` (`mios-opencode-gateway.service`, `:8633`) — OpenAI
  `/v1` shim for opencode, the loopback ACP-style coder peer of the council.
- `usr/share/mios/ai/v1/mcp.json` — the MCP-registry overlay the agent-pipe
  CONSUMES external MCP servers from (`mcp_registry` in `mios.toml`).
- Helpers as clean tool backends: `mios-web-search` (SearXNG `:8888`),
  `mios-sysview`, `mios-discord-send`, the CDP browser tool loop.

So the work is WIRING + standardizing onto these standards, not greenfield.

## Phases (sequenced; pick a starting point)

### Phase 1 — Complete + verify the MCP tool CONTRACT  ·  effort: M  ·  risk: LOW  ·  ✅ DONE (committed)
- Audit `mios-mcp-server`: is `mios-mcp.service` running? are ALL `[verbs.*]`
  rendered as MCP tools with correct JSON input schemas?
- Fill gaps: ensure `web_search`, `browser_*`, `sysview`, `os-control` verbs
  AND `discord_send` (`[verbs.discord_send]` → `mios-discord-send` backend)
  are first-class MCP tools. Schemas come from mios.toml `[verbs.*]` (SSOT) —
  no hardcoded tool lists.
- Deliverable: one authoritative, schema-correct, locally-hosted MCP tool
  catalog. Additive — changes no live behaviour yet.

### Phase 2 — Standard OpenAI tool-call loop  ·  ✅ ALREADY REALIZED (in Hermes)
- The canonical agentic loop (offer tools → model returns `tool_calls` →
  execute → feed `role:tool` back → repeat → grounded final answer) already
  runs **inside Hermes** (`hermes-agent.service`, `:8642`), which operates full
  tool-loops with its full capability set within the complete MiOS AI
  pipeline/chains. It is NOT a thing agent-pipe still has to build.
- Topology (corrected 2026-05-22, operator): agent-pipe
  (`/v1/chat/completions`, `:8640`) is the refine → route → polish → critic
  ORCHESTRATION layer; it forwards to Hermes (`:8642`) which runs the loop,
  then folds the results back. Hermes is NOT bound to a narrow tool set — it
  carries its full built-in tool registry (terminal/shell, web, file, …) PLUS
  the full MiOS verb + skill surface (`discord_send`, os-control, browser,
  computer-use, … all reachable). Hermes config's `tools:` block only
  configures `web_search`'s provider; it is not the whole surface.
- So the historical narrate-instead-of-call symptom was never a missing-loop
  or missing-tool problem — at worst it's occasional EXECUTOR-MODEL behaviour
  (a small model describing an action instead of emitting the `tool_call` it
  is fully able to). That's optional reliability tuning, done live in the
  Hermes layer (executor model choice / `tool_choice` nudge / SOUL prose) on
  the operator's hardware — NOT an architectural gap and NOT blocking 3/5.
- SHIPPED this session (standards surface, not a fix for anything broken):
  `GET /v1/verbs/openai-tools` — the verb catalog in OpenAI `{type:function}`
  shape, the twin of `/v1/verbs` (MCP) + the A2A card skills. One SSOT
  (`_VERB_CATALOG`), three projections (MCP / OpenAI-tools / A2A). For strict
  external OpenAI / A2A / ACP clients that lack the MiOS plugin; execution via
  the existing `POST /v1/dispatch`. Hermes does not need it.

### Phase 3 — Single execution path, no hardcodes  ·  ✅ ESSENTIALLY SATISFIED
- CORRECTED FRAMING (2026-05-22): the original "delete `_build_dispatch_cmd`
  verb-arms" is WRONG. That function is NOT bespoke duplication to remove —
  it is the SINGLE shared execution backend: `/v1/dispatch` →
  `dispatch_mios_verb` → `_build_dispatch_cmd`, and MCP `tools/call`, the
  OpenAI-tools surface, A2A-routed verb calls, AND the planner DAG all execute
  THROUGH it. Deleting it breaks every standard surface. It stays.
- What Phase 3 actually wanted is already true: there is ONE execution path
  (`_build_dispatch_cmd` over the launcher broker), arms are generated from
  the `[verbs.*]` SSOT, and the rejected keyword/topic detector is gone.
  Remaining = ordinary hygiene: migrate the last few hardcoded verb arms into
  `[recipes.*]`/SSOT over time (see the no-hardcode memory). Not blocking.

### Phase 4 — A2A Agent Cards for multi-agent coordination  ·  effort: H  ·  risk: MED  ·  ✅ PUBLISH + CONSUME SHIPPED
- Replace `_pick_fanout_agents` strength-token matching with A2A Agent Cards:
  each sub-agent (Hermes, opencode, daemon, sys) publishes a card
  (capabilities/skills/endpoint); the orchestrator routes + fans out by
  card-advertised capability (semantic match), not hardcoded tokens. opencode
  keeps ACP for delegated execution. Removes the daemon-flood root cause.
- SHIPPED (publish side): agent-pipe serves the A2A AgentCard at
  `/.well-known/agent-card.json` (+ `/.well-known/agent.json` legacy +
  `/v1/agent-card`), generated from mios.toml `[agents.*]` SSOT — each agent
  becomes an A2A skill (id=name, tags=strengths, description=role+lane). Same
  data `_pick_fanout_agents` scores, now in the open standard. Additive,
  zero pipeline risk; an `x-mios` block cross-links the OpenAI `/v1` + MCP
  surfaces so a discovering peer knows how to drive MiOS.
- SHIPPED (consume side): `_pick_fanout_agents` now routes on the SAME
  `_agent_skill_tags()` SSOT the card publishes, with WORD-BOUNDARY matching
  (was substring: `search` matched inside `researching`). Card capability ==
  routing key; daemon-flood guards (fanout=false + score>0 bonus gating)
  preserved.
- SHIPPED (federation): real cross-node delegation now rides A2A — the `[a2a]`
  roster + `mios-a2a-discover` write live peers to
  `/etc/mios/ai/v1/a2a-peers.json`, and the `a2a_delegate` /
  `transfer_session_to_agent` verbs hand a sub-task (or the whole session via
  the A2A `contextId`) to a registered peer and fold its answer back. Phase 4
  is effectively complete; further refinement (semantic / embedding match over
  tags) is optional polish.

### Phase 5 — Validation → STRUCTURAL  ·  ◑ CORE ALREADY PRESENT; do NOT force the rest
- ALREADY STRUCTURAL: the confirmation engine (`_inline_satisfaction_check`)
  AND-folds the recorded `tool_call` rows' `success` fields → deterministic
  satisfied/unsatisfied when agent-pipe recorded the calls. (Those rows live in
  the `tool_call` table in PostgreSQL+pgvector, the unified agent datastore.)
- The remaining roadmap idea — "validate an action-CLAIM in the answer prose
  IFF a matching tool_call exists" — is DELIBERATELY NOT done, for two
  binding reasons: (1) it requires natural-language claim detection, which
  needs language-specific patterns → violates the no-hardcoded-language rule;
  (2) Hermes runs the tool-loop internally, so agent-pipe sees the invoked
  tool NAMES (`_tools_called`) but not always structured per-call results —
  treating "no agent-pipe row = unsatisfied" is exactly the
  "succeeds-early-then-reports-failed" false-negative the engine already fixed
  (server.py ~1979-1995). Forcing it would regress that fix.
- Net: the soft INVOKED-TOOL-CHECK polish rule stays as the language-neutral
  guard for the agent-internal path; the structural row-fold covers the
  agent-pipe-recorded path. This is the correct split, not a gap.

## Status / order
- Phase 1 (MCP contract) — ✅ done.
- Phase 2 (standard tool-loop) — ✅ already realized inside Hermes (full loop +
  full capabilities in the MiOS pipeline); only optional executor-reliability
  tuning remains, done live. Three standard tool projections now exist off one
  SSOT: MCP (`/v1/verbs`), OpenAI-tools (`/v1/verbs/openai-tools`), A2A skills.
- Phase 4 (A2A) — ✅ publish (agent card) + consume (tag-SSOT routing) +
  federation (peer discovery + `a2a_delegate`/`transfer_session_to_agent`)
  shipped.
- Phase 3 (retire bespoke dispatch/hardcodes) + Phase 5 (structural validation)
  remain as cleanups; neither blocks the working pipeline.

The end state these phases serve: the agentic OS half of MiOS coordinates and
executes entirely through open standards, off the one `mios.toml` SSOT, so the
same image runs the same way on any hardware — and a discovering MCP/A2A peer
can drive or be driven by a MiOS node with zero bespoke glue.
