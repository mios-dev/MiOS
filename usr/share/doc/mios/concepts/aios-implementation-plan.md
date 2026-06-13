<!-- AI-hint: Roadmap for the Agentic-OS (AIOS) transition, mapping research survey requirements to MiOS's existing `agent-pipe` infrastructure and defining the technical path for offline-first, FOSS-compliant agentic features.
     AI-related: /etc/mios/..., /usr/lib/mios/agent-pipe/, /etc/mios/mios.toml, mios-computer-use, mios-sync-env, mios-os-control, mios-agent-pipe, mios-verb, mios-remember, mios-oscontrol-server -->
# AIOS / Agentic-OS Implementation Plan for MiOS

> Status: research plan (2026-06-04). Source: operator-supplied AIOS/AgentOS
> architecture survey ("Architectural Engineering of Agentic Operating Systems"
> + "Engineering a Unified Local Agentic Operating System"). This document maps
> that survey onto MiOS's *actual* state and sequences the genuinely-remaining
> work. Companion notes: `architecture.md`, `computer-use-federation.md`,
> `coderun-sandbox.md`, `OFFLINE-FIRST.md`.

Real implementation file referenced throughout:
`usr/lib/mios/agent-pipe/server.py` (the bespoke OpenAI-compat orchestrator —
*not* the AIOS/Cerebrum SDK; that divergence is deliberate).

---

## 0. Three reality checks (read before building)

**(A) ~60% of the survey is already shipped in MiOS.** This is mostly
*verify -> finish the long tail -> harden*, not greenfield. Verified live
2026-06-04 against `server.py`: MCP + A2A *consume* wired into the loop
(`_mcp_call_tool` :14084, `_a2a_send_message_to_peer` :14395), admission
controller (`_admit` :790), outcome-ranked tiered memory
(`_store_knowledge`/`_recall_knowledge`/`_blended` :7205/:7273/:7319), KV-cache
demand-paging on the llama.cpp iGPU lane (`_kv_paging` :2202), saturation
scheduler (`_execute_dag_saturated` :10297), dead-node circuit-breaker, global
host cap (`_GLOBAL_DISPATCH_SEM` :611), semantic firewall, passport ed25519
signing, coderun bwrap sandbox. The survey's "kernel services" picture is
largely MiOS *today*.

**(B) Do NOT vendor Wide-Moat / "Yambr" Open-Computer-Use.** The survey's whole
docker-compose stack (`ghcr.io/yambr/open-computer-use`, a patched OWUI image,
a host Docker-socket mount) violates two binding rules. Prior MiOS research
verdict stands: that repo is **Business Source License 1.1** (source-available,
*not* FOSS; Change Date 2029) and has **no offline path** (vision defaults to
GPT-4o, sub-agent to Claude/OpenRouter). It cannot be the core of a FOSS,
fully-offline distro, and docker-compose is not MiOS-shaped (MiOS =
podman-quadlet + systemd + `mios.toml` SSOT). We build `mios-computer-use` from
MiOS parts instead (WS-4).

**(C) Some specifics in the survey are fabricated or aspirational — don't code
to them.** "Qwen 3.6 35B" / "qwen3.6" do not exist (MiOS runs qwen3.5:4b,
gemma4:e4b, hermes); the survey's `system_audit.sh` greps for `qwen3.6` and
would always fail. **LAKE** (ML-in-kernel scheduling) and **ProbeLogits**
(logit-vector kernel security) are research-grade and ollama does not expose
logit tensors — treat as Phase-4 spikes, not deliverables. The magic numbers
(2.1x speedup, 98.7% token cut, 92% compaction, 65ms, 32MB KV cap) are
paper/illustrative targets, not contracts. The survey also describes MiOS
aspirationally as already "encapsulating AIOS/Cerebrum" — it does not; the
agent-pipe is bespoke by design.

> Every workstream's first task: re-verify current state against live
> `server.py` before building. Point-in-time audits drift.

---

## 1. Concept -> current state -> real delta

