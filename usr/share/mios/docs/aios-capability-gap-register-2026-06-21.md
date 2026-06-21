<!-- AI-hint: The authoritative AIOS capability GAP REGISTER for MiOS (2026-06-21), produced by a 67-agent code-grounded + web-verified + adversarially-verified audit across 10 AIOS dimensions (kernel/scheduler, memory/storage, context, orchestration/tools, security/access, self-improve, benchmarking, substrate/deploy, perception/multimodal, standards/interop). 55 gaps surfaced -> 53 confirmed -> deduped to ~12 distinct real gaps in 4 themes: kernel hot-path enforcement, SLO/workflow-aware scheduling, memory-lifecycle wiring, and resource-governance+lifecycle. Each gap is file:line code-grounded with offline-vs-VM closure + a recommended WS task. Companion to aios-engineering-blueprint.md (the current-state map) and ws-remaining-vm-completion-checklist.md.
     AI-related: ../doc/mios/concepts/aios-engineering-blueprint.md, ./ws-remaining-vm-completion-checklist.md, ../mios.toml, ../../../lib/mios/agent-pipe/server.py -->
# MiOS — AIOS Capability Gap Register (2026-06-21)

> Produced by a 67-agent multi-agent audit: 10 AIOS dimensions each web-verified
> against the 2026 state-of-the-art **and** code-grounded against the live MiOS
> tree, then **adversarially verified** (each claimed gap re-checked by a skeptic
> prompted to refute it). 55 gaps surfaced → **53 confirmed, 2 refuted** (the two
> refutations were KV/RadixAttention claims already satisfied by the SGLang
> `hierarchical_cache` + vLLM `prefix_caching` lanes). After de-duplicating
> overlapping findings across dimensions, **~12 distinct real gaps** remain, in
> **4 themes**.

## Executive summary

MiOS realizes the full **Rutgers AIOS kernel taxonomy** (Agent Scheduler /
Context / Memory / Tool / Storage / Access managers) as concrete, unit-tested
modules on a genuinely immutable, GPU-native, fully-local OS. Estimated **~80%
of a full AIOS** (an *estimate*, not a measured score — prior audits put it
75–80%). The remaining gaps are **not missing topology** — the manager seams and
pure cores all exist — but **central-path wiring and lifecycle holes**: for the
highest-value paths the kernel does not drive execution, the scheduler does not
preempt or shed running work, a memory-tiering feedback loop is dead on the live
backend, and there is no home for **resource governance** (cost/energy/VRAM
arbitration) or **agent lifecycle** (prompt versioning / workflow recovery /
runtime audit). Security is strong: **8/10 OWASP-Agentic controls wired-live, 2
with enforcement-wiring caveats** (ASI06 inbound-enforce, ASI10
`principal_mode=enforce`).

---

## Theme 1 — Kernel & scheduler hot-path enforcement (the structural debt)

| Component | Status | Evidence | What full AIOS needs | Effort | Offline/VM |
|---|---|---|---|---|---|
| Kernel Stage-2 dispatch is not the live path: 4/5 modes raise `NotImplementedError` | partial | `server.py:19255-19261` `_kernel_stage2b` raises for chat/dispatch/multi_task/agent; only `dag`→`execute_dag` is real. `KERNEL_ROUTE` default-off; the only live kernel touch is a shadow-route log (`server.py:26724-26729`) that never alters control flow. Grep: zero `dispatcher.run()` invocations in 27k lines. | The Scheduler must dispatch ALL agent syscalls through the kernel facade so scheduling/context/access policy is enforced at ONE chokepoint. Today the kernel-space vs user-space boundary is architectural-only for 4/5 modes. | L | vm |
| RR preemption wired only to a no-tools fan-out sliver, not foreground or tool-loop turns | wired_but_weak | `_rr_eligible` (`server.py:3405-3414`) requires `not body.get("tools")` + a llama.cpp `/slots` lane + `RR_ENABLE` (default-off). `_rr_run` invoked at exactly one site (`server.py:4364`, fan-out dispatch). Foreground `chat_completions`→`_respond_native_loop_direct`→`_v1_secondary_tool_loop`/`_ollama_secondary_tool_loop` contain NO `_rr_run`. | Real RR time-slices ALL concurrent agent threads — including the interactive turn and the multi-step tool loop. MiOS's two highest-value paths can never be preempted; the priority gate still only re-orders ADMISSION, not running work. | L | vm |

