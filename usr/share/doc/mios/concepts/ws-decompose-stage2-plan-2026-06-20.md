<!-- AI-hint: Stage-2 execution plan for the WS-A11/WS-3 server.py decomposition -- maps each chat_completions intent branch to its Kernel manager + Dispatcher handler, the behaviour-parity test plan, and the staged-cutover order, so the HIGH-RISK central-path rewire is executed safely (VM-verified) after the Stage-1 seam trio (mios_router/mios_dispatcher/mios_kernel) already shipped.
     AI-related: usr/lib/mios/agent-pipe/mios_router.py, usr/lib/mios/agent-pipe/mios_dispatcher.py, usr/lib/mios/agent-pipe/mios_kernel.py, usr/lib/mios/agent-pipe/server.py -->

# WS-A11/WS-3 decompose — Stage 2 execution plan (2026-06-20)

Stage 1 shipped the **pure seam trio** (additive, unwired, 40 host-tests green):
`mios_router` (Router → `RouteDecision`), `mios_dispatcher` (mode → injected
handler), `mios_kernel` (composes `route → dispatch` + 5 manager seams). Stage 2
is the **high-risk, VM-verified** rewire of the live `chat_completions` central
path. This plan makes it safe + incremental.

## Manager-seam adapters (server.py builds these over EXISTING code)

Each AIOS manager is a thin adapter over modules already shipped this wave —
**no new logic**, just composition:

| Kernel seam | Adapter wraps (already shipped) |
|---|---|
| `scheduler` | `_GLOBAL_PRIORITY_GATE` (mios_sched) + `_PREEMPT` (mios_preempt) + lane sems |
| `memory` | `_MEMORY` (mios_memory MemoryProvider) + scratchpad persist/rehydrate (WS-A2) |
| `context` | mios_tokenize + mios_ctxpack + mios_compact (WS-A5) + KV paging/fork (WS-A4) |
| `tools` | `_TOOL_CONFLICT` (mios_toolconflict) + `dispatch_mios_verb` chokepoint |
| `access` | `_dispatch_pdp_reason` (mios_pdp) + HITL gate + mios_secset + mios_principal |

## Per-mode handlers (lift the EXISTING branch bodies behind the seam)

`RouteDecision.mode` → the current inline body, registered into the Dispatcher:

| mode | current chat_completions site | handler = (no behaviour change) |
|---|---|---|
| `chat` | `refined.get('intent')=='chat'` reply path | the conversational-reply block |
| `dispatch` | the `intent=='dispatch'` fast-path | `dispatch_mios_verb(tool,args)` |
| `multi_task` | the broad swarm fan-out | `_plan_swarm` + the council/DAG fan-out |
| `dag` | the DAG branch | `execute_dag` |
| `agent` | the default agent tool-loop | the native-loop / `_respond_native_loop_direct` |

The hybrid/compute/council *promotions* currently layered into the cascade move
INTO the relevant handler (they refine WITHIN a mode), not into the Router —
keeping the Router a pure primary classifier.

## Staged cutover (each step committed + VM-verified before the next)

1. **Adapters only** — build the 5 manager adapters + register `KERNEL` once
   (near `_VERB_CATALOG`), but DO NOT yet rewire `chat_completions`. Verify the
   build + `scheduler_state.kernel.managers()` shows all 5 wired.
2. **Shadow route** — at `chat_completions` top, compute
   `KERNEL.router.route(refined)` and LOG it next to the cascade's chosen branch;
   ship a few turns, confirm the Router's mode == the cascade's actual path for
   every intent (parity telemetry, zero behaviour change).
3. **Delegate one mode at a time** — replace the `chat` branch with
   `KERNEL.dispatcher.run(decision)` first (lowest risk), VM-verify, then
   `dispatch`, then `agent`, then `multi_task`/`dag`. Keep the old branch behind
   a `[ai].kernel_dispatch` flag (default off → old path) until each mode is
   proven, then flip the flag.
4. **Remove the cascade** — once all modes delegate + the flag is on by default,
   delete the inline `refined.get('intent')` cascade; `38-drift-checks`
   `check_module_boundary` already guards the new modules from importing back.
5. **Thread trace** — pass the WS-A8 trace id through `KERNEL.handle` so each
   mode handler opens a stage span under the request trace.

## Parity gate

Add `test_mios_router.py`-style golden cases asserting `Router.route(refined)`
matches a recorded `(intent, flags) → expected mode` table for every shipped
intent; run in-build. A divergence fails the build BEFORE the flag flips.

## Why staged + flagged

`chat_completions` is the single live path every gateway (OWUI, Discord, CLI)
hits. The flag + per-mode cutover means a parity bug in one mode degrades to the
proven old branch for that mode only, never a full-pipeline outage — and each
step is reversible by flipping `[ai].kernel_dispatch` off.
