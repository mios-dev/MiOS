<!-- AI-hint: Architectural roadmap for the agent-pipe system within MiOS — establishes the 2-stage classify→execute routing, OpenAI API conformance, and the unified tools/skills/recipes capability catalog as the source of truth for tool selection. Historical master plan (2026-06-07); reflects the migration to mios-llm-light/pgvector. -->
# MiOS agent-pipe — OpenAI-standards conformance + 2-stage routing + unified capability catalog

**Master plan (2026-06-07).** Synthesis of three research passes (OpenAI tool-routing
on llama.cpp; tools/skills/recipes unification; full OpenAI API standards) into one
sequenced roadmap. Every claim below is grounded in the cited research; this doc is the
SSOT for the work. Guiding constraints (operator, binding): **no hardcoded English routing
rules** (use schemas + SSOT, not prose); **keep ALL MiOS functionalities** (every change is
additive + fail-safe to current behaviour); **mios.toml is the SSOT**.

> **Status note (2026-06-13).** This is a planning/roadmap document, kept as the design
> record for the agent-pipe routing + standards work. Names were reconciled during the
> later migration: the local inference lane is **mios-llm-light** (llama.cpp behind the
> `mios-llm-light` proxy image, `:11450`) serving chat models + embeddings; the agent
> datastore is **PostgreSQL + pgvector** (`mios-pgvector`). The OpenAI/Ollama-compatible
> API surface and the upstream `mios-llm-light` image are still the engine; only the MiOS
> unit identity changed. The design and sequencing below are unchanged.

## Purpose — where this fits in MiOS as a whole

MiOS is one system built two ways at once: an **immutable bootc/OCI Fedora
workstation** (the whole OS is a single container image you boot, `bootc upgrade`
like a `git pull`, and `bootc rollback` like a Ctrl-Z) that is *also* a **local,
self-replicating, agentic AI operating system**. The build pipeline assembles the
image, the bootc lifecycle carries it forward, and inside that image a full local
agent stack lives behind one OpenAI-compatible endpoint (`MIOS_AI_ENDPOINT`,
Architectural Law 5).

This document covers the **brain of that stack**: the `agent-pipe` orchestrator
(`:8640`) and how it should select and dispatch capabilities. A user request flows
from a front-end (OWUI `:3030`, the Discord gateway, the `mios` CLI) into agent-pipe,
which **refines** it, **routes** it, **fans it out** across a council/swarm, dispatches
tool/verb calls, and **polishes** the answer. **MiOS-Hermes** (`:8642`) is the
OpenAI-compatible gateway and tool-loop agent; **mios-llm-light** (`:11450`) does the
generation and embeddings (heavy lanes `mios-llm-heavy`/`mios-llm-heavy-alt` are gated
on VRAM); **pgvector** (`:5432`) is the unified agent memory and knowledge substrate;
**MCP** exposes the tool surface and **A2A** federates peer agents.

The two failure modes this plan removes are the operator's core pain:
**mis-routing** (the planner picks the wrong verb because the catalog is lumped into a
few broad sections) and **client incompatibility** (gaps against the OpenAI
Chat-Completions contract). Fixing them makes the agentic half of MiOS both
*accurate* (the right tool fires) and *portable* (any OpenAI client speaks to it),
which in turn advances the AIOS/MCP/A2A federation roadmap already in memory — each
move here maps almost 1:1 onto the existing pipeline, verbs, MCP serve, and state
substrate.

## 0. What is already true (verified this session)
- Entire pipeline runs on **gemma4:12b** (one resident model on the 4090; VRAM 1.8→10.3 GB,
  72% util; chat + reasoning_content split verified), served by mios-llm-light (`:11450`).
  `refine→swarm/DAG→synthesis→polish`.
- `/v1/chat/completions` (stream + function-tools), `/v1/models`, `/v1/embeddings` served;
  MCP endpoint served; per-chat blackboard + knowledge DB (**PostgreSQL + pgvector**) as
  state substrate.
- **Root-caused the mis-routing:** the planner sees all 82 verbs grouped under a few broad
  `section`s — esp. "Discovery / resolution" lumping web+files+apps+memory — so a small/large
  model alike picks the wrong verb (research→OS-probes; "what does <script> do"→mios_apps).
- **Fix proven (5/5):** a constrained-enum domain classifier (`response_format` json_schema +
  thinking-OFF) classifies the query's domain correctly, incl. both prior mis-routes.

## 1. Routing fix — 2-stage classify→execute (CORE; partially built)
Per the llama.cpp research, the load-bearing facts:
- llama-server (the engine mios-llm-light runs behind the `mios-llm-light` proxy) supports
  `response_format: json_schema` → GBNF grammar; **enum-of-strings is the most reliable
  constraint**. `--jinja` is set; mios-llm-light forwards `response_format`/`tools`/
  `tool_choice` untouched (no `strip_params`).
- **CRITICAL #20345:** grammar is silently dropped when thinking is ON → **Stage-1 MUST run
  thinking-OFF**. **Fail-open #19051:** a grammar-parse failure returns HTTP 200 unconstrained →
  **validate the label in code**, never trust 200.
- tool_choice `auto`/`required`(`any`)/named all supported.

**Design:**
- **Stage 1 — `_route_domain(query)`**: classify into ONE domain via the enum (thinking-OFF,
  validate against the catalog). DONE as a standalone, 5/5.
- **Stage 2 — domain-filtered decompose**: the planner sees only that domain's ≤20 verbs
  (inject by `.replace()`-ing the rendered catalog block with a domain-filtered render at the
  decompose call site — minimal, no constant restructure).
- **FAIL-SAFE:** unknown/empty/low-confidence domain → FULL surface (current behaviour) → no
  capability lost; swarm/council/DAG unchanged.

