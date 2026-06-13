<!-- AI-hint: Strategic roadmap documenting the transition to a full AIOS architecture, detailing specific implementation paths for kernel scheduling, tiered memory management, and context engineering to achieve high-throughput agentic operations. -->
# MiOS — Full AIOS Control Roadmap (research-grounded, 2026-06-11)

Synthesis of four deep research sweeps of the **open-source AIOS landscape** (June 2026),
mapped onto MiOS's current pipeline. Each pillar lists the field's battle-tested pattern,
then the concrete MiOS move. Sources are inline. MiOS is already ~80% of the AIOS
reference; this is the prioritized plan for the remaining "full AIOS control."

Shipped on the way here (2026-06-11): the refine classifier now discerns
**internal / external / both**, splits "both" into a concurrent local+web `multi_task`
DAG, and **executes each facet against its own source** (local facet → `system_status`/
`mios_apps` via `_read_tool_enrich`; web facet → `web_research`) and synthesizes —
verified end-to-end (local facet reads the real RTX 4090).

---

## The four pillars (key findings)

### 1. Kernel + scheduling
- Rutgers **AIOS** (`agiresearch/AIOS`, kernel v0.3.0 2026-01-22) is the canonical LLM-OS:
  agent scheduler, context manager, memory/storage/tool/access managers, Cerebrum SDK.
  Reports up to **2.1× throughput** — but shipped scheduling is **only FIFO + Round-Robin**,
  isolation is **logical (privilege-group hashmap)**, and the context switch is a plain
  KV-cache snapshot (the paper's beam-search framing is NOT in the code).
- The strong *production* scheduler is **Autellix** — program-level MLFQ over vLLM,
  **4–15× throughput** by scheduling whole agent programs, not individual LLM requests.
- AIOS's own data: scheduling **hurts** trivial turns on small models — gate it to contention.

### 2. Memory + context
- **MemGPT/Letta**: tiered virtual memory (core/in-context ↔ archival/recall on disk),
  the LLM **self-pages via tool calls** (`memory_insert`/`replace`/`rethink`); productized
  on **Postgres + pgvector**; **sleep-time agents** consolidate memory off the latency path;
  block limit is now 100k chars (not 2k).
- **Anthropic context engineering**: **compaction** (summarize+reinit near full window) +
  **context-editing** (drop stale tool results, keep last N) → +39% agentic search, 84%
  fewer tokens over 100 turns. **Sub-agent context isolation** + just-in-time retrieval.
- **Serving layer**: vLLM PagedAttention + APC; **SGLang RadixAttention + HiCache**
  (L1 GPU→L2 RAM→L3 disk, local file backend); **llama.cpp `/slots` save/restore** —
  with the **`--swa-full` guard required for Gemma/Qwen SWA models** or restored KV is wrong.
- Loop patterns: **ReAct** (reason+act+observe) + **Reflexion** (verbal self-reflection on
  failure into an episodic buffer, retry). Recall ranking: recency·importance·relevance.

### 3. Multi-agent orchestration
- **Magentic-One dual-ledger**: a Task Ledger (Facts/Guesses/Plan) + Progress Ledger
  (per-agent assignment + "complete?"/"progress?"), with re-plan triggered at **stall > 2**.
- **LangGraph**: state graph + **reducers** (`operator.add` accumulates concurrent writes,
  never overwrite) + **checkpoint per super-step** (durability, HITL, time-travel) + `Send()`
  dynamic map-reduce. **Supervisor vs swarm** routing (94% vs 91% accuracy, swarm ~40% faster).
- **OpenHands `AgentDelegateAction`**: parent spawns named sub-agents that run in parallel
  threads and return **one consolidated observation** (errors per sub-agent).
- **The single biggest reliability win for mixed tasks**: make an action node **depend on**
  a research node's typed output (findings → action), not run as independent siblings
  (Magentic-One WebSurfer→Coder; MS Agent-Framework explicit graphs over implicit GroupChat).
- Typed/structured handoffs (CrewAI Pydantic, MetaGPT SOP artifacts) stop the find-out→do
  boundary degrading into hallucinated free text. Loop guards (stall/handoff caps) mandatory.

### 4. Computer-use / OS control
- Field convergence: **typed-API/verb/hotkey first → a11y-tree click → vision-grounded last**
  (UltraCUA +22% OSWorld & 11% faster; Anthropic 150K→2K tokens by pushing work to code).
- a11y-first/vision-fallback (UFO² recovers 10–25% of UIA-only failures); **Linux AT-SPI is
  materially weaker than Windows UIA** → vision fallback matters more on the flatpak side.
- Local single-GPU grounding is viable: **Holo1.5-7B** (ScreenSpot-Pro 57.94) / **UI-TARS-1.5-7B**
  (Apache-2.0, vLLM/SGLang). **Coordinate scaling is the #1 "click missed" bug** — Qwen2.5-VL
  emits absolute pixels, **Qwen3-VL reverted to normalized 0-1000**; HiDPI rescale required.
- Safety = sandbox + least-privilege + **HITL on consequential actions** + injection classifier
  (Meta "Rule of Two": ≤2 of {untrusted input, sensitive access, state-change} without a gate).
- Reliability = **verify-after-action** (before/after screenshot or a11y diff) + retry +
  wait-for-stable-element + re-ground (bounded ~10 iters).

---

## Prioritized roadmap for MiOS

Mapped to MiOS's substrate (refine→route→decompose→execute→synthesize; llama-swap +
SGLang lanes; pgvector + knowledge recall; MCP surface; typed OS-control verbs; the
`dispatch_mios_verb` chokepoint; the CPU-pinned daemon-agent).