| Survey concept | MiOS state | Real remaining work |
|---|---|---|
| AIOS 6-manager kernel | PARTIAL->PRESENT (all six exist as fns) | finish scheduler + memory paging |
| Agent Scheduler (FIFO/RR/priority/SJF) | PARTIAL — `_admit` = priority *backoff*, not reorder | **WS-1: real priority queue** |
| Context Mgr / KV checkpoint·restore·fork | PARTIAL — `_kv_paging` real on iGPU llama.cpp; no `fork` | scale-up (vLLM+LMCache), `kv_fork` |
| Memory Mgr (MemGPT/Letta tiers) | PARTIAL — warm/hot + outcome-rank, no eviction | **WS-3: eviction/TTL + self-edit tools** |
| Storage (vector recall) | PRESENT — embed-at-write + cosine, SurrealDB | minor: compaction/TTL |
| Tool Mgr + MCP serve/consume | PRESENT — both wired into loop | **WS-2: Code Mode**, `.mcpb` security |
| ReAct loop + context compaction | PARTIAL — universal tool-loop shipped | explicit compaction + prompt-cache |
| Computer-Use (LiteCUA roles) | PARTIAL — pc_* verbs, hermes-browser CDP, pc-vision | **WS-4: `mios-computer-use`** (VRAM-gated VLM) |
| Terminal persistence (PTY/tmux/ACI) | PARTIAL — coderun sandbox, no persistent PTY | **WS-5: PTY shell + ACI normalizer** |
| Shell impedance (PS .NET pipeline) | relevant — MiOS spans WSL + win32 nodes | WS-5 ACI across executors |
| Semantic firewall / taint / OPA-RBAC | PRESENT (strongest area) | policy engine (vs hardcoded allowlists) |
| HITL approval | PARTIAL — binds the dev, not the runtime | **WS-6: runtime approval queue** |
| Determinism / replay | ABSENT | **WS-6: parameterized run-templates** |
| Logit-level (ProbeLogits) security | ABSENT | WS-8 spike (needs logit access; vLLM) |
| Immutable host (bootc/UKI/fapolicyd) | PARTIAL — bootc; UKI transitioning | **WS-7: UKI + composefs + fapolicyd** |
| MicroVM (Firecracker/gVisor) | ABSENT — bwrap only | WS-8 Phase-4 isolation |
| Code Mode (token cut) | ABSENT | WS-2 (early win) |
| Local/Remote kernel topology | PARTIAL — tailnet A2A peers/nodes | WS-8 formalize |

---

## 2. Workstreams (sequenced by leverage)

Each obeys the binding rules: `mios.toml` SSOT (no literals in code), no
hardcoded topic/exclusion lists, no live launches from the dev assistant,
full offline, deliverables are complete-replacement files. Deploy = `wsl sudo
cp` -> `mios-sync-env` -> `systemctl restart`; push from `C:\MiOS` (Windows
git + GCM).

- **WS-1 — Finish the scheduler kernel (priority queue).** #1 structural gap,
  no new hardware. Detailed below (Section 3).
- **WS-2 — Code Mode for tools.** Biggest token win, low risk. Agents discover
  the verb/MCP surface as a local API inside the coderun bwrap sandbox and
  write code to call it, returning only filtered results instead of loading
  ~61 function schemas. Compose with `_worker_tools_surface` + per-lane
  tool-cap. Done: a multi-tool task runs with schemas out of context; measured
  token delta logged.
- **WS-3 — Memory eviction + active self-editing tiers (P2.1).** Add the
  missing MemGPT/Letta half: K-LRU eviction/TTL over the SurrealDB knowledge
  table (opt-in — first data-loss path, gate hard, back up first) + self-edit
  verbs (`core_memory_append/replace`, `search_archival`). Must not evict
  outcome-ranked "hot" rows. Builds on `_blended` (:7319) + tier promotion.
- **WS-4 — `mios-computer-use` (FOSS, replaces Wide-Moat).** LiteCUA
  Perceptor/Reasoner/Worker pattern from MiOS parts behind one agent-pipe
  front. P0 (now, no VRAM): doc-gen skills (LibreOffice/Pandoc) + register the
  `pc_*`/vision/control verbs as ONE OWUI Native tool. P1: per-chat **rootless
  podman** sandboxes (not Docker-socket). P2 (VRAM-gated): local grounding VLM
  on vLLM/SGLang (ollama can't serve grounding heads; ~16GB VRAM; Qwen3-VL-4B /
  ShowUI-2B / GUI-Actor-7B). P3: flatten into `mios-os-control`.