## Theme 2 — SLO / workflow-aware scheduling (the 2026 frontier)

| Component | Status | Evidence | What full AIOS needs | Effort | Offline/VM |
|---|---|---|---|---|---|
| Admission is capacity-only (VRAM/host-load), not deadline/SLO-aware; **fails OPEN** under contention | partial | `_admit` (`server.py:1554-1616`) gates only `_over_global_ceiling()` + VRAM fit; every branch admits or degrades-open. `priority` only scales backoff sleep; no `deadline`/SLO request class, no least-deadline-first, no shed. `_budget_admit` (`server.py:1179-1226`) rejects on rolling token/rate exhaustion (a tripwire) but **also degrades-open** (`server.py:1224-1226`) — a probe failure during a storm silently disables backpressure. | SLO-class admission (SCORPIO/Andes/QLM): per-request deadline/SLO class, least-deadline-first, REJECT/shed best-effort under contention. And backpressure must **fail-closed**, not open. | M | mixed |
| No workflow-atomic / agent-graph scheduling: the schedulable unit is one dispatch, not the whole workflow | missing | Per-dispatch primitives only: `PriorityGate.acquire(priority)` per call, `_admit` per `(ep,model,lane)`, `_PREEMPT` keyed on conv. `_pick` orders by `(priority,-seq)`+aging with no DAG awareness, no session-affinity batching, no KV co-location. `mios_kvfork` reuse is never a scheduler input. | SAGA/Cortex make the agent WORKFLOW the schedulable entity: Agent Execution Graphs predict cross-tool-call KV reuse for session-affinity batching + a task-completion-time fairness metric. | L | mixed |
| Native-engine priority pass-through absent (priority shaping stops at the agent-pipe) | wired_but_weak | `mios_batch.is_native_batch`/`batch_key`/`CoalesceWindow` are imported (`server.py:118`) but never invoked — the documented hold-and-flush chokepoint does not exist; `BATCH_ENABLE` default-off. `PriorityGate` shaping never reaches the continuous batcher. | Expose request-class/priority HINTS into the native engine's own scheduler (e.g. vLLM request-priority) so cross-engine priority survives past the GPU-lane boundary. (Coalescing-bypass of self-batching engines is itself a correct design choice.) | M | vm |

## Theme 3 — Memory lifecycle wiring (strong plane, dead feedback loop)

