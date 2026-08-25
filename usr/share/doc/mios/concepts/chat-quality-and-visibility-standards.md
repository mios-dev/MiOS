<!-- AI-hint: MiOS AI Chat — Quality + Full-Visibility Gap Register
     AI-related: mios-launch, mios-locate, mios-text-edit -->
# MiOS AI Chat — Quality + Full-Visibility Gap Register

> Research-grounded gap register. Source: a live `@`/`mios`-CLI session
> (`what directory` / `what's here?`) that surfaced four chat-quality defects,
> traced to root cause by a 6-agent code audit of the `agent-pipe` orchestrator
> (`:8640`), cross-checked against 2025–2026 upstream native patterns. Companion
> to [`native-openai-visibility-and-aios-mapping.md`](native-openai-visibility-and-aios-mapping.md)
> and to `MIOS-GAP-REGISTER-2026-06-27.md`. Not tracked by the 108-task backlog.
> Timeless: describe the WHY, not the date. Every fix is SSOT-/model-driven,
> flag-gated, degrade-open (Law 7).

## 0. The thesis — full visibility and a clean answer are the SAME fix

Operator mandate, restated: **everything streams natively to every surface —
tools used, thinking/reasoning, sources, every hop of every agent.** The live
session looked like the opposite of clean (a `Refined Query/Intent/Reply` blob,
tool-call JSON as raw text, the answer restated 3×, then a non-terminating
"Reflexion" essay loop). The instinct is to read that as "too much visibility."
It is the reverse: it is visibility implemented the **wrong way** — globally
inlining raw internal blobs into `delta.content` (the answer channel) because
`[observability].debug=true` collapses the reasoning emitter onto content
(`sse.py:93-94`).