- **WS-5 — Stateful terminal + ACI.** PTY/tmux-wrapped persistent shell so
  cwd/env survive turns; ACI normalizer (pagination, head-tail truncate,
  explicit CWD/env injection, pre-exec arg lint) shared by the Linux + Windows
  executors. MiOS-specific angle: normalize the PowerShell .NET object pipeline
  to flat text without the documented UNIX-harness hang. Respect the
  Session-0/WSL hazard (never start the WSL VM from a Session-0 context).
- **WS-6 — Determinism + runtime HITL (P3).** Parameterized replayable
  run-templates (record a DAG run keyed by intent-class) + a pending-action
  queue that suspends write/launch verbs until an out-of-band approval
  (passport ed25519 already provides the crypto primitive). Surface the
  approval dialog in the OWUI pipe.
- **WS-7 — Immutable host hardening.** Verity-rooted UKI + composefs/fs-verity
  + fapolicyd execution whitelist (`Action = f(path, hash, pid)`) with a
  carve-out for the agent's legitimate sandboxed codegen. Rollback-tested
  (bootc atomic) before enforcing; operator-gated boot changes. See
  `usr/share/doc/mios/upstream/composefs.md`, `bootc.md`.
- **WS-8 — Research spikes (no commitment).** vLLM/SGLang heavy lane +
  LMCache (RadixAttention prefix-sharing == the swarm's shared-prefix
  workload), `kv_fork` for swarm forking, ProbeLogits (needs vLLM logit
  access), LAKE (revisit after WS-1 gives a queue to learn over), MicroVM
  upgrade from bwrap, remote-kernel topology formalization. All VRAM- or
  research-gated.

### Sequencing
1. Verify pass (confirm WS-1..3 against live `server.py`).
2. Quick wins: WS-2 (Code Mode) + WS-3 (memory eviction).
3. Hard kernel gap: WS-1 (priority queue) — deliberate, wedge-aware.
4. Security-critical: WS-6 (replay + HITL).
5. Parallel infra track: WS-7 (UKI/fapolicyd) — independent of agent-pipe.
6. Capability: WS-5 (ACI/PTY) then WS-4 (computer-use P0/P1).
7. Park behind gates: WS-8 until VRAM frees / after the queue lands.

---

## 3. WS-1 — Priority scheduler queue (file-level plan)

### Current state (verified 2026-06-04 against `server.py`)
- `_sched_priority` (:13298): turn score = `complexity*0.4 + urgency*0.6`,
  derived from the refined plan (no hardcoded topic map). Exposed at
  `/v1/scheduler` (:13349). **ADVISORY only** — the lane semaphores admit in
  arrival order; this is the documented hook a policy engine would order on.
- `_turn_priority` (:17549) = `_sched_priority(refined).score`, threaded into
  council/DAG dispatch via the `priority=` arg (:18791, :19134).
- `_dispatch_priority` (:1849): lane-based base priority for a node
  (`_LANE_PRIORITY`, SSOT `[dispatch].lane_priority`).
- `_admit` (:790): priority-weighted **BACKOFF** + VRAM co-load wait, bounded
  by `ADMIT_MAX_WAIT`, degrade-open. Higher priority -> shorter backoff. NOT a
  reordering queue.
- Acquisition chain (identical in `_call_agent_complete` :2985-2991 and
  `_call_agent_stream` :3675-3678):
  `await _admit(...)` -> `async with _GLOBAL_DISPATCH_SEM` -> `_endpoint_sem`
  -> `_lane_sem`. All three are plain `asyncio.Semaphore` -> waiters wake FIFO.
- `_lane_sched_stats` (:13324) introspects `sem._value` / `sem._waiters`.

**The gap:** once a dispatch is waiting on a semaphore, a later higher-priority
dispatch cannot jump ahead. Priority affects only the soft pre-sem backoff, not
who gets the next freed slot.

### Goal
The next freed **global** slot goes to the highest-priority waiter, not the
earliest arrival — a real reordering queue, bounded, degrade-open, behind a
default-off flag (mirrors the `_admit` rollout).

