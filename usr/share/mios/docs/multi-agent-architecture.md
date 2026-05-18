# MiOS multi-agent architecture — research + migration plan

> Operator directive 2026-05-18: "this all seems HARDCODED!!! HOW
> WOULD THIS MULTI_AGENTIC_REASONING WORK NATIVELY!??? RESEARCH!"

This doc captures the 2026 multi-agent patterns research and the
concrete migration plan to move MiOS off regex-driven post-processing
and onto native structured-handoff multi-agent reasoning.

## Current pipe (the thing being replaced)

```
user prompt
   → MiOS-Agent pipe (OWUI function)
        → CPU REFINE (qwen2.5-coder:7b)         ← text-out LABELS (INTENT/TOOLS/DELEGATE/PLAN)
        → Hermes orchestrator (qwen3.5:4b)      ← native tool_use, OpenAI tool_call schema
            → terminal / web_search / delegate_task / ...
        → CPU POLISH (qwen2.5-coder:7b)         ← text-in TEXT BLOB of streamed hermes output
   → operator-facing markdown
```

The break: hermes streams its raw OpenAI-format text deltas to the
pipe; the pipe wraps them in a `<details>` and re-prompts polish
with the SAME text blob. Polish can't see which tool_call ran, what
its arguments were, whether it succeeded, what its `tool_call_id`
was. So polish has to GUESS. Hence the regex post-processing layer
that grew up around it:

* `_THINK_TAG_RE` / `_DETAILS_BLOCK_RE` / `_LEADING_THOUGHT_RE` to
  strip model leaks from polish output
* `_KNOWN_AGENT_ERROR_RE` to detect "the agent claimed X failed"
  and substitute a generic rewrite