- **P0 — Program-level scheduler with preemption (gated to contention).** Adopt
  Autellix-style MLFQ over the whole agent task/DAG so a long swarm doesn't starve quick
  council turns; demand-aware LRU eviction for victims. GATE to contention (AIOS data:
  it hurts trivial small-model turns). Closes the standing "true priority queue / preemption" gap.
- **P1 — KV slot-save/restore as agent virtual memory.** Map each conversation to a stable
  llama.cpp slot file; restore-before / save-after each turn; **add `--swa-full` for the
  Gemma/Qwen lanes** (or restored KV is corrupt). The concrete local AIOS context manager.
- **P2 — Self-editing tiered memory.** Promote the per-conversation scratchpad to labeled,
  size-bounded **memory blocks** the agent edits via verbs (MemGPT); add **compaction +
  stale-tool-result clearing**; wire **memory-pressure eviction** (warn→flush, LRU-K >80%)
  to pgvector archival. Closes the P2.1 eviction gap.
- **P3 — Dual-ledger + typed-output synthesis + action→research edges.** Add a per-conversation
  Fact Ledger + Progress Ledger to the DAG path; make synthesis a **reducer over typed node
  outputs** (verb-output schema for action nodes, `{claim,source}` for research) instead of a
  free-text merge (kills fabrication upstream of the polish figure-guard); for a "both" task,
  let an action facet **depend on** a research facet's output when findings must drive the action.
- **P4 — ReAct+Reflexion durable loop.** Formalize each turn as call→observe→reason until no
  tool calls, bounded by max_iter/max_retry, with a Reflexion step on tool error; **checkpoint
  per super-step** (keyed by `chat_id`) so a crash resumes, not restarts. The concrete fix for
  the recurring narrate-instead-of-call failure.
- **P5 — Per-agent access control + HITL at the MCP chokepoint.** Implement the AIOS
  privilege-group model (agent-ID → group + audit log) at `dispatch_mios_verb`; classify verbs
  routine/privileged/destructive; **destructive → HITL confirm**. Enforces the per-child
  tool-surface goal; safely re-opens the security-blocked hermes-direct launch path.
- **P6 — Computer-use action hierarchy + reliability.** Encode verb/MCP → a11y-tree (Windows
  UIA; AT-SPI best-effort) → vision (`pc_click`) as an explicit router, not a model hope; **fix
  the qwen3-vl coordinate scaling** (pin the convention, handle HiDPI); add **verify-after-action**
  + wait-for-stable + bounded retry. Consider Holo1.5-7B / UI-TARS-1.5-7B on the heavy lane.
- **P7 — KV hierarchy + sleep-time consolidation.** Enable **SGLang HiCache** (local file
  backend) on the heavy lane so the 17K-token tool-surface prefix reuses + idle KV spills
  GPU→RAM→disk; give the **daemon-agent a Letta sleep-time job** (consolidate knowledge rows +
  shared memory blocks off the latency path). Upgrade recall to recency·importance·relevance.

### What NOT to copy
- MetaGPT's rigid role assembly-line (trades concurrency for determinism) — take its
  typed-artifact-between-stages idea (P3), not the fixed role sequence.
- The paper's beam-search context-switch framing — cite/build the real KV-cache snapshot.
- Don't size MiOS expectations to vendor "superhuman OSWorld ~72%" claims (self-reported);
  independent peer-reviewed agents are ~27–35%. Architecture choices exist *because* raw
  reliability is low — that is the load-bearing lesson for local-first AIOS control.