| Component | Status | Evidence | What full AIOS needs | Effort | Offline/VM |
|---|---|---|---|---|---|
| Tiering feedback loop **dead on the live pgvector backend** — `access_count`/`recall_hits`/`last_access`/`tier='hot'` never bumped on recall | wired_but_weak | The page-in promote is a raw SurrealQL `UPDATE` via `_db_post` (`server.py:11640-11647`). Under `_PG_PRIMARY`, `_db_post` returns `None` for any `UPDATE` (`server.py:2100-2103`) and never executes; the call supplies no `pg_sql` so the `_db_read`/`_db_update` PG paths (`server.py:2126-2149`) can't catch it. **Class bug**: any raw `_db_post("UPDATE/DELETE …")` survivor is silently dead on pg — needs a tree-wide grep sweep, not a one-site fix. | Live importance/recency signals so K-LRU eviction (`mios_evict.py`), hot/cold promotion, and decay operate on real recall telemetry. | M | offline |
| Multi-tenant memory isolation: RLS policies exist but the app never `SET LOCAL`s the per-request owner | partial | `schema-init.sql` has `owner_user` columns + RLS policies, and `_recall_*` app-filter by `owner=_rls_owner()` (WS-5/#27), but no per-connection `SET LOCAL mios.owner_user` → the DB-level RLS policy is inert (app-filter is the only live isolation). | Bind a verified principal → `SET LOCAL` the RLS owner each request so DB-level RLS is the belt-and-suspenders behind the app filter (OWASP ASI08 multi-tenant). | M | mixed |
| Memory-poisoning **write-time validation** absent | missing | `_store_knowledge_task` (`server.py:11334`) writes recall-derived Q/A with no instruction/URL/code-pattern rejection. ASI08 is "single-user taint + audit," partial. | OWASP ASI08: VALIDATE extracted facts before write (reject embedded instructions/URLs/code-like entries); carry source/confidence + recency-wins invalidation (mark stale, don't delete). | M | offline |
| Core-tier memory not auto-loaded into context each turn (tool-pull only) | partial (design delta) | `agent_memory` (core) recall is tool-driven/off-by-default by the no-context-injection rule (blueprint:56; `server.py:11450`). Deliberate MiOS divergence, tracked not defect. | CoALA/Letta auto-load bounded, labeled, self-editable core blocks every turn. Closing it (if desired) = a bounded core block in the system-role `<env>` plane, never the user message. | M | offline |

## Theme 4 — Resource governance & agent lifecycle (the register's blind spot — added by the completeness critic)

| Component | Status | Evidence | What full AIOS needs | Effort | Offline/VM |
|---|---|---|---|---|---|
| Cost/energy accounting is token-rate only — no $-cost or energy/VRAM-hour dimension (CLASSic "C" is a stub) | missing | `_budget_admit` is a token-count rolling-window tripwire; `mios_quota` cost model is "default unlimited, remote adapters stubbed" (blueprint:131). Grep `energy\|kwh\|watt\|carbon\|cost_usd` → no matches. | On a local-GPU OS the **power envelope is the real constraint**: $-per-task + energy-per-token as first-class accounting/scheduling signals (CLASSic Cost axis). | M | offline |
| GPU/VRAM arbitration is admission-time fit-check only — no preemptive eviction / lane reclamation under pressure | missing | `_admit` checks VRAM co-load fit at admission, but nothing evicts a resident model or reclaims a lane once admitted. The operator's own MEMORY records VRAM co-fit as *the* live failure mode (granite CPU-spill, SGLang OOM). | A GPU memory manager that arbitrates/evicts across lanes under VRAM pressure — an AIOS Storage/Resource-manager capability. | L | vm |
| No agent/prompt/model versioning in the orchestrator — the ~12 hop prompts are unversioned | missing | Grep `prompt_version\|agent_version\|rollback` in `mios_selfimprove.py`/server.py prompt assembly → none. WS-A17 (#29) versions skill/recipe *packages*, but live refine/synth/polish/swarm/council/native-loop prompts have no stamp/A-B/rollback. | A versioning substrate is the **prerequisite** for the self-improve ACT half (WS-11) to safely roll an auto-edited prompt forward/back. | M | offline |
| Fault-tolerance is per-call degrade-open, not workflow recovery — no DAG checkpoint/resume | missing | 395 `circuit\|retry\|fallback\|degrade\|recover\|replay` hits, all per-request degrade-open or per-lane circuit-breaker. A swarm/DAG that dies mid-flight restarts from zero, not the last completed node. | Treat the workflow as a durable, **resumable** entity (checkpoint/resume) — pairs with Theme-2 workflow-atomic scheduling. | L | mixed |
| No runtime audit/compliance assertion framework (build-time only) | partial | Security-S is "build-time; no runtime assertion fw" (blueprint:135); ASI07 "audit captured; no real-time anomaly alert" (blueprint:108). `38-drift-checks.sh` is build-time. | Runtime policy assertion + tamper-evident audit + anomaly alerting for the multi-tenant store, not just a build gate. | M | mixed |

---

## Top priorities

1. **Kernel Stage-2 hot-path rewire (WS-A11b/#15)** — until `dispatcher.run()` owns chat/dispatch/multi_task/agent, every scheduler policy is bolted on ad hoc instead of enforced at one syscall chokepoint.
2. **Revive the pgvector tiering feedback loop (WS-MEM-TIER)** — a dead `UPDATE` (`server.py:11640` vs `:2100-2103`) blinds K-LRU eviction on the live store; fully offline; sweep for the whole *class* of dead raw-`_db_post` writes.
3. **RR preemption on foreground + tool-loop (WS-A12b/#16)** — wire preemption to the two paths it currently excludes, where ~all of WS-A12's anti-HoL-blocking value lives.
4. **Deadline/SLO-class admission + fail-CLOSED shed (WS-SCHED-SLO)** — give the scheduler the ability to say "no" and protect a foreground turn during saturation.
5. **Resource governance: cost/energy accounting + VRAM arbitration (WS-RES-GOV)** — the power envelope is the binding constraint on a local-GPU OS; make $/energy/VRAM-hour first-class and add cross-lane VRAM eviction.
6. **Workflow-atomic scheduling + KV-reuse co-location (WS-SCHED-WF)** — make the DAG the schedulable unit; feed `mios_kvfork` predictions into `_pick`; add a task-completion-time fairness metric.
7. **Prompt/agent versioning substrate (WS-LIFECYCLE-VER)** — the prerequisite for safely closing the self-improve ACT loop.
8. **Write-time memory-poisoning validation (WS-MEM-VALIDATE)** + **multi-tenant RLS `SET LOCAL` (WS-5b)** — small, high-leverage OWASP ASI08 hardening.

## Offline-closable vs VM/hardware-gated

**Offline-authorable now** (pure-module + flag-gated): revive the pgvector tiering `UPDATE` + class-sweep; write-time fact-validation; deadline/SLO request-class + least-deadline-first + shed logic (+ fail-closed backpressure); workflow-atomic policy core + KV co-location heuristic; native-engine priority-hint construction; cost/energy accounting model; prompt-version stamping.

**VM / boot-loop-gated**: kernel Stage-2 hot-path rewire; RR preemption on foreground+tool-loop (`/slots` is engine-live); cross-lane VRAM eviction; batch chokepoint activation (coupled to the unbuilt remote core, WS-A16/#20).

**Mixed** (offline core, live activation): SLO admission; multi-tenant RLS `SET LOCAL`; workflow checkpoint/resume; runtime audit/anomaly framework.

## Recommended next WS tasks

- **WS-A11b** Route chat/dispatch/multi_task/agent through `dispatcher.run()` behind `KERNEL_ROUTE`; VM-verify parity with the inline cascade.
- **WS-MEM-TIER** Translate the page-in promote (`server.py:11640-11647`) to a parameterized PG `UPDATE`; sweep + fix all dead raw-`_db_post` UPDATE/DELETE survivors.
- **WS-A12b** Invoke `_rr_run`/snapshot-restore from `_respond_native_loop_direct` + the secondary tool loops.
- **WS-SCHED-SLO** SLO request classes + least-deadline-first in `PriorityGate._pick` + a shed/reject outcome in `_admit`; make backpressure fail-closed.
- **WS-RES-GOV** Cost/energy ledger ($/kWh/VRAM-hour) as a scheduling signal + cross-lane VRAM eviction under pressure.
- **WS-SCHED-WF** DAG as the schedulable entity; `mios_kvfork`-predicted co-location; task-completion-time fairness; workflow checkpoint/resume.
- **WS-LIFECYCLE-VER** Stamp + version + rollback the live hop prompts (prerequisite for self-improve ACT).
- **WS-MEM-VALIDATE** Reject instruction/URL/code-like facts before store; source/confidence + recency-wins invalidation.
- **WS-5b** `SET LOCAL mios.owner_user` from the verified principal on every agent-plane query.
- **WS-AUDIT-RT** Runtime policy-assertion + anomaly-alert framework over the audit stream.

## Corrections folded in from the completeness critic

- Down-graded **"8/10 OWASP wired-live"** → "8/10 wired-live, 2 with enforcement-wiring caveats" (ASI06/ASI10); ASI01 has no ML intent-divergence detector.
- The **"~80% AIOS"** figure is an *estimate*, not a measured score.
- The dead-`UPDATE` is a **class bug** (sweep, don't fix one site).
- Merged the batch row + "native-engine priority" priority into one finding.
- Multi-tenant RLS counted once (it appears in Theme 3, the priorities, and ASI08 — one gap).

## Sources

AIOS kernel taxonomy https://arxiv.org/abs/2403.16971 · SCORPIO SLO-serving https://arxiv.org/pdf/2505.23022 · FastSwitch https://arxiv.org/pdf/2411.18424 · SAGA https://arxiv.org/abs/2605.00528 · Cortex (Agent Execution Graphs) https://arxiv.org/html/2510.14126 · Letta/MemGPT https://www.letta.com/blog/memory-blocks · CoALA https://arxiv.org/pdf/2309.02427 · MIRIX https://arxiv.org/pdf/2507.07957 · memory consolidation https://hindsight.vectorize.io/blog/2026/05/21/agent-memory-consolidation · τ-bench `pass^k` https://arxiv.org/abs/2406.12045 · CLASSic https://arxiv.org/html/2511.14136v1 · OWASP Top-10 Agentic (ASI01–ASI10).

> **Verification note:** the specific SAGA/Cortex/SCORPIO performance figures
> (1.64× TCT, 99.2% SLO attainment, 1.31× Belady) were cited from dimension
> syntheses but not independently re-fetched this pass; the qualitative
> architectural distinctions (capacity-only vs SLO/deadline-aware admission;
> per-call vs workflow-atomic scheduling) are established on the MiOS code
> regardless. All MiOS file:line claims were adversarially re-checked against the
> tree (53/55 survived; 2 refuted).