Real full visibility is **every agent activity emitted on its own native typed
channel**. That renders *richer* on every surface (Thinking pane, tool cards,
citation chips, status shimmer) AND keeps `delta.content` to exactly one clean
final answer — which is also the only KV-cache-safe, replay-safe shape
(OWUI #21815). The invariant that reconciles both goals:

> **The final answer is the ONLY thing in `delta.content`. Everything else —
> thinking, plan, tool calls + args, tool output, sources, status — rides a
> native replay-safe channel and stays fully visible on every surface.**

The channel map (what "EVERYTHING" means, concretely):

| Agent activity (all hops, incl. sub-agents) | Native replay-safe channel | Surfaces it renders on |
|---|---|---|
| Thinking / reasoning | `reasoning_content` (+`reasoning`) · Responses `reasoning` item | OWUI Thinking pane, Hermes; strict clients via folded inline |
| Plan / decomposition | structured plan object (internal) + a `reasoning`/status line | Thinking pane, status strip |
| Tools used + args | native `tool_calls` / Responses `function_call` item · `mios_status` pill | tool cards + status shimmer, every surface |
| Tool output | `reasoning_content` summary · `source` event for refs · `function_call_output` | Thinking pane + citation chips |
| Sources / citations | OWUI `source`/`citation` event | citation chips |
| Status / phase | `mios_status` → OWUI `status` event | ephemeral shimmer |
| **Final answer** | **`delta.content` — only this** | message body |

Everything below is either (a) a channel the trace is on the WRONG side of, or
(b) an activity that isn't emitted at all. The plumbing is ~90% built; the work
is routing every hop and every sub-agent into it instead of suppressing it or
content-dumping it.

---

## 1. FULL-VISIBILITY gaps (FV) — the spine

These block "every agent → every surface." FV-A and FV-E are the load-bearing
ones; the rest are coverage.

**FV-A — Sub-agent / leaf thinking is turned OFF at the source. (P1)**
Every `/v1` light-lane leaf node pops `think` and sets `enable_thinking:False`
(`agent_call.py:820-821`); swarm planner/synth do the same (`swarm.py:1237`). Leaf
agents therefore emit only their *final output*, never their *reasoning* — so
"reasoning from ALL agents" is structurally impossible today. This is a
deliberate token-budget/clean-answer choice that directly contradicts the
mandate. **Fix:** replace the blanket off with a per-lane SSOT toggle
`[lanes.*].stream_thinking` (default surfaces reasoning; degrade-open to off per
lane). No keyword logic — a config flag per inference lane.

**FV-B — Channel collapse in fan-out. (P1)**
`_push(frag)` tags every child fragment as one merged-queue event `("SF", name,
frag)` with **no channel discriminator**, and upstream `frag = _content or
reasoning_content` only forwards reasoning when content is empty
(`agent_call.py:738-746, 797-802, 878-885`). The orchestrator cannot tell a
child's *thought* from its *answer*, so child reasoning can't be routed to the
reasoning channel distinctly. **Fix:** a 3-tuple channel tag
(`content|reasoning|tool`) on the merged event so each fragment lands on its
right channel.

**FV-C — Per-node-completion granularity, not live token thinking. (P2)**
Node output streams into the reasoning block as each node *finishes*
(`swarm.py:626-632`), a burst at `done`, not token-by-token during the work.
**Fix:** forward child reasoning tokens live (pairs with FV-B/FV-D).

**FV-D — Buffered sub-agent calls forward nothing live. (P2)**
`agent_call.py` still has `r.json()` buffered hops (`573, 660, 999, 1179`); those
children stream zero reasoning — only the coarse hermes-tail file poll gives any
live signal. **Fix:** `stream=True` + reasoning-forward on all hops, or an
explicit per-hop SSOT downgrade.

**FV-E — "Full visibility" is currently faked by inlining reasoning as CONTENT. (P1)**
`sse.configure()` defaults `[observability].debug` **ON** (`sse.py:370-376`;
`mios.toml:2906`; `server.py:355`); when on, `_sse_reasoning` returns a **content**
chunk and `_sse_status` sets `_content` instead of `_reason` (`sse.py:93-94,
197-201`). That is the exact mechanism behind the scaffold blob + triple-restate
in the transcript. The clean path already exists (debug OFF → everything on
`reasoning_content`); the default posture overrides it. **Fix:** retire
content-inlining as the visibility mechanism. Everything on the reasoning channel
*by default*; `debug` gates only *how much* trace mirrors to content-only
surfaces (per FV-F), never promotes reasoning into `content` on a
reasoning-aware surface.

**FV-F — "ALL surfaces" is unreachable for strict clients via the reasoning field alone. (P1)**
OWUI (`reasoning_content`) and Hermes (`reasoning`) render the trace; Zen/strict
OpenAI clients ignore both and show only `content` (`sse.py:56-60`). So "put
everything on the reasoning channel" makes it invisible on strict surfaces —
which violates the mandate in the other direction. **Fix (from the companion
doc, Moves A/B):** per-surface capability negotiation via an
`X-MiOS-Surface`/`reasoning_ok` hint the OWUI pipe sets — reasoning-capable →
typed channels; strict → an opt-in **folded inline** trace, where **MiOS owns the
replay history and persists/replays only the clean final `content`** (so inline
display never busts the KV cache). Default clean.

**The FV fix, unified:** one canonical typed-event schema —
`thinking | plan | tool_call | tool_result | source | content` — that *every
stage and every sub-agent hop emits into*, per-surface routed. The infra
(`_sse_reasoning`, `STATUS_AS_REASONING` re-streaming every phase, dual-field
emit, node emitters) already supports it; the work is (1) FV-A per-lane
`stream_thinking`, (2) FV-B channel tag, (3) FV-D stream-all-hops, (4) FV-E/F
retire global content-inline → per-surface routing. All flag-gated, degrade-open.

---

## 2. CHAT-QUALITY gaps (CQ) — instances of the same root

### CQ1 — Refine/plan scaffold leaks into the answer; answer restated 3×. (P1)
**Root cause (two bugs, streaming path, both amplified by `debug=ON`):**
- *Channel mis-routing.* `chat.py:1425-1426` forwards every refine token through
  `_sse_reasoning`, which `sse.py:93-94` collapses to `delta.content` under
  `_DEBUG_ENABLE`. The refine micro's raw completion — including its `reply`
  field, explicitly declared internal ("consumed by another agent, NOT shown to
  the user", `refine.py:205-206`) — streams into the persisted answer before any
  tool runs. A truthy `on_token` also disables the JSON grammar + `/no_think`
  (`refine.py:734-739`), so the micro *narrates markdown* (the `Refined
  Query/Intent/Intended Outcome/Reply` block) instead of compact JSON.
- *No de-dup across hops.* cwd is in every hop's `<env>` block, so refine (`reply`,
  `chat.py:1789→1803`), the executor/local-state answer (`native_loop.py:1061,
  1101-1102`), and the polish pass (`native_loop.py:856-865, 976`) each generate
  "the current directory is /", and each reaches `content` under debug.

**Fix (channel-route + de-dup — visibility preserved):** the refine pump and the
`_refine_reasoning` summary must ride `reasoning_content`/`mios_status`
**regardless of `_DEBUG_ENABLE`** (pin pre-answer hops to the reasoning channel;
`debug` only chooses content-mirroring for strict surfaces per FV-F). Enforce
exactly one generation in `content` per turn (extend the existing `_live_streamed`
guard at `native_loop.py:858` across refine-reply / raw-synthesis / polish).
Optional efficiency: for an `<env>`-answerable turn, let refine's `reply` be the
single answer and short-circuit executor+polish (3 model calls → 1), model-gated,
degrade-open. Non-streaming refine path already exhibits neither bug — this is
streaming-specific.

### CQ2 — Tool calls emitted as literal text; inconsistent; `launch_app` misroute. (P1)
**Root cause:** native `tool_calls` is primary, `mios_jsonsalvage` +
`_rescue_tool_calls` is a fallback that fires **only when the native array is
empty** (`secondary_loop.py:334-344`). There is **no grammar/constrained decoding
on any lane** (light llama.cpp can't even force `tool_choice`,
`endpoints.py:75-87`; heavy SGLang emits native calls only if launched with the
matching `--tool-call-parser`). The leak itself: the **final answer-shaping
completion is fired with NO `tools[]`** (`native_loop.py:780-782`), its raw
`delta.content` streamed verbatim (`805-810`), only `<think>` stripped
(`851-854`), polish skipped when live-streamed (`858`). With no schema offered,
any residual tool intent can only come out as prose — and nothing sanitizes that
path. Inconsistency: `_rescue_tool_calls` returns after the **first** fenced block
(`toolexec.py:277-278`) so multi-call narrations partly execute, partly get
stripped, partly leak; plus a files-domain **prefetch** fires `fs_search`
deterministically (`native_loop.py:748-772`), which is why "a real
`linux_file_search` ran" even as others leaked.

**`launch_app` misroute:** the file-search verbs are `hidden=true`/`rare`
(`mios.toml:3446-3473`) so they're dropped from the model surface
(`server.py:3956`) — **yet their model-facing names are advertised inside visible
verbs' descriptions** (`read_file`/`resolve_launch_command`/`everything_search`
name `linux_file_search`, e.g. `mios.toml:3971`). The model reads a capability it
cannot call and wraps it into the one live "run by name" verb it can see —
`launch_app` (`mios.toml:9084`, a duplicate of the `open_app` alias at `3157`)
→ `mios-launch: no resolution`. The rescue allowlist accepts off-surface names
(`toolexec.py:210-224`), so both the wrapped name and `launch_app` dispatch.