### Design (minimal, reversible)
- Add `_PriorityGate` (asyncio): a heap of waiters keyed by `(-priority, seq)`
  guarding `GLOBAL_DISPATCH_CONCURRENCY` permits. `async with
  _priority_gate(prio):` replaces `async with _GLOBAL_DISPATCH_SEM:` at the two
  call sites. Same bound; difference is wake order = highest priority first,
  FIFO tie-break via a monotonic `seq` (reuse `_ADMIT_SEQ` :694).
- Compose with `_admit`, don't replace it: `_admit` = capacity gate (don't
  start work when host is over the load/VRAM ceiling); `_PriorityGate` =
  ordering (pick the most important among the bounded running set). Keep
  `_endpoint_sem` / `_lane_sem` underneath unchanged.
- Anti-starvation: priority aging — a waiter's effective priority rises with
  wait time past `priority_starvation_ms` so low-priority never fully starves.
- Observability: extend `_lane_sched_stats` + `/v1/scheduler` to report the
  gate's heap depth and the head waiter's priority, so reordering is observable
  before/after enabling.

### Preemption (P1.1b — DEFERRED, documented only)
True turn-boundary preempt (signal the lowest-priority in-flight CPU/iGPU node
to KV-checkpoint via `_kv_paging` and yield to a starved high-priority turn)
depends on KV save on the lane + the request-cancellation plumbing. Defer; the
priority gate alone closes the #1 gap. Mid-decode preempt + cross-engine KV
migration are explicitly out of scope (Phase-4/research).

### SSOT knobs (`mios.toml [dispatch]`)
- `priority_queue_enable` (env `MIOS_PRIORITY_QUEUE`), default `false` — deploy
  as a no-op, observe at `/v1/scheduler`, then enable via an `/etc` drop-in.
- `priority_starvation_ms` — aging threshold.
- Reuse `lane_priority` + `_sched_priority`/`_dispatch_priority` — no new
  priority source.

### Safety
- DEGRADE-OPEN: any gate error -> fall through to the plain
  `_GLOBAL_DISPATCH_SEM` path (keep it as the fallback).
- Bounded: never more than `GLOBAL_DISPATCH_CONCURRENCY` in-flight; aging
  prevents indefinite low-priority wait.
- Flag-gated default-off; the proven wedge stack (global cap, circuit-breaker,
  per-lane caps, admission) stays intact underneath.

### Verification
- Unit (standalone, mock runner — mirror the `_execute_dag_saturated`
  unit-test pattern): high-priority waiter takes the next freed permit ahead of
  an earlier low-priority waiter; FIFO tie-break; aging bump fires;
  degrade-open on injected error.
- Live: deploy default-off (no-op) -> flip via `/etc` drop-in -> run ONE wide
  research turn **in OWUI** (never bounded curls — they orphan server-side
  turns and create overlap spikes) -> confirm `/v1/scheduler` shows reordering,
  load stays < ceiling, `NRestarts=0`, zero errors.

### Files touched
- `usr/lib/mios/agent-pipe/server.py` — new `_PriorityGate` + `_priority_gate()`
  near the sem defs (~:608-611 / :790); swap the two `async with
  _GLOBAL_DISPATCH_SEM` sites (:2989, :3676); extend `_lane_sched_stats`
  (:13324) + `/v1/scheduler` (:13349). Complete-replacement file per the
  deliverable rule.
- `usr/share/mios/mios.toml [dispatch]` — add `priority_queue_enable`,
  `priority_starvation_ms`.
- (optional) `/etc/mios/...` drop-in for the enable flag at deploy time.

### Out of scope for WS-1
Mid-decode preemption, cross-engine KV migration, the LAKE ML scheduler — all
WS-8/Phase-4/research.

### WS-1 build status (2026-06-04): BUILT + unit-verified, default-off, UNCOMMITTED
- `usr/lib/mios/agent-pipe/mios_sched.py` (NEW) — `PriorityGate`: pure-stdlib,
  bounded, priority-ordered, anti-starvation, cancellation-safe gate. Sibling
  module per the `mios_jsonsalvage`/`mios_owui` pattern (advances the
  modularization workstream too).
