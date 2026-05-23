# MiOS AI — End-to-End Pipeline Map

How a user message becomes an answer in MiOS: every query-resolution path,
the loops inside each, and where they branch. Grounded in
`usr/lib/mios/agent-pipe/server.py` (the orchestrator) +
`usr/share/mios/owui/pipes/mios_agent_pipe.py` (the OWUI front).

Everything below runs **100% locally** — local Ollama lanes, local Hermes
gateway, local SearXNG, local SurrealDB. No cloud AI, no CDN at runtime.

---

## 0. The prime directive (read this first)

MiOS does **not** let a sub-agent write the answer. The pipeline is shaped
around one rule the operator set:

> **Refine PREPARES the plan. Sub-agents only emit think-blocks + tool results.
> Polish PREPARES the final, user-facing answer.**

So every path has the same skeleton:

```
   user → REFINE (plan + route) → [one or more backends do the work] → POLISH (the answer)
```

The backends differ in *how many agents* engage and *how they're wired*
(single, council, swarm/DAG), but they always feed raw material UP to polish,
which consolidates it into the operator's voice. Sub-agent reasoning is shown
to the user only inside a collapsible `<details type="reasoning">` think-block;
the visible answer is always polish's output.

---

## 1. Components (the 10,000-ft view)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  OWUI chat  (Open WebUI)                                                   │
│    • injects persona / locale / language system messages                   │
│    • injects mios_flags toggles: 🧩 delegate · full-swarm · force-tool      │
│    • renders sub-agent output → <details> think-block; polish = visible     │
└───────────────┬────────────────────────────────────────────────────────────┘
                │  OpenAI /v1/chat/completions (SSE stream)
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  mios-agent-pipe  (FastAPI, server.py)  ── THE ORCHESTRATOR / ROUTER       │
│                                                                            │
│   REFINE ─► route ─► { chat | dispatch | agent | swarm/DAG } ─► POLISH     │
│      │                         │                                  │        │
│   qwen3.5:4b              Hermes + council               qwen3.5:4b        │
│   (think:false)           + per-agent DAG               (persona applied)  │
└──┬─────────────┬───────────────┬──────────────────────────┬───────────────┘
   │             │               │                          │
   ▼             ▼               ▼                          ▼
 micro lane   Hermes :8642   sub-agent registry        SurrealDB
 (iGPU/ROCm)  OpenAI gateway  [agents.*] in mios.toml   (session, tool_call,
 classify/    standard         opencode, daemon-agent,   knowledge, scratchpad,
 refine/web   tool-loop        client nodes…)            events)
                  │
                  ▼
            verb dispatch  ── _build_dispatch_cmd ──►  launcher broker
            (SSOT [verbs.*].cmd templates in mios.toml)   │
                                                          ▼
                                              mios-* shell verbs / helpers
                                              (mios-winget, mios-web-search,
                                               mios-discord-send, mios-window…)