**Fix (native events, not "hide"):**
- **A (root, durable):** engine-level constrained tool-calling so a call *cannot*
  render as prose — SGLang `--tool-call-parser` + xgrammar; llama.cpp GBNF from
  the offered `tools[]`. **Give the final shaping completion `_pb` the same
  `tools[]`** so residual intent surfaces as a native `tool_call` event (executed
  + shown as a typed pill), not text. Gate on the `mios_endpoints` capability
  SSOT; degrade-open.
- **B (visibility guarantee):** streaming-aware salvage that **re-emits** a
  narrated call as `mios_status` + `reasoning_content` + Responses
  `function_call`/`function_call_output` (fully visible on every surface),
  diverts it off `content`, then executes it and feeds the result back. Reuses
  the OWUI-pipe pattern (companion doc Move C).
- **C (SSOT catalog repair):** surface a routed domain's declared verbs even when
  `hidden`, keying the Stage-2 filter on the canonical verb via `_resolve_verb_key`
  (`server.py:4028-4034`) so a files turn always carries a working
  `linux_file_search`; derive "see also" names from the live surface (stop
  advertising uncallable names); consolidate the duplicate `launch_app`; on
  `mios-launch` no-resolution, degrade via `tool_search` instead of dead-ending.

### CQ3 — Grounding failure: hallucinated listing + no `list_dir` verb. (P1)
**Root cause:** there is **no first-class directory-listing verb**. `linux_file_search`
is `mios-locate` — a substring locate over indexed paths, not a lister
(`query="."` matches every path with a `.` → the mingw `.a` libs the operator
saw; `query=""` → "missing `<query>`"). The only thing that can list a directory
is `read_file`/`text_view` (it `os.walk`s a dir, `mios-text-edit:219-241`) — but
it's capped at depth 2 / 500 entries, is framed as "read a file," and is
**structurally excluded** from auto-grounding because it has a required `path`
arg the enricher won't infer (`server.py:4734-4745`). cwd is injected as a
*string* in the `<env>` block (`grounding.py:466,508-511` ← `mios:699`) but **no
directory snapshot**, and the local-state CORE verb set
(`list_windows/process_list/container_status/system_status/mios_apps`,
`server.py:4685-4701`) contains no lister — so no "GROUND on real output" block is
produced (`server.py:4769`) and the turn falls through to the model's parametric
prior (the generic FHS table). ReAct/act-first discipline exists for
identity/location/web/state but **not for filesystem contents**; `force_tool →
tool_choice=required` exists but is a manual OWUI toggle (`chat.py:1193-1198`),
not auto-engaged by query type. The `fs_search` description
(`mios.toml:3469`) frames it as *the* "find files on Linux" tool and never says
it's a substring matcher that can't enumerate a directory.