* `_OUTER_FENCE_RE` to unwrap `````markdown` ... ```` ` wrappers
* `_STRUCTURED_MD_RE` heuristic to skip polish on already-clean
  tabular output
* Polish system-prompt ban lists ("NEVER report 'launched' unless
  RAW OUTPUT contains tool_result success:true...")

Every one of these is downstream pollution from the text-blob
handoff. The model can't reason about structure it doesn't see.

## What 2026 multi-agent best-practice looks like

Three patterns dominate (see Sources at bottom):

### Planner → Executor → Critic → Aggregator
[Strands](https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/),
[Agno](https://docs.agno.com/reasoning/reasoning-agents),
[LangGraph supervisor pattern](https://www.digitalapplied.com/blog/agent-architecture-patterns-taxonomy-2026).
Each agent has a single responsibility; hand-off via JSON schema.

### Actor + Critic reflection loop
Reflexion / Self-Refine. Actor generates, critic scores against
explicit criteria + provides feedback, actor revises. No regex
post-processing — the critic is an LLM call over structured input.

### Structured tool_result handoff
[Anthropic tool_use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
+ [OpenAI Responses API](https://platform.openai.com). Every tool
invocation emits `{tool_call_id, name, arguments, output, success}`.
Downstream agents read fields directly. No text-mangling.

## The gap for MiOS

* Hermes ALREADY does native tool_use (the session JSON at
  `/var/lib/mios/hermes/sessions/session_*.json` has the structured
  records: `tool_calls: [{function:{name, arguments}, id}]` paired
  with `role: tool` messages containing `tool_call_id` + content +
  `success: true|false`).
* `delegate_task` ALREADY gives Hermes supervisor-worker fan-out.
* `skill_view` / `skill_manage` give the agent introspection +
  self-modification.

What's MISSING:

1. **Structured handoff from Hermes to the compose layer.** The
   pipe consumes Hermes's SSE text stream and loses every
   tool_call boundary. Polish operates on text → has to guess.
2. **No explicit Critic agent.** When something goes wrong, no
   structured "verdict + failed_steps" object — just the model's
   own self-flagellation in prose.
3. **Refine emits LABELS not JSON.** INTENT/TOOLS/DELEGATE/PLAN
   are text fields; downstream agents string-parse them.

## Migration plan (incremental)

### Phase 1 (this commit): structured Compose input
* Pipe reads the active Hermes session JSON at end-of-stream.
* Extracts `[{tool_call_id, tool_name, arguments, output, success}]`.
* Passes the LIST plus the user prompt to compose (was: polish) as
  a structured JSON blob in the system prompt.
* Compose system prompt rewritten to reason over structured input
  (no regex; "step 1 used `mios-find` and returned success=true
  with output `<...>`; step 2 ran `web_extract` which returned
  success=false with error `<...>`; therefore the final answer
  reports step 1 succeeded and step 2 did not run").
* The text-blob path stays as fallback if the session JSON is
  unavailable; the structured path takes precedence.

### Phase 2: Critic Agent
* After Compose drafts a final answer, Critic Agent (qwen3:1.7b on
  iGPU per micro-LLM directive) scores it against the structured
  tool history: does the answer's success/fail claims match each
  tool_result's `success` field? Are all planned steps accounted
  for?
* If verdict is "revise", Critic returns specific `failed_assertions:
  [...]`; Compose revises.
* Loop bounded at 2 iterations (compose, critique, revise, done).

### Phase 3: Refine emits JSON
* Refine prompt rewritten to output JSON conforming to a schema:
  `{intent: str, plan: [{tool: str, args: dict, success_criteria:
  str}], delegate: bool}`.
* Compose reads `plan[].success_criteria` to evaluate each
  tool_result against the operator's actual intent (not just
  exit-code success).
* This enables the Critic to give targeted feedback: "step 2's
  success_criteria was 'returns a URL'; tool_result was the
  search-only error -- step did not meet criteria".

### Phase 4: Drop regex post-processors
* `_KNOWN_AGENT_ERROR_RE`, `_DETAILS_BLOCK_RE`, the polish
  ban-list lines, `_STRUCTURED_MD_RE` — all become unnecessary
  because Compose reasons over structure, not text.
* `_strip_outer_md_fence` stays (it's a literal formatter fix,
  not behavioural).

## Phase 1 implementation note (shipped alongside this doc)

`mios_agent_pipe.py` Pipe class gains `_load_session_tool_history`
that finds the session JSON matching the current chat by
mtime-proximity. The compose call is gated: if structured input
loaded, use the new compose-from-structure prompt; otherwise fall
back to the legacy text-blob polish (so older sessions / failed
session loads degrade gracefully).

## Sources

- [Multi-Agent Orchestration: Pattern Language 2026 — Digital Applied](https://www.digitalapplied.com/blog/multi-agent-orchestration-patterns-producer-consumer)
- [Agent Architecture Patterns: 2026 Taxonomy Guide](https://www.digitalapplied.com/blog/agent-architecture-patterns-taxonomy-2026)
- [Multi-Agent System Patterns: A Unified Guide — mjgmario / Medium](https://medium.com/@mjgmario/multi-agent-system-patterns-a-unified-guide-to-designing-agentic-architectures-04bb31ab9c41)
- [Multi-Agent collaboration patterns with Strands Agents and Amazon Nova — AWS](https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/)
- [Hierarchical Planner AI Agent with Open-Source LLMs and Structured Multi-Agent Reasoning — MarkTechPost](https://www.marktechpost.com/2026/02/27/a-coding-implementation-to-build-a-hierarchical-planner-ai-agent-using-open-source-llms-with-tool-execution-and-structured-multi-agent-reasoning/)
- [Reasoning Agents — Agno docs](https://docs.agno.com/reasoning/reasoning-agents)
- [Tool use with Claude — Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Building Effective AI Agents — Anthropic](https://resources.anthropic.com/building-effective-ai-agents)
- [Anthropic introduces "dreaming," learning across sessions — VentureBeat](https://venturebeat.com/technology/anthropic-introduces-dreaming-a-system-that-lets-ai-agents-learn-from-their-own-mistakes)
- [AI Trends 2026: Test-Time Reasoning and the Rise of Reflective Agents — HuggingFace](https://huggingface.co/blog/aufklarer/ai-trends-2026-test-time-reasoning-reflective-agen)
- [Customize agent workflows with Strands Agents — AWS](https://aws.amazon.com/blogs/machine-learning/customize-agent-workflows-with-advanced-orchestration-techniques-using-strands-agents/)
- [LangGraph vs CrewAI vs AutoGen: Complete Multi-Agent Orchestration Guide for 2026](https://pockit.tools/blog/langgraph-crewai-autogen-multi-agent-orchestration-guide/)