```

**Lanes & models (SSOT: `mios.toml`, overridable by env):**

| Role | Model (default) | Lane | Notes |
|---|---|---|---|
| Refine (routing) | `qwen3.5:4b` | dGPU | `think:false`; `keep_alive=30m` to kill the cold-start gap |
| Polish (answer) | `qwen3.5:4b` | dGPU | persona applied; the real output step |
| Classify / micro | `qwen3:1.7b` / `0.6b` | iGPU (ROCm, `mios-ollama-igpu`) | cheap intent + task-gen |
| Hermes orchestrator | `mios-hermes` | dGPU | `:8642` OpenAI gateway, full tool-loop |
| Swarm decomposer | `qwen3.5:4b` | dGPU | `_plan_swarm`; `/api/chat think:false` |
| Vision | `llama3.2-vision:11b` / `qwen3-vl:4b` | dGPU | image turns bypass refine |
| Planner (gated OFF) | `gemma4:e4b` → `mios-planner` | — | `PLANNER_ENABLED=false` (VRAM) |
| Embeddings | `nomic-embed-text` | — | knowledge recall + RAG |
| Secondaries (fan-out) | per-agent `cpu_model` twin | CPU | offloads so dGPU stays free for primary |

---

## 2. The master resolve flow (the router)

This is the decision tree inside `chat_completions`. Each diamond is a
short-circuit — the first one that matches *returns*, so simple queries never
pay for machinery they don't need.

```mermaid
flowchart TD
    A["user message + history"] --> V{"image in turn?"}
    V -- yes --> VLM["VISION: local VLM direct<br/>(no refine / no Hermes)"] --> OUT
    V -- no --> S[("open SurrealDB session row")]
    S --> R["REFINE_INTENT — qwen3.5:4b, think:false<br/>→ intent, refined_text, target_agent,<br/>hint_tools, hint_skills, tasks?, reply?"]

    R --> Cbypass{"trivial input?<br/>(&lt; 24 chars)"}
    Cbypass -- yes --> RT["layer-1 router<br/>classify_intent"]
    Cbypass -- no --> C1{"intent == chat?"}

    C1 -- yes --> CHAT["CHAT FAST-PATH<br/>refine.reply / _quick_chat_reply<br/>NO backend, NO Hermes"] --> OUT
    C1 -- no --> MT{"intent == multi_task<br/>and &ge;2 tasks?"}

    MT -- yes --> SHQ["shadow-queue to kanban_shadow"] --> AD1["per-agent DAG<br/>_respond_agent_dag<br/>(concurrent + synthesize)"] --> POL
    MT -- no --> DEC{"force_delegate OR _multi_step<br/>OR decompose-by-default<br/>(and PLANNER_ENABLED)?"}

    DEC -- yes --> SW["_plan_swarm → _agent_dag_from_tasks<br/>fallback: decompose_intent"]
    SW --> SWok{"&ge;2 agents OR a WRITE action?"}
    SWok -- yes --> AD2["per-agent DAG<br/>_respond_agent_dag"] --> POL
    SWok -- no --> AG
    DEC -- no --> AG

    AG["AGENT PATH (unify-on)<br/>refine → Hermes streamed<br/>+ council secondaries"] --> POL
    POL["POLISH — qwen3.5:4b<br/>persona + language applied"] --> KS[("store knowledge<br/>fire-and-forget")]
    KS --> OUT(["SSE stream to OWUI"])
```

**Override toggles** (per-turn, from the OWUI chat-bar → `body.mios_flags`,
stripped before Hermes sees them):

- `force_council` → engage the **full swarm** (every eligible agent, equal weight).
- `force_delegate` (🧩) → **force** per-agent DAG decomposition; if the planner
  declines, escalates to `force_council` so the toggle never collapses to one agent.
- `force_tool` → `tool_choice=required` on the executor (anti-narration guard).

These override the `mios.toml [dispatch]` SSOT defaults **for that turn only** —
the "forced vs. natural" control, in the spirit of OpenAI `tool_choice`.

---

## 3. The five backend patterns (and the loop inside each)

### 3a. Chat fast-path — *no backend*
`intent=chat` (and no force flags) → use `refine.reply`, or generate one with
`_quick_chat_reply`. Streams straight out. This is the sub-50 ms path that keeps
"hey, how's it going?" from triggering a 30–90 s Hermes tool cascade.
**Loop:** none. One model call, already done by refine.

### 3b. Dispatch fast-path — *one verb, no LLM answer* (unify-off only)
Layer-1 router returns `{action:dispatch, tool, args}` → `dispatch_mios_verb` →
broker → result wrapped in an OpenAI-shaped `tool_call` + `tool_result`
`<details>` envelope. A `tool_call` row is written to SurrealDB.
**Loop:** none — single tool execution. (Under unify-on this folds into the agent path.)

### 3c. Agent path (unify-on default) — *Hermes + live council*
The workhorse. `intent=agent` →

```
   refine plan ─► Hermes orchestrator (:8642, standard OpenAI tool-loop)
                     │   while (model emits tool_calls):
                     │       run verb via broker → feed tool_result back
                     │   until: final assistant message (no more tool_calls)
                     │
                     ├─► COUNCIL secondaries fan out CONCURRENTLY (equal weight)
                     │       every chat-eligible [agents.*] node, bounded by
                     │       _agent_sem (MIOS_AGENT_CONCURRENCY) + jitter
                     │
                     ▼
   merged asyncio.Queue  ◄── primary pumped in background
                         ◄── secondaries push events: PR/PT/SF/PD
                     │
                     ▼
   one think-block stream (live reasoning) ─► critic ─► POLISH (the answer)