**Fix (SSOT + model-driven):**
1. **Add a first-class `list_dir` verb** to `[verbs.*]` — `model_name =
   "list_directory"`, backed by the existing `os.walk` lister with a new
   `--depth 1` immediate-children mode for true `ls` semantics, `path` **defaulting
   to cwd** (so "what's here" needs no arg-inference), accurate `desc`, and
   `examples`. The catalog auto-projects to planner prose + OpenAI/MCP tool
   schemas, so the model self-selects it — no keyword gate.
2. **Ground cwd deterministically:** fire `list_dir(path=cwd)` in
   `_read_tool_enrich` when the forwarded `cwd` is present (keyed off the SSOT env
   value, model-driven via a refine `state_scope`/filesystem signal like the
   existing `inventory_filter`), so the "NEVER invent system state" discipline
   auto-covers directory questions. Already flag-gated
   (`READ_TOOL_ENRICH_ENABLED`), degrade-open when cwd absent.
3. **Correct the misleading SSOT descriptions** (`fs_search` = substring locate,
   "does NOT list a directory — use list_dir"; promote/redirect `read_file`'s
   dir-listing note).

### CQ4 — Reflexion doom-loop: no convergence, no cutoff, re-proposes the same call. (P1)
**Root cause:** the `@`/native path
(`_respond_native_loop_direct → _v1_secondary_tool_loop`) has guards that all miss
this failure shape:
- *Max-iter exists but is loose + time-blind.* `SECONDARY_TOOL_MAX_ITERS=15`
  (`secondary_loop.py:300`), no wall-clock budget — only the 300 s httpx timeout
  (`native_loop.py:124`). The user Ctrl-C'd at ~1 min, before 15 heavy completions
  finished.
- *Repeat detection exists but is exact-match + evadable.* `_tool_call_sig`
  (`secondary_loop.py:44-60`) breaks only when **every** call in a round is
  already-seen (`386-389`); the observed calls each varied one token
  (`"."`→`""`→`launch_app mios-locate`→`launch_app linux_file_search`) so the
  guard never tripped. A *successful-but-useless* result (locate returning
  garbage) is invisible to every guard.
- *Escalation is keyed on the wrong branch.* The bounded replan +
  `_daemon_diagnose` (the only real escalation) lives inside the `if not tcs:`
  give-up branch (`secondary_loop.py:345-385`); the model kept emitting (varied)
  tool_calls, so it never entered → never escalated. No "N consecutive failures →
  stop/handoff."
- *Reflexion here is action-free prose.* The native path appends a free-text
  "SYSTEM REFLEXION" user message every failed round, unbounded
  (`secondary_loop.py:402-408`), streamed as the visible essays (`329-330`). The
  **structured** `reflect_on_step_failure` — which returns a real `{tool,args}`
  correction bounded to one turn (`reflect.py:255-391`) — is wired **only** into
  the DAG path (`dag_exec.py:769`), never the native/`@` loop. Nothing blacklists
  a call that already hard-errored; `tools[]` is rebuilt identically each round
  (`native_loop.py:431`).

**Fix (SSOT budgets + structural signatures — no English gates):**
- **SSOT the budgets:** `SECONDARY_TOOL_MAX_ITERS` and `SECONDARY_REPLAN_MAX` are
  code/env literals with no `mios.toml` key (`server.py:835, 3314`); `reflexion_enable`
  reads a non-existent `[agent]` section (`secondary_loop.py:265`) so it always
  falls back to `true`; doc/code drift (`mios.toml:2264` says replan=1, code=5).
  Give them a real `[agent_pipe]` SSOT home.
- **Add structured no-progress + escalation:** normalized progress signature
  (tool-name + normalized args, or a hash ignoring trivial arg variation) → break
  on repeated tool-name or repeated `tool_execution_failed` signature beyond an
  SSOT `no_progress_window`; a per-turn **failed-`(tool,args)` blacklist** so an
  identical hard-error can't re-run; an SSOT `max_consecutive_failures` that fires
  escalation off the *failure signal itself*, not the give-up branch; an SSOT
  `wall_clock_budget_s`.
