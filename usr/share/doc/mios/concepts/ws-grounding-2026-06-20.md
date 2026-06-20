<!-- AI-hint: Code-grounding verdicts for the MiOS master plan — per-workstream DONE/PARTIAL/MISSING assessment against the live tree at HEAD 8658df1, with exact file:line anchors. The headline split: Track-A AIOS-kernel primitives are unbuilt; the security/federation/infra half is largely built. Companion machine file: ws-grounding-2026-06-20.json.
     AI-related: usr/share/doc/mios/concepts/ws-grounding-2026-06-20.json, usr/share/doc/mios/concepts/ws-0-preflight-findings-2026-06-20.md, usr/lib/mios/agent-pipe/server.py, C:/Users/mios/MIOS-MASTER-PLAN.tasks.json -->

# MiOS master-plan — code-grounding verdicts (2026-06-20, HEAD 8658df1)

Per-workstream assessment of the master plan against the **live** `C:/MiOS`
tree. Machine-readable companion: `ws-grounding-2026-06-20.json`.

## Method & headline

A fan-out of read-only agents grounded each workstream's acceptance criteria
against the actual code (the 27,311-line `agent-pipe/server.py`, its
`mios_*.py` sibling modules, `test_mios_*.py` suites, `automation/*.sh`,
`mios.toml`, `ai/v1/*.json`). **Finding: the plan splits cleanly in two.**

- **Track-A kernel primitives (early/mid waves): genuinely UNBUILT.** The 11
  grounded so far are all `missing` with high confidence — these are the new
  AIOS-LLM-kernel seams (tokenizer, ctx-packing, trace, PDP, batch-coalesce,
  RR-preempt, MemoryProvider, SmartRouting, tool-conflict, fail-loud catalog,
  the Router/Dispatcher decomposition).
- **Security / federation / infra half: largely BUILT** (prior backlog clear:
  signed A2A principal, mTLS-PKI, reputation, egress firewall, owner_user RLS,
  k3s gen, GOAP lane, self-improve). These 18 were not re-grounded here (quota
  reset) and need a second pass.

## Grounded `missing` workstreams (11) — exact anchors in the JSON

| Task | WS | Keystone deltas (abridged) |
|---|---|---|
| #2 | WS-A1 | fail-loud `_load_verb_catalog`/`_load_recipe_catalog` gated by `[ai].catalog_fail_mode`; `mios-ai-manifest-gen` projecting `ai/v1/*.generated.json` w/ `--check`; `48-ai-manifest-drift.sh`; `registry_kind` in tools.json; test |
| #6 | WS-A2 | `emb_model`/`emb_version` columns + stamping; persist `_SCRATCHPADS` → pg `scratch` + rehydrate; `mios_embed_backfill.py`; SSOT flags; test |
| #7 | WS-A5 | `mios_tokenize.py` seam + `mios_ctxpack.py` + `mios_compact.py`; replace `//4` heuristics (`_fit_context` 7336, `_usage_estimate` 24653); route `[:200]`/`SLOW_LANE_BLOCK_CHARS` slices through `truncate_to_tokens`; tests |
| #8 | WS-A7 | `mios_toolconflict.py` (limit/group maps + asyncio acquire/release); parse `parallel_limit`/`conflict_group` in `_load_verb_catalog`; wire into `_dispatch_bounded` (16581); declare on stateful verbs; test |
| #13 | WS-A8 | `event` table trace cols; `mios_trace.py` span emitter; trace/span contextvars; mint+propagate trace id in `chat_completions` (24747); stage spans; `GET /v1/trace/{id}`; `scheduler_state` block; SSOT keys; test |
| #15 | WS-A11≡3 | `mios_router.py` (Router + `RouteDecision`); `mios_kernel.py` (Kernel facade: Scheduler/Memory/Context/Tool/Access managers + Dispatcher); `KERNEL` instantiated; `chat_completions` delegates (removes inline `refined.get('intent')` cascade); tests + harness |
| #16 | WS-A12 | `mios_preempt.py` snapshot contract; PriorityGate quantum + suspend-counter in `mios_sched.py`; interruptible decode; suspend→requeue→resume; `[dispatch] rr_*` keys; test (depends on #15 Context seam) |
| #17 | WS-A15 | `mios_memory.py` (MemoryProvider ABC + PgVectorMemoryProvider + `get_memory_provider` fail-closed); rewire `_store_knowledge_task`/`_recall_agent_memory`/`_recall_knowledge_pg`; `[pgvector].memory_provider`; test (depends on #6) |
| #19 | WS-A6 | `mios_batch.py` coalescer; `_batch_key(ep,model)`; wire into `_call_agent_complete` (3917) w/ native-batch bypass; `scheduler_state` `.batch` block; `[dispatch] batch_*` keys; test (depends on #15) |
| #20 | WS-A16 | Lane cost/quality metadata + `cost_estimate()`; `mios_smartroute.py`; `[ai.remote_cores.*]`; wire dead anthropic/gemini adapters into call path; cost ledger; tests (depends on #15) |
| #21 | WS-A9 | `mios_pdp.py` decision core; `_dispatch_agent_var` contextvar; fix fail-OPEN `max_permission` (6981); wire PDP into `_dispatch_mios_verb_inner` (16701); share core with surface RBAC filters; audit event; SSOT keys; postcheck lint; test (depends on #13) |

## Verification model

Every grounded suite is a pure-stdlib `python3 <test_mios_*.py>` assert-script
(no pytest, no DB, no `server.py`) — runnable on the build host AND in-build via
`build.sh`. The full live-stack/VM build run remains the operator's final gate.