- `usr/lib/mios/agent-pipe/server.py` — `from mios_sched import PriorityGate`
  (after the mios_owui import); knobs + `_GLOBAL_PRIORITY_GATE` +
  `_priority_gate()` CM after `_GLOBAL_DISPATCH_SEM`; both
  `async with _GLOBAL_DISPATCH_SEM` chokepoints swapped to
  `async with _priority_gate(_prio)`; `priority_gate` block added to
  `/v1/scheduler`.
- `usr/share/mios/mios.toml [dispatch]` — `priority_queue_enable = false` +
  `priority_starvation_ms = 4000`.
- `usr/lib/mios/agent-pipe/test_mios_sched.py` (NEW, dev) — standalone asyncio
  test. **Result: 15/15 checks pass** (bound, priority reorder, FIFO tie-break,
  anti-starvation, cancel-while-queued, cancel-after-grant, cap-never-exceeded
  under 40-task load). `py_compile` clean on `mios_sched.py` + `server.py`.

**Deploy (operator — assistant cannot push/restart):**
1. `wsl sudo cp` `mios_sched.py` + `server.py` -> `/usr/lib/mios/agent-pipe/`,
   `mios.toml` -> `/usr/share/mios/` (the VM `/usr` is a copy, not a bind).
   `test_mios_sched.py` is dev-only; not needed at runtime.
2. `mios-sync-env` (belt-and-braces; the gate knobs are read directly from
   `mios.toml` by `_disp_num`/`_DISPATCH_TOML` at import, not via env).
3. `systemctl restart mios-agent-pipe.service`.
4. **Verify no-op:** `GET /v1/scheduler` -> `priority_gate.enabled=false`, normal
   turn works (deploy is inert until the flag flips).
5. **Flip on:** set `priority_queue_enable = true` in `/etc/mios/mios.toml`
   `[dispatch]` (admin layer wins) -> restart.
6. **Live verify:** run ONE wide research turn **in OWUI** (never bounded curls —
   they orphan server-side turns -> overlap spikes per the wedge forensics).
   Watch `/v1/scheduler.priority_gate` (`queued`, `head_priority`), load stays
   under the admit ceiling, `NRestarts=0`, zero errors.
- Push from `C:\MiOS` (Windows git + GCM), never from WSL.

---

## Appendix A — WS-2 / WS-3 code-surface map (2026-06-04 research)

Captured so the next build session starts grounded. All citations are
`server.py` lines.

### WS-3 memory (knowledge table) — clearest quick win, infra already present
- WRITE: `_store_knowledge` (7256) -> `_store_knowledge_task` (7278). Row fields:
  `q`, `answer`, `sources`, `access_count` (seed 0), `recall_hits` (seed 0),
  `tier` (seed `'warm'`), `satisfied` (outcome signal, omitted if None), `emb`
  (nomic-embed-text via `_embed_one`, best-effort), `ts`, `session_id`,
  `passport` (ed25519). Issued via `_db_create` -> `_db_post` (`/sql`),
  fire-and-forget `_db_fire`. DB NS/DB = `mios`/`mios`, creds env-sourced
  (hardcoded `root:root` defaults — see dedup-audit).
- READ: `_recall_knowledge` (7324) + `_blended` (7370). `SELECT ... ORDER BY ts
  DESC LIMIT 60`, cosine >= 0.62 (strict 0.82 else demand a shared anchor
  token), blended rank = cosine + outcome*satisfied + hot + log1p(access),
  K=3. Page-in UPDATE bumps `access_count`/`recall_hits`/`last_access` and
  promotes `tier='hot'` at access_count >= 5 (7408).
- EVICTION: **none** — confirmed. Deferral comment at 7131. `tier`,
  `last_access`, `access_count`, `satisfied` are all already populated, so an
  eviction policy is pure addition (no migration).
- WORKING MEMORY: `_SCRATCHPADS` (4800) — per-chat `deque(maxlen=60)`, TTL 1h,
  LRU 256 chats, in-memory only (lost on restart). `_scratchpad_note` (4912) /
  `_scratchpad_render` (4924).
- SELF-EDIT VERBS: `remember`/`recall` are **declared in agent prose** (5091)
  but **not implemented** as verbs -> the prose/impl gap WS-3(b) closes.