**SSOT done:** `mios.toml [routing.domains.*]` maps all 82 verbs → 9 domains + per-domain
"use-when" `desc` (the classifier reads these). `router_enable` master switch.

## 2. Unified capability catalog — tools + skills + recipes (NEXT)
Per the tools/skills/recipes research: **unify the catalog, keep the kinds.**
- One SSOT catalog; every row tagged `kind ∈ {tool, recipe, skill}` + `domain`.
  - `kind=tool` = the 82 verbs (have `section`→seed `domain`).
  - `kind=recipe` = `[recipes.*]` — surfaced as **function-tools** (deterministic "subgraph-as-tool").
  - `kind=skill` = lightweight **metadata rows** (name/desc/domain/version/path); the SKILL.md
    body stays a file (progressive disclosure) and is invoked via the existing
    `skill_view`/`skill_invocation` loop — **never flatten skill bodies into the tool list**.
- **Routing across kinds:** Stage-1 picks domain(+kind); Stage-2 loads that domain's tools+recipes
  as function-tools and skills as description-only. <20 capabilities/turn.
- **Composition rules:** recipes→tools OK; skills→tools/recipes OK; **recipes→skills FORBIDDEN**
  (keeps recipes deterministic); cycles guarded by the existing in-flight dedup. Version
  skills/recipes `(author,name,version)` (feeds A2A federation).
- **Standard mapping:** MiOS verbs→MCP tools; recipes→MCP **prompts**; skills→filesystem SKILL.md
  advertised via **A2A** — all rows live in `mios.toml` (SSOT); `_VERB_CATALOG` 3-projection extends.

## 3. OpenAI standards conformance — Tier 0/1/2 (from the standards research)
**TIER 0 — conformance fixes (do first; low effort, high client-compat payoff):**
1. **Emit `usage`** (non-stream + `stream_options.include_usage` → final empty-`choices` chunk).
   Use **aggregated REAL** tokens across pipeline back-end calls (honest, not faked). The one
   documented gap today.
2. **Verify the streaming contract:** first chunk `delta.role:"assistant"`; per-`index` tool-call
   deltas with `arguments` as **string** fragments; finishing chunk with `finish_reason`; literal
   `data: [DONE]` last.
3. **OpenAI error object** everywhere: `{"error":{message,type,param,code}}` + correct status
   (400/401/429/500) + rate-limit headers.
4. **Accept `developer` role** (≥ system); accept-and-ignore unknown-but-standard params
   (`stream_options`, `parallel_tool_calls`, `reasoning_effort`, `response_format`).
5. **Confirm `finish_reason:"tool_calls"`** whenever tool calls are returned; `arguments` a JSON string.

**TIER 1 — standards hardening (medium):**
6. **Strict-mode function schemas** on verbs (`strict:true`, `additionalProperties:false`,
   all-required); honor `tool_choice` (+`allowed_tools`) + `parallel_tool_calls`.
7. **Structured Outputs** exposed (`response_format json_schema strict` + `refusal`). The 2-stage
   router already uses this internally → makes it OpenAI-canonical.
8. **Prompt-cache-friendly ordering** (static instructions/tool-defs first, variable last) to
   maximize llama.cpp prefix reuse; report `cached_tokens` in usage.
9. **`reasoning_tokens`** in `usage.completion_tokens_details` for gemma4; keep the OWUI
   `<details type="reasoning">` think-block for Chat-Completions clients.

**TIER 2 — adopt the new standard (`/v1/responses`); additive, strategic:**
10. **Add `/v1/responses`** (Chat Completions stays for OWUI): pipeline stages/sub-agents/verbs →
    **items**; gemma4 reasoning → **reasoning items** (`content`/`summary`/`encrypted_content`);
    per-chat blackboard + knowledge DB → `store`/`previous_response_id`.
11. **MCP via the Responses `mcp` tool type** (`mcp_list_tools`/`mcp_call`/approval items) — MiOS's
    own model treats its served MCP endpoint + tailnet A2A peers as hosted tools (advances the
    P0→P1 MCP/A2A consume+federate roadmap).
12. **Hosted-tool surface** in Responses for web_search/coderun/computer-use verbs where names line up.

## 4. Build order (sequenced; each step deploy+test, fail-safe, reversible)
1. **Tier-0 conformance** (usage + streaming contract + error object + roles) — independent of routing,
   unblocks perfect OWUI/client compat. *Gate: OWUI shows tokens; `[DONE]`/tool-deltas verified.*
2. **Routing Stage-1+2** (wire `_route_domain` + domain-filtered decompose; fail-safe). *Gate:
   research→web→web_search; "what does <script> do"→code/files (not mios_apps); broad sweep; nothing lost.*
3. **Unify catalog** (add `kind`+`domain`; recipes as function-tools; skills as description-only).
   *Gate: a recipe + a skill route + invoke correctly via their domain.*
4. **Tier-1 hardening** (strict schemas + structured outputs + cache ordering + reasoning_tokens).
5. **Tier-2 `/v1/responses`** (additive) + MCP-as-hosted-tool.

## 5. Net assessment
MiOS is **substantially Chat-Completions-conformant**; the only thing that can break clients today
is the **omitted `usage`** + the streaming/error-shape details (Tier 0, cheap). The **routing fix**
(proven) is the operator's core pain. The **unified catalog** and **`/v1/responses`** are the
strategic moves that also advance the AIOS/MCP/A2A roadmap already in memory — each maps almost 1:1
onto MiOS's existing pipeline, verbs, MCP serve (mios-llm-light + Hermes), and pgvector state
substrate. Done, these make the agentic half of the immutable MiOS image both accurate in its tool
selection and portable to any OpenAI client — the contract the rest of the system builds on.