```

- **Hermes tool-loop** = the standard OpenAI tool-call loop. The model decides,
  emits a `tool_call`, the broker executes the verb, the result is fed back; it
  repeats until a final message. This is the one part already on open standards.
- **Council** = *equal weighting*: every eligible agent answers the same prompt
  in parallel. Secondaries stream their reasoning **live** into the think-block
  while the primary is still in its silent tool-loop, via one merged queue
  (race-free). Secondaries prefer their `cpu_model` twin so the dGPU stays free.
- Each hop carries the **refined plan injected as a system-message prefix** — no
  sub-agent ever runs on raw user text.

### 3d. Swarm / per-agent DAG — *split one goal across agents, then synthesize*
Triggered by `multi_task` (≥2 itemized tasks), `_multi_step`, the 🧩 toggle, or
**decompose-by-default** (a substantive agent ask ≥ N words).

```
   _plan_swarm (qwen3.5:4b)  →  [ {agent, sub-task}, … ]   (self-gates: [] if trivial)
        │  fallback → decompose_intent (general verb-DAG planner)
        ▼
   _agent_dag_from_tasks → DAG {nodes:[{agent|tool, deps}]}
        │  taken only if ≥2 agents OR contains a WRITE action
        ▼
   _execute_dag_emitting → run nodes concurrently, respecting deps
        │   per-node live emitters:  🛰️ engaged · ✅ responded · 💤 silent
        │   (each shows lane · model · endpoint)
        ▼
   🧬 synthesis → POLISH → one answer
```

**Loop:** the DAG executor — nodes with satisfied dependencies fire in parallel
(shared `_agent_sem`), their outputs gate downstream nodes, until the graph drains.
Distinct agents/lanes do *distinct* work (not a Hermes duplicate).

### 3e. Vision — *direct to VLM*
An image-bearing turn can't be served by the text executor, so it bypasses
refine/planning/Hermes entirely and goes straight to the local VLM. No session
or refine overhead. **Loop:** none.

---

## 4. Cross-cutting loops & context (active across all backends)

These aren't separate paths — they wrap the backends above.

| Mechanism | What it does | Where |
|---|---|---|
| **Knowledge recall** | Embed-at-write + cosine recall of prior Q&A, threshold-gated, injected into each agent's `_sys_prefix`. | `_recall_knowledge` |
| **Knowledge store** | Every finished Q&A (+ derived sources: verbs invoked, URLs) persisted to SurrealDB `knowledge`, fire-and-forget after polish. | `_store_knowledge` |
| **RAG enrich** | Pulls from OWUI knowledge collections (embeddings via `nomic-embed-text`) into the prompt. | `_rag_enrich` |
| **Per-chat scratchpad** | Rolling cross-agent blackboard keyed by OpenAI `metadata.chat_id`, contextvar-threaded so concurrent council/DAG tasks inherit it; rendered into every node's prompt. | `_scratchpad_note` / `_scratchpad_render` |
| **A2A / ACP context** | The same blackboard exposed in open `Message{role,parts[],contextId}` shape at `GET /a2a/contexts/{id}`. | `_a2a_messages_for` / `_a2a_context` |
| **Web fan-out** | One `web_search` query expands into K concurrent sub-queries → RRF merge (in `mios-web-search`), bounded by a semaphore. | verb → helper |
| **Temporal grounding** | `today`/`tomorrow` injected into refine/polish/dispatch (fixes "tomorrow = today"). | refine/polish |
| **Anti-fabrication (P5)** | Structural check flags narrated-but-not-executed WRITE actions (`write_action_unmet`) to polish, so the model can't fake "I posted it." | `refine_intent` post-pass |
| **Satisfaction / auto-halt** | `mios-daemon-agent` runs a Definition-of-Done checker across tool_call/window/file/URL signals; emits `user_query_satisfied`; agents halt on that instead of looping. | `mios-daemon-agent` |

### Verb dispatch (the bottom of every action)
When any agent invokes a verb, `_build_dispatch_cmd(tool, args)` renders it.
**SSOT first:** a verb with a `cmd` template in `mios.toml [verbs.*]` renders via
the catalog (`_template_to_cmd`); only verbs whose logic genuinely needs code
(conditionals, enums, base64 staging, recursion) keep a hardcoded branch. The
rendered line goes to the launcher broker, which runs the `mios-*` helper.
Template placeholders: `{arg}` · `{arg=default}` · `{arg?FLAG}` (optional flag).

---

## 5. The bypass: task-generation calls

OWUI also fires non-conversational helper calls — **title, tags, follow-up
suggestions, autocomplete**. These do **not** touch refine / Hermes / council.
They go straight to the cheap micro model on the iGPU lane and return. Keeping
them off the main path is why the conversation list stays snappy.

```
   OWUI task-gen (title/tags/followup/autocomplete) ──► micro model (iGPU) ──► done