- **Make reflexion emit-or-terminate:** wire the native path to the structured
  `reflect_on_step_failure` (returns a different action or terminates), kept
  **internal** (reasoning channel), not streamed as an essay.

---

## 3. Upstream native patterns (2025–2026, cited) → MiOS mapping

| Gap | Native upstream mechanism | Source | MiOS move |
|---|---|---|---|
| FV / CQ1 | Typed reasoning channel, never prose-in-answer: Anthropic `thinking` vs `text` blocks; OpenAI Responses `reasoning` items vs `output_text`; Gemini `thought` parts; vLLM/SGLang `--reasoning-parser` splitting `reasoning_content` from `content` at the server | docs.claude.com/en/docs/build-with-claude/extended-thinking · developers.openai.com/api/docs/guides/reasoning · ai.google.dev/gemini-api/docs/thinking · docs.sglang.io/advanced_features/separate_reasoning | Refine/plan = structured object consumed internally; set `--reasoning-parser` on the heavy lane; Hermes forwards only `content` |
| FV / CQ1 | Planner–executor: plan is a typed object in state, not transcript prose (LangGraph plan-and-execute) | langchain.com/blog/planning-agents | Refine returns a plan object; only the final node returns user text → kills the restate |
| CQ2 | Constrained decoding guarantees well-formed calls: vLLM `--enable-auto-tool-choice --tool-call-parser hermes` + `guided_json`/xgrammar; SGLang `--tool-call-parser` + structural tags; llama.cpp GBNF `from_json_schema` | docs.vllm.ai/en/stable/features/tool_calling · docs.sglang.ai/advanced_features/function_calling · github.com/ggml-org/llama.cpp/blob/master/grammars/README.md · arxiv.org/abs/2411.15100 (xgrammar) | Launch engines with the model-correct `--tool-call-parser`; GBNF on light lanes; never accept a fenced block as a call |
| CQ3 | Act-before-answer: ReAct observe-before-assert; `tool_choice:"required"`/`any`/named forces the call; env context up-front | arxiv.org/abs/2210.03629 · docs.claude.com/en/docs/agents-and-tools/tool-use/implement-tool-use · anthropic.com/research/building-effective-agents | `tool_choice:"required"` on model-classified state-query turns; `list_dir` + cwd snapshot up-front |
| CQ4 | Bounded loops: Reflexion is `max_trials`-bounded by design; LangGraph `recursion_limit`; Agents SDK `max_turns` + `error_handlers`; tool errors as structured `is_error` observations | arxiv.org/abs/2303.11366 · docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT · openai.github.io/openai-agents-python/running_agents · anthropic.com/engineering/writing-tools-for-agents | SSOT iteration/wall-clock budgets + no-progress hash + failed-call blacklist + escalate after N; reflexion must change the action or stop |

---

## 4. Priority, sequencing, and where it can be done

**Wave 1 — the channel spine (unblocks the mandate + CQ1/CQ2 visibility).**
FV-E/FV-F (retire content-inline → per-surface routing) + FV-A (`stream_thinking`
per-lane) + FV-B (channel tag) + CQ1 (refine → reasoning channel, one answer in
content). One coherent "typed-event schema, every hop emits into it" change.
*Mostly offline-authorable; needs the live AI plane to validate streaming.*

**Wave 2 — tool-call integrity (CQ2).** Engine `--tool-call-parser` +
constrained decoding; give `_pb` the `tools[]`; streaming-aware re-emit; SSOT
catalog repair (surface routed-domain verbs, consolidate `launch_app`, stop
advertising uncallable names). *Engine-flag parts need the live lanes; catalog +
salvage parts are offline.*

**Wave 3 — grounding (CQ3).** Add `list_dir` verb (+`--depth 1` lister mode),
wire it into `_read_tool_enrich` for cwd, fix misleading descriptions.
*Offline-authorable; validate live.*

**Wave 4 — loop control (CQ4).** SSOT the budgets, add no-progress + failed-call
blacklist + `max_consecutive_failures` + wall-clock budget, wire the structured
reflector into the native path. *Offline-authorable; validate live.*

All waves are flag-gated and byte-identical when their flag is off. None require
a schema/data migration. The recurring root across CQ1/CQ2/FV is a single
architectural choice — **which channel carries which activity** — so Wave 1 is
the highest-leverage: it is simultaneously the operator's full-visibility mandate
and the fix for the ugliest transcript defects.
