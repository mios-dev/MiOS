# MiOS Agentic Standards Roadmap (MCP · OpenAI tool-loop · A2A/ACP)

Operator directive 2026-05-22: "NOTHING hardcoded anywhere; fix in code to
OpenAI-API standards and patterns for multi-agentic solutions using
open-source tools, locally hosted. Research, then refine to specs — ACPs,
MCP, etc." Roadmap requested ("you sequence it, I pick").

## Why
Every recurring failure traces to NON-STANDARD, hardcoded plumbing:
- the 4B executor **narrates** "I posted to Discord" instead of emitting a
  real `tool_call` (no standard tool-loop) → the lie;
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

### Phase 2 — Standard OpenAI tool-call loop in the orchestrator  ·  effort: H  ·  risk: HIGH  ·  THE core fix
- agent-pipe runs the canonical agentic loop against the local model + the
  MCP server: offer tools via the OpenAI `tools=` param → model returns
  `tool_calls` → execute each via the MCP client (`tools/call`) → feed
  `role:tool` results back → repeat until the model stops calling → final
  answer grounded in REAL results.
- Structurally kills narration (acting REQUIRES a `tool_call`) + the lie (a
  claim can't exist without a tool result) + Discord (it becomes a tool the
  loop executes, not prose).
- Decision: the loop lives in agent-pipe (model ↔ MCP), the standard place,
  rather than relying on the 4B's internal narration.
- KEY RISK / cross-cutting: local-model function-calling reliability. Mitigate
  with a tool-capable executor model (qwen3.5:4b supports tools; size up if
  needed) and `tool_choice` forcing for clear action intents. This phase is
  make-or-break and gates Phases 3 + 5.

- FINDING (2026-05-22): the tool-loop already exists INSIDE Hermes, not
  agent-pipe. agent-pipe (`/v1/chat/completions`) is the refine/route/polish/
  critic orchestration layer; it FORWARDS `proxy_body` to Hermes and Hermes
  runs its own tool-loop (`server.py:6824`). Hermes is NOT bound to a narrow
  tool set: it carries its FULL tool registry (its own built-ins incl a
  terminal/shell + web/file tools) PLUS the MiOS verb + skill surface --
  `discord_send`, os-control, browser etc. are all reachable. So the
  narrate-instead-of-call LIE is NOT a missing-tool problem; it is an
  EXECUTOR-BEHAVIOUR problem: the small model (`hermes/config.yaml` default
  `granite4.1:3b`) emits prose ("I posted to Discord") instead of emitting
  the `tool_call` it is fully able to. Fixing it is reliability work, not
  plumbing.
- SHIPPED (standards surface, NOT the narration fix): `GET /v1/verbs/
  openai-tools` -- the verb catalog in OpenAI `{type:function,...}` shape, the
  twin of `/v1/verbs` (MCP shape) + the A2A card skills. One SSOT
  (`_VERB_CATALOG`), three projections (MCP / OpenAI-tools / A2A). For STRICT
  OpenAI / A2A / ACP clients that lack the MiOS plugin; execution via the
  existing `POST /v1/dispatch`. Hermes does NOT need it (already has the
  surface). Additive + offline-verified.
- REMAINING = the make-or-break reliability work (live-iteration; operator
  runs Hermes + tails its log -- cannot be validated offline):
  1. Pin a reliably tool-calling executor in `hermes/config.yaml` (the 3B
     default narrates; a tool-tuned / larger model emits tool_calls).
  2. Force action via `tool_choice` (or required-tool) on clear action
     intents so the loop MUST call rather than describe.
  3. SOUL/system-prompt: acting REQUIRES a tool_call; describing an action
     you did not call is a failure (reinforces, never replaces, 1+2).
  - VERIFY LIVE: in OWUI, "post X to my Discord" -> tail
    `journalctl -u hermes-agent` for a real `tool_call` (NOT prose) and
    confirm the message arrives. Same for os-control / browser.

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
- REMAINING (consume side): make `_pick_fanout_agents` route by the card's
  declared skill tags (and, with Phase 2's loop, by structural capability)
  instead of substring token overlap. Card is the SSOT it reads.

### Phase 5 — Validation → STRUCTURAL  ·  effort: M  ·  risk: LOW
- With tool results captured by the MCP loop, the confirmation engine grounds
  on actual `tool_call` outcomes. Retire the soft INVOKED-TOOL-CHECK prompt
  rule in favour of structural grounding: an action-claim is valid IFF a
  matching successful tool_call exists in the loop history. Deterministic.

## Recommended order
1 → 2 → 3 → 5, with 4 in parallel after 1. Phase 2 is the highest-impact
single change (fixes narration/lie/Discord at once); Phase 1 is its
prerequisite. Phase 4 independently kills the fan-out hardcodes.