```

---

## 6. Live status emitters (what the user sees while it works)

The pipe streams SSE status events so the chat shows live progress, not a
spinner. Per-AI-node, during council/DAG fan-out:

| Emit | Meaning |
|---|---|
| 🛰️ | node **engaged** (lane · model · endpoint) |
| ✅ | node **responded** |
| 💤 | node **went silent** (e.g. a client node that's asleep; short-timeout drop) |
| 🧬 | **synthesis** pass running (covers the gap before polish) |

Phase events (`prompt` → `refine` → backend → `…_done`) drive the top-line
status. Client-hosted nodes (a phone over Tailscale) auto-join when up and
auto-drop when gone (`health_gate` → short timeout).

---

## 7. One query, traced end-to-end

> **User:** "find the biggest log files under /var and tell me what's filling them"

```
1. OWUI       → injects persona+locale, no flags. POST /v1/chat/completions (stream).
2. refine     → intent=agent, refined_text + hint_tools=[fs_search, directory_lookup,
                system_logs], target_agent=hermes. (not chat, not multi_task)
3. decompose? → substantive agent ask ≥ N words → _plan_swarm. Self-gates: this is
                ONE goal with dependent steps, not 2 independent goals → falls through.
4. agent path → Hermes tool-loop:
                  tool_call fs_search(path=/var, type=f, …)      → broker → results 🛰️✅
                  tool_call directory_lookup(...) / system_logs  → broker → results
                council secondaries stream reasoning live into the think-block.
                knowledge recall + scratchpad injected into the prompt.
5. polish     → consolidates tool results into a ranked answer, operator's voice,
                correct language. 🧬→ visible reply; raw reasoning in <details>.
6. store      → Q&A + sources (verbs, paths) → SurrealDB knowledge (fire-and-forget).
```

If the same user had said *"install VS Code **and** open it"* → step 2 yields a
**dag** (one goal, dependent steps) → `_respond_agent_dag` runs
`winget_install` then `open_app` in order, emitting per-node status, then polish.
If they'd said *"check disk usage, summarize my unread mail, and list running
containers"* → **multi_task** (3 independent goals) → concurrent per-agent DAG →
synthesize one answer.

---

## 8. Design invariants (why it's shaped this way)

- **Nothing hardcoded** — models, ports, agents, verbs, recipes, and tunables
  all flow from `mios.toml` (SSOT) → `${MIOS_*:-default}`. Command literals live
  in the `mios-*` helpers, not in dispatch.
- **No canned English** — status text and gates are generated, not hardcoded
  strings; intent routing is model-decided, with **no topic deny-lists**.
- **Full offline** — every lane, gateway, search, and DB is local.
- **Truthful actions** — a real ask → a real `tool_call` → a real result; the P5
  check + `force_tool` exist to stop the model *narrating* an action it didn't take.
- **Fast path stays fast** — trivial input skips refine; chat skips the backend;
  task-gen skips everything but the micro model.

---

*Source of truth: `usr/lib/mios/agent-pipe/server.py`. This map is descriptive —
when in doubt, the code (and `mios.toml`) wins. Related:
`docs/agentic-standards-roadmap.md`, `docs/agentos-roadmap.md`.*
