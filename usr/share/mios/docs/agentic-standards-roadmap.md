# MiOS Agentic Standards Roadmap (MCP · OpenAI tool-loop · A2A/ACP)

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
- **validation by a soft prompt rule** on a 4B model (misses the lie).

The fix is convergence onto the Linux-Foundation Agentic-AI standards:
**MCP** for tools, the **OpenAI tool-call loop** for execution, **A2A**
Agent Cards for coordination, **ACP** for delegated runs. All open-source,
all local, no cloud-AI dependency (Architectural Law 5).

## What already exists (build ON this)
- `agent-pipe` — OpenAI `/v1/chat/completions` endpoint (the standard surface).
- `mios-mcp-server` — MCP stdio server (JSON-RPC 2.0, spec 2025-06-18);
  renders `[verbs.*]` SSOT as MCP tools; `tools/call` → agent-pipe
  `/v1/dispatch` → launcher broker. `mios-mcp.service`.
- `opencode-gateway` — OpenAI `/v1` shim for opencode (ACP-style delegate).
- `usr/lib/mios/tools/responses-api/mcp.json` — Responses-API + MCP config.
- Helpers as clean tool backends: `mios-web-search`, `mios-sysview`,
  `mios-discord-send`, CDP browser.

So the work is WIRING + standardizing, not greenfield.

## Phases (sequenced; pick a starting point)

### Phase 1 — Complete + verify the MCP tool CONTRACT  ·  effort: M  ·  risk: LOW  ·  ✅ DONE (committed)
- Audit `mios-mcp-server`: is `mios-mcp.service` running? are ALL `[verbs.*]`
  rendered as MCP tools with correct JSON input schemas?
- Fill gaps: ensure `web_search`, `browser_*`, `sysview`, `os-control` verbs
  AND `discord_send` (new `[verbs.discord_send]` → `mios-discord-send` backend)
  are first-class MCP tools. Schemas come from mios.toml `[verbs.*]` (SSOT) —
  no hardcoded tool lists.
- Deliverable: one authoritative, schema-correct, locally-hosted MCP tool
  catalog. Additive — changes no live behaviour yet.

### Phase 2 — Standard OpenAI tool-call loop  ·  ✅ ALREADY REALIZED (in Hermes)
- The canonical agentic loop (offer tools → model returns `tool_calls` →
  execute → feed `role:tool` back → repeat → grounded final answer) already
  runs **inside Hermes**, which operates full tool-loops with its full
  capability set within the complete MiOS AI pipeline/chains. It is NOT a
  thing agent-pipe still has to build.
- Topology (corrected 2026-05-22, operator): agent-pipe
  (`/v1/chat/completions`) is the refine → route → polish → critic
  ORCHESTRATION layer; it forwards to Hermes (`server.py:6824`) which runs
  the loop, then folds the results back. Hermes is NOT bound to a narrow
  tool set — it carries its full built-in tool registry (terminal/shell,
  web, file, …) PLUS the full MiOS verb + skill surface (`discord_send`,
  os-control, browser, … all reachable). `hermes/config.yaml`'s `tools:`
  block only configures `web_search`'s provider; it is not the whole surface.
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

### Phase 3 — Retire bespoke dispatch + every remaining hardcode  ·  effort: M  ·  risk: MED
- With the MCP loop proven, delete agent-pipe's bespoke `_build_command`
  verb-arms, the dual tool paths, and any keyword/topic literals. Tools flow
  ONLY through MCP + the loop. One path, no hardcodes.

### Phase 4 — A2A Agent Cards for multi-agent coordination  ·  effort: H  ·  risk: MED  ·  ◑ PUBLISH-SIDE SHIPPED
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
  zero pipeline risk; `x-mios` block cross-links the OpenAI `/v1` + MCP
  surfaces so a discovering peer knows how to drive MiOS.
- SHIPPED (consume side): `_pick_fanout_agents` now routes on the SAME
  `_agent_skill_tags()` SSOT the card publishes, with WORD-BOUNDARY matching
  (was substring: `search` matched inside `researching`). Card capability ==
  routing key; daemon-flood guards (fanout=false + score>0 bonus gating)
  preserved. → Phase 4 effectively complete; further refinement (semantic /
  embedding match over tags) is optional polish.

### Phase 5 — Validation → STRUCTURAL  ·  effort: M  ·  risk: LOW
- With tool results captured by the MCP loop, the confirmation engine grounds
  on actual `tool_call` outcomes. Retire the soft INVOKED-TOOL-CHECK prompt
  rule in favour of structural grounding: an action-claim is valid IFF a
  matching successful tool_call exists in the loop history. Deterministic.

## Status / order
- Phase 1 (MCP contract) — ✅ done.
- Phase 2 (standard tool-loop) — ✅ already realized inside Hermes (full loop +
  full capabilities in the MiOS pipeline); only optional executor-reliability
  tuning remains, done live. Three standard tool projections now exist off one
  SSOT: MCP (`/v1/verbs`), OpenAI-tools (`/v1/verbs/openai-tools`), A2A skills.
- Phase 4 (A2A) — ✅ publish (agent card) + consume (tag-SSOT routing) shipped.
- Phase 3 (retire bespoke dispatch/hardcodes) + Phase 5 (structural validation)
  remain as cleanups; neither blocks the working pipeline.