### WS-2 Code Mode — bigger than a quick win; do after WS-3
- TOOL SURFACE: `_worker_tools_surface` (4664, sync verbs+recipes) +
  `_worker_tools_surface_async` (4722, adds promoted skills + MCP tools, sorts
  by `_tool_priority` 4697, caps via `cap` arg). ~71 OpenAI function-tool dicts
  (`x-mios-verb`/`-recipe`/`-skill`/`-mcp-server` routing hints). Caches:
  `_WORKER_TOOLS_CACHE` (4657), `_WORKER_TOOLS_FULL_CACHE` (4736).
- PER-LANE CAP: `LANE_TOOL_CAP` (395) / `SLOW_LANE_TOOL_CAP` (407) /
  `_lane_tool_cap` (412). Already shrinks the surface on weak lanes — so Code
  Mode's token win is mainly the FULL surface on capable lanes + local result
  filtering.
- EXEC CHOKEPOINT: `_exec_tool_calls` (3372) — branches skill (3411) / recipe
  (3436) / MCP `mcp.*` -> `_mcp_call_tool` (3462) / verb -> `dispatch_mios_verb`
  (3481). `allow_write` gates non-read. `_build_dispatch_cmd` (11787) maps
  verb+args -> broker command (SSOT `[verbs.*].cmd` template).
- CODE SANDBOX: **not wired into the agent-pipe** — `coderun` is prose intent
  (5095) only; the system-level coderun-sandbox (podman) is not a tool path.
  Code Mode must wire it in first. No `./servers/` virtual-FS discovery exists.
- INJECTION: tools attached to worker/DAG nodes (10194) + council secondaries
  (18827 stream / 19159 non-stream) under `WORKER_TOOL_CTX` 16384 /
  `WORKER_TOOL_CTX_SLOW` 6144. `tool_choice=required` stripped for endpoints
  that 400 on it (iGPU llama.cpp).

---

## WS-3 build status (2026-06-04): BUILT + unit-verified, default-off, UNCOMMITTED

Scope corrected during the build: `remember`/`recall` ALREADY EXIST as real
broker verbs (`mios.toml` `[verbs.remember]`/`[verbs.recall]` ->
`usr/libexec/mios/mios-remember`, with scope/key add+list+update/forget). NOT
reimplemented — a second in-process memory path would fragment memory. So WS-3
shipped the genuine gap: **bounded K-LRU + TTL eviction over the auto-append
`knowledge` table** (the mios-remember facts are a separate store, untouched).

- `usr/lib/mios/agent-pipe/mios_evict.py` (NEW) — pure helpers: `protect_where`,
  `ttl_where`, `parse_count`, `parse_ids`, `delete_stmt`, `plan_sweep`. DB-free,
  unit-testable (sibling-module pattern).
- `usr/lib/mios/agent-pipe/server.py` — import; `KNOWLEDGE_EVICT_*` knobs after
  `KNOWLEDGE_HOT_THRESHOLD`; `_db_count` / `_evict_select_ids` /
  `_evict_delete_ids` / `_evict_knowledge` / `_knowledge_evict_loop` +
  `@app.on_event("startup")` after `_recall_knowledge`; `knowledge_eviction`
  posture block in `/v1/scheduler`.
- `usr/share/mios/mios.toml [knowledge]` — `evict_enable`/`evict_dryrun`/
  `evict_interval_s`/`evict_ttl_days`/`evict_max_rows`/`evict_min_access`/
  `evict_batch` (all default to a no-op: the loop only starts when enable OR
  dryrun is set).
- `usr/lib/mios/agent-pipe/test_mios_evict.py` (NEW) — **24/24 checks pass**
  (protect/ttl SQL fragments, count/id parsing, delete-stmt building, the
  batch-bounded plan arithmetic). `py_compile` clean.

NEVER deletes hot / satisfied / pinned / recently-accessed rows. Per-sweep
`evict_batch` bounds blast radius.

**Deploy (operator):** `wsl sudo cp` `mios_evict.py` + `server.py` ->
`/usr/lib/mios/agent-pipe/`, `mios.toml` -> `/usr/share/mios/`; `mios-sync-env`;
`systemctl restart mios-agent-pipe.service`. **BACK UP the knowledge table
first.** Then set `[knowledge].evict_dryrun = true` in `/etc/mios/mios.toml`,
restart, and watch the journal for `knowledge-evict DRY-RUN: would remove ...`;
once the counts look right, set `evict_enable = true`.
`/v1/scheduler.knowledge_eviction` shows the posture.

