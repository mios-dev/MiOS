# MiOS AI Architecture — 2026-05-16 snapshot

Single source of truth for what's wired vs. what needs operator action.
Reflects operator directive 2026-05-16:

> query MiOS-Agent (OWUI default) >> small CPU model refines via
> template >> sends refined to MiOS-Hermes >> Hermes loops + tools
> >> delegates to CPU when needed >> uses opencoder for opencoder
> tasks >> answer + report via MiOS-Agent chat

## Live chain (this commit)

```
operator types in OWUI
      │
      ▼
  /api/chat/completions   (OWUI sets model="MiOS-Agent")
      │
      ▼
  prefilter :8641         (mios-delegation-prefilter.service)
      │  ├─ rewrites model "MiOS-Agent" → "hermes-agent"
      │  ├─ [ENABLED] refine via mios-sys-agent (qwen3.5:2b GPU)
      │  │     - applies reasoning template silently
      │  │     - rewrites user message to INTENT/CONSTRAINTS/MIOS
      │  │       CONTEXT/PLAN handoff
      │  └─ forces delegate_task on fan-outable prompts
      │
      ▼
  hermes :8642            (hermes-agent.service, qwen3-coder:30b GPU)
      │  ├─ skills: mios-environment, windows-control, pc-control,
      │  │           parallel-fanout, self-improvement, ...
      │  ├─ tools: terminal, file, web, delegation, skills, memory,
      │  │           todo, session_search, code_execution, browser,
      │  │           discord, cronjob, clarify
      │  ├─ delegate_task → MiOS-Delegate (qwen3:1.7b children)
      │  └─ delegate_task acp_command=opencode → MiOS-OpenCoder
      │
      ▼
  Ollama :11434           (raw inference)
      │  models resident:
      │    qwen3-coder:30b           17 GB GPU      hermes main
      │    mios-sys-agent (qwen3.5:2b)  4 GB GPU    refinement
      │    qwen3:0.6b-cpu             600 MB CPU    micro daemons
      │
      ▼
  response streams back through prefilter to OWUI
```

## Background daemons (READ-only -- micro-LLM for status, never launch)

| daemon | role | model |
|---|---|---|
| mios-log-watcher | classify journal events | qwen3:0.6b-cpu |
| mios-cron-director | gate cron rules on system state | qwen3:0.6b-cpu |
| mios-agent-nudger | detect refusal patterns in hermes output | qwen3:0.6b-cpu |
| mios-micro-llm | CLI wrapper for direct classification | qwen3:0.6b-cpu |

Operator clarification 2026-05-16: "MiOS-Hermes launches and operates
things themselves -- just the micro-llms read logs and files on
pass/fail". Daemons stay observation-only; never trigger actions.

## Pending operator decisions (model pulls / heavy work)

### A. Larger Gemma 4 for hermes (operator-suggested)

Current: `qwen3-coder:30b` Q4_K_M, ~17 GB VRAM on a 20.5 GB GPU.
Operator-observed: spills out of VRAM every turn (only 3.5 GB
headroom; mios-sys-agent at 4 GB doesn't co-resident).

Gemma 4 advantages operator cited:
- Extended context window (Gemma typically 128 K, Qwen3 32 K)
- Compression efficiencies

Candidates to evaluate (need pull):
- `gemma4:e4b` (already baked, 8.9 GB) -- TINY for the executor
  role; was evaluated for delegate but not hermes
- `gemma3:12b` or `gemma3:27b` if released as Gemma 4 in operator's
  terminology -- need to verify exact tag

Operator action required:
```
ollama pull gemma4:<tag>           # bandwidth-heavy
ollama show gemma4:<tag>           # confirm context_window
# Then ship a Modelfile that builds hermes-gemma + swap config:
#   model:
#     provider: custom:local-ollama
#     default: gemma4:<tag>
```

### B. VRAM strategy

20.5 GB GPU, current resident:
- qwen3-coder:30b   17 GB   (hermes)
- mios-sys-agent     4 GB   (refinement)

Total: 21 GB > 20.5 GB → mios-sys-agent forces partial qwen3-coder
eviction every turn → 5-10s of reload time per chat.

Options:
1. **Smaller hermes model** (Gemma 12 B / Qwen 14 B ≈ 8-9 GB) →
   fits alongside sys-agent comfortably with headroom for KV cache
2. **CPU-pin sys-agent** → frees the 4 GB but refinement becomes
   30-60s (operator already vetoed this trade)
3. **Bigger GPU** → operator hardware change
4. **Status quo with eviction** → slow first-turn after refinement,
   fast subsequent

Recommended: when operator pulls the gemma evaluation candidate,
test option 1.

### C. OpenCoder native delegation

opencode is already on the toolset list (platform_toolsets.
api_server includes "skills" + "delegation"). hermes can call:
```
delegate_task(tasks=[{
  goal: "rename + restructure these 12 files",
  acp_command: "opencode"
}])
```

OpenCoder uses ONLY offline models (operator-confirmed):
qwen3-coder:30b or similar via the local Ollama. Its strengths:
- File-system navigation
- Multi-file edits
- PC-control task chains
- Long-running coding work

Pending: a skill / SOUL rule that tells hermes WHEN to prefer
opencode delegation. Currently hermes makes that call ad-hoc; could
be more explicit:
- File-system heavy tasks (move/rename/refactor >3 files)
- PC-control loops (window manipulation chains)
- "Click around the UI to do X" workflows

Operator action required: confirm exact opencode model + add
SKILL.md guidance for the delegation heuristic. The OpenCoder lane
itself is already plumbed (per the prior session work on aux
lanes).

## Single-source-of-truth pointers

- mios.toml [ai] = model identities + endpoints
- mios.toml [ai.host_thresholds] = auto-pick by RAM (big/mid/small)
- mios.toml [ai.host_thresholds] = micro_model + sys_agent_model
- /usr/share/mios/ollama/Modelfiles/*.Modelfile = derived models
  (gpt-oss-tools:20b, qwen3:0.6b-cpu, mios-sys-agent, ...)
- /var/lib/mios/hermes/config.yaml = hermes runtime config (model,
  reasoning_effort, delegation, auxiliary lanes)
- /usr/share/mios/ai/hermes-soul.md = agent persona + truthfulness
- /usr/share/mios/ai/refusal-patterns.txt = shared patterns
- /usr/share/mios/hermes/skills/*/SKILL.md = capability index

## Open questions

1. Operator's "Gemma 4" -- which exact ollama tag? gemma3:12b?
   gemma3:27b? Something newer?
2. VRAM strategy -- accept current eviction or swap hermes to
   smaller model?
3. OpenCoder delegation heuristic -- explicit SKILL rule or trust
   hermes's judgement?
