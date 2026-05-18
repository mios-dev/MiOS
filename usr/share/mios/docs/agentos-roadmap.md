# MiOS AgentOS Roadmap

Architectural roadmap for evolving the MiOS agent stack toward the
2025-2026 AIOS / AgentOS reference architecture. Phases ordered by
operator-impact-per-line-of-code, not by formal completeness.

## Current state (pre-roadmap)

| AgentOS principle | MiOS implementation | Gap |
|---|---|---|
| Tripartite layer (App/SDK/Kernel) | OWUI -> mios-agent-pipe (:8640) -> hermes-agent (:8642) | No formal SDK boundary; mios-agent-pipe IS the SDK in practice |
| MCP-style tool execution | mios-launcher broker (CAPTURE_JSON), typed verbs, LiteCUA via mios-pc-control + mios-windows | Strongest piece in MiOS |
| Multi-frontend through one chain | OWUI shipped; Discord/Slack/Telegram pending Step 4/5 | OWUI works; Discord pending |
| Shared cross-cutting state | SurrealDB: agent / session / tool_call / event / kanban_shadow / scratch / agent_metric | Works |
| Local memory (per-agent) | hermes/.hermes/*.db, mios-daemon/state.json, OWUI webui.db | Works |
| iGPU resource lane | mios-ollama-igpu at :11435 for micro-LLMs | Live; WSL falls back to CPU (kernel doesn't expose /dev/kfd) |
| Query decomposition into DAG | router emits ONE action; no DAG | **GAP A** |
| Deliberative Collective Intelligence | single-pass critic loop, informal | **GAP B** |
| Document-mutation event bus | hermes-tail/*.json + nudges (polled) | **GAP C** (no inotify pub/sub) |
| Personal Knowledge Graph | flat OWUI memory only | **GAP D** |
| Sequential Pattern Mining | none | **GAP E** |
| Taint-aware memory + Semantic Firewall | none | **GAP F** |
| Agent Passports / crypto identity | sysuser uids only | **GAP G** |

Operator-observed failures these gaps caused:
- "open notepad and type hello and save to documents" -- monolithic
  handling; Hermes tried random paths because no DAG split into
  open_app -> focus -> type -> save chain (GAP A)
- "Hermes claimed it launched but didn't" -- single-pass critic
  didn't FALSIFY the success claim (GAP B)
- daemon polling 3 sideband JSONs at 5-min ticks vs reacting
  on-mutation (GAP C)

## Phase A -- foundational gaps (commit 1-3)

### A.1 -- DAG query decomposition via orchestrator-subagent

**Reference**: Anthropic's multi-agent research system pattern --
NOT DeepSieve verbatim (DeepSieve needs DeepSeek-V3-scale planner;
operator-stack tops out at qwen2.5-coder:7b for the decomposer).
~300 LoC in `mios-agent-pipe`, no new heavy deps.

**Shape**:
- New router action: `decompose`. Returns:
  ```
  {"action": "decompose",
   "nodes": [
     {"id": "n1", "tool": "open_app", "args": {"name": "notepad"}, "deps": []},
     {"id": "n2", "tool": "focus_window", "args": {"title": "Notepad"}, "deps": ["n1"]},
     {"id": "n3", "tool": "pc_type", "args": {"text": "hello"}, "deps": ["n2"]},
     {"id": "n4", "tool": "pc_key", "args": {"keys": "ctrl+s"}, "deps": ["n3"]}
   ]}
  ```
- agent-pipe runs nodes topologically; failures retry up to 2x
  (reflexion cap) before pruning + asking operator.
- Each node emits a SurrealDB tool_call row tagged with the DAG id
  + parent edges -- gives a full audit trail for multi-step intents.

**Decomposer model**: qwen2.5-coder:7b (function-calling-tuned),
not qwen3:1.7b (too small for reliable multi-hop per community
reports).

### A.2 -- inotify-backed document-mutation event bus

Replace the 3 separate poll loops in mios-daemon (hermes-tail,
delegation-prefilter, log-watcher) with one inotify watcher on
`/var/lib/mios/*/` directories. Hooks emit SurrealDB.event rows.
Agents (mios-daemon, agent-pipe critic, future Kanban dispatcher)
SELECT FROM event WHERE source = X AND ts > <last_seen>.

### A.3 -- Taint-aware memory tags

When agent-pipe's broker dispatch returns a tool_call result whose
source is untrusted (e.g. web fetch, RAG document, external API
response), tag the result content with `tainted = true` before it
enters the chain's context. A small pre-execution check in the
Semantic Firewall (Phase B.3) refuses high-privilege follow-up
verbs (service_restart, container_restart, open_url to non-allow-
listed domain) if any tainted content is in context.

## Phase B -- deliberation upgrade (commit 4-6)

### B.1 -- DCI 14-act vocabulary as structured output

Define the typed-acts schema (14 acts: frame/clarify/reframe,
propose/extend/spawn, ask/challenge, bridge/synthesize/recall,
ground/update, recommend). Each agent reply in deliberation MUST
emit JSON with an `act` field. Lets us tag SurrealDB.event with
the act type + run analytics on which act fired before resolution.

### B.2 -- DCI-CF convergent flow critic (replaces single-pass)

4 personas on hermes-agent + one ollama model (Framer / Explorer /
Challenger / Integrator). Bounded loop: R_max=3 rounds, K_max=4
candidate finalists. Always emits a decision packet {choice,
rationale, minority_report, reopen_triggers}. Tensions preserved
as first-class objects in SurrealDB.event(kind="dissent").

Single-model role-playing works per the DCI paper (Gemini 2.5
Flash, 4 differentiated system prompts). Diversity helps but isn't
required.

### B.3 -- Semantic Firewall pre-MCP-dispatch

Small Python layer in agent-pipe. Before any WRITE-class verb
fires, check:
- Operator's original DAG (from A.1) authorized this verb
- No tainted content (from A.3) in agent context
- Action target is consistent with the DAG node's `args`
On violation: abort + emit SurrealDB.event(kind="firewall_block",
severity="high") + surface to operator.

## Phase C -- long-horizon autonomy (commit 7+)

### C.1 -- Personal Knowledge Graph in SurrealDB graph mode

SurrealDB is multi-model -- native graph support. New tables:
`person`, `pref`, `device`, `app_install`, with RELATE edges. Per-
operator graph queried by router/refine to ground ambiguous terms
("my browser" -> RELATE preference -> chromedev).

### C.2 -- Sequential Pattern Mining over tool_call history

SurrealDB.tool_call is already populated (since Phase-2 SurrealDB
writes). SPM job runs on schedule (mios-daemon? new mios-pattern
service?), finds repeating N-grams in (tool, args) tuples, codifies
as a Hermes skill or agent-pipe verb. Operator gets a "you did X
3 times in 2 days; want me to make it a skill?" nudge.

### C.3 -- Agent Passports (signed identity tokens)

Each agent gets a private key at sysuser provisioning. Every
SurrealDB write signs (agent_id, ts, op_hash). Cryptographic chain
of action attribution. Useful when delegation goes deep (operator
-> Hermes -> sub-agent -> tool).

## What stays put

The MCP-style execution layer (mios-launcher broker, mios-pc-
control, mios-windows, typed verbs) is already strong; the
research validates it. No changes planned. The dual-ollama lane
(iGPU micro-LLMs / dGPU big models) is novel vs the reference
architecture and stays.

## Cross-cutting

Every phase respects the existing operator rules:
- mios.toml + html SSOT (no hardcoded values; per-phase knobs go
  into the TOML chain)
- no hardcoded English in agent surfaces
- bootc-immutable code paths; mutable state under /var
- full offline; no cloud calls baked in

Open questions before implementation:
- Phase A.1 decomposer model: confirm qwen2.5-coder:7b vs trying
  Hermes-3-8B (more tool-tuned)
- Phase A.2: inotify or fanotify? inotify simpler; fanotify
  catches more cases. Default inotify unless operator wants the
  fanotify generality.
- Phase B.2 personas: 4 prompts on hermes-agent (cheaper) or 4
  separate ollama instances (heavier, true isolation)?