Follow-ups (not built): unify the auto-RAG recall to also surface mios-remember
facts; a `search_archival` verb exposing `_recall_knowledge` on demand.

---

## WS-6 build status (2026-06-04): BUILT + unit-verified, ON by default

Two pieces: (1) runtime HITL approval gate, (2) replayable run-template capture.

- `usr/lib/mios/agent-pipe/mios_hitl.py` (NEW) — pure decision helpers
  (`parse_scope`/`requires_approval`/`gate_outcome`/`block_result`).
- `server.py` — import; `HITL_*` knobs + `_hitl_is_approved`/
  `_hitl_record_pending`/`_hitl_gate` + `GET /v1/hitl/pending` +
  `POST /v1/hitl/approve` (passport-signed) after `_emit_session_event`; the
  gate call in `_dispatch_mios_verb_inner` right after the taint firewall;
  `RUN_TEMPLATE_*` + `_run_template_class`/`_capture_run_template` +
  `GET /v1/run-templates` before `execute_dag`; the capture call at the top of
  `execute_dag` (single point — covers saturated + level paths).
- `mios.toml` — `[hitl]` (enable=true, mode="log", verbs="") + `[run_template]`
  (enable=true).
- `test_mios_hitl.py` (NEW) — **19/19 pass**. `py_compile` clean.

ON by default per the 'everything on' directive, BUT HITL `mode` defaults to
**`log`** (non-blocking: emits a `hitl_request` event then proceeds) so the
autonomous swarm is never deadlocked. Flip `[hitl].mode = "gate"` to actually
block scoped (high-privilege) verbs until `POST /v1/hitl/approve` (the agent's
retry of the approved action then passes). Approvals are passport-signed;
`_action_hash` is the approval key.

Run-templates: capture + `GET /v1/run-templates` observability shipped; replay-
REUSE (match a new turn to a stored plan + skip planning) is the documented
follow-up.

Deploy: `wsl sudo cp` `mios_hitl.py` + `server.py` + `mios.toml`; `mios-sync-env`;
restart. Verify: `GET /v1/hitl/pending`, `GET /v1/run-templates`.

---

## WS-5 build status (2026-06-04): ACI normalizer BUILT + unit-verified, ON; PTY = follow-up

The persistent-PTY / stateful-shell half is cross-component (no shell substrate
lives in the agent-pipe — it belongs with the coderun sandbox / broker shell) and
is a documented follow-up. The ACI OUTPUT NORMALIZER (the survey's head-tail
truncation) is built + on:

- `usr/lib/mios/agent-pipe/mios_aci.py` (NEW) — `normalize_output`: head-TAIL
  truncation (keep start + end, elide the middle with an anti-fabrication
  marker), line + char caps, degrade-open.
- `server.py` — import; `ACI_MAX_LINES`/`ACI_HEAD_FRAC` knobs; `_cap_verb_result`
  rewritten to use it (was head-only `out[:cap]`, which dropped the tail where a
  command's error/exit/result lands).
- `mios.toml [aci]` — `max_lines=160`, `head_frac=0.6`.
- `test_mios_aci.py` (NEW) — **14/14 pass**. `py_compile` clean.

Now every verb/recipe result keeps its tail (the result/error), not just its
head. Follow-ups: a persistent PTY/tmux shell so cwd/env survive turns (needs the
coderun/broker shell substrate); the PowerShell .NET-pipeline → flat-text
normalization belongs in the Windows executor (`mios-oscontrol-server.ps1`);
optionally route the skill/MCP result slices through the ACI too.

---

## Appendix B — remaining workstreams (WS-2/4/7/8): specs + prerequisites

WS-1/3/5/6 are pure agent-pipe changes → built, unit-tested, default-on. The
four below are **cross-component / infra / hardware-gated**, so they cannot be
safely built blind + flipped on from inside the agent-pipe. Each is spec'd to be
ready when its prerequisite is met. (Honest scope: shipping unsandboxed
code-exec, an un-booted fapolicyd policy, or a VRAM-less vLLM lane "on" would be
reckless on a live box — these need their substrate first.)

### WS-2 — Code Mode  ·  prerequisite: coderun sandbox wired into the tool loop
- The agent-pipe has NO code-exec tool path today (`coderun` is prose-only at
  server.py:5095; `_exec_tool_calls` branches are skill/recipe/MCP/verb). The
  system-level coderun-sandbox (podman; `concepts/coderun-sandbox.md`) is not a
  verb.
- Build order: (1) add a `coderun` verb (`mios.toml [verbs.coderun]` →
  `_build_dispatch_cmd` → broker → the rootless-podman coderun container,
  permission=write); (2) inside that sandbox, expose the verb/MCP surface
  (`_worker_tools_surface_async`, server.py:4722) as a local Python API the
  generated code calls, returning only filtered results; (3) measure the token
  delta vs the current per-lane capped surface.
- Why not default-on-now: executing model-written code requires the sandbox to
  exist + be verified; doing it unsandboxed is a security non-starter.

### WS-4 — mios-computer-use P0  ·  prerequisite: doc-gen binaries + OWUI pipe deploy
- `pc_click`/`pc_type`/`pc_key` + `mios-pc-vision`/`mios-pc-control` verbs already
  exist. P0 = (a) doc-gen skills (pptx/docx/xlsx/pdf) via **LibreOffice + Pandoc**
  — new `usr/libexec/mios/` CLI tools + `mios.toml [verbs.*]`/recipes (needs the
  binaries in the image, `[packages.*]`); (b) register the pc_*/vision/control
  verbs as ONE OWUI Native tool — an OWUI **pipe/function** deployed via
  `mios-owui-install-pipe` (NOT an agent-pipe edit; webui.db function table).
- Why not default-on-now: spans the image package set + the OWUI container; not a
  `server.py` change. Do NOT vendor Wide-Moat (BSL/no-offline) — build from MiOS
  parts (see §0-B + `open_computer_use_plan`).

### WS-7 — Immutable host: UKI + fapolicyd  ·  prerequisite: image rebuild + boot test
- Files to add (image-build artifacts, NOT live toggles): a verity-rooted UKI in
  the Containerfile/BIB path (`concepts`/`upstream/bootc.md`,`composefs.md`); a
  fapolicyd execution-whitelist policy under `usr/lib/...` with a carve-out for
  the sandboxed agent codegen (WS-2); `kargs.d` entries.
- **HARD SAFETY LINE — not flipped on by the 'everything on' directive.**
  fapolicyd enforce-mode or a mis-signed UKI **bricks boot**; this is the one
  place "default on, debug live" is the wrong order. Build it in a dedicated
  image-build session, enable in **permissive** mode first, confirm via
  `just build` + a VM boot + rollback test (bootc atomic), THEN enforce. Holding
  this off-by-default is deliberate, not incomplete.

### WS-8 — Research spikes  ·  prerequisite: VRAM free / research time
- vLLM/SGLang heavy lane + LMCache (RadixAttention = the swarm's shared-prefix
  workload): built+gated, **VRAM-blocked** by the Windows-held 4090 (see
  `gpu_igpu_compute_topology`). Turning it "on" now just fails — activate when
  VRAM frees.
- `kv_fork` (extends `_kv_paging` on llama.cpp), ProbeLogits (needs logit access
  → vLLM, not ollama), LAKE (revisit after the WS-1 queue gives it something to
  learn over), MicroVM (Firecracker/gVisor upgrade from bwrap): research-grade,
  not flip-on features.

### Net status for the live-test session
Default-ON and ready to exercise on MiOS-DEV: **WS-1 priority queue, WS-3
knowledge eviction, WS-5 ACI normalization, WS-6 HITL (log mode) + run-template
capture.** Deploy = `wsl sudo cp` the new sibling modules (`mios_sched.py`,
`mios_evict.py`, `mios_hitl.py`, `mios_aci.py`) **alongside** `server.py`, plus
`mios.toml`; `mios-sync-env`; `systemctl restart mios-agent-pipe.service`. The
four sibling modules are easy to forget — the normal deploy only copies
`server.py`.
