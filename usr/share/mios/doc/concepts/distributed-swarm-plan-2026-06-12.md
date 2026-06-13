<!-- AI-hint: Specifies the architectural roadmap for the MiOS distributed swarm, detailing the transition from single-large-model execution to concurrent multi-small-model execution across local, dGPU, and remote nodes.
     AI-related: mios-heavy, mios-llama-worker -->
# MiOS Distributed Concurrent Multi-(small)-Model Tool-Swarm — Design + Plan (2026-06-12)

Operator directive: "MiOS AI should DELEGATE A SWARM to multiple smaller models
against ALL hardware endpoints and networked nodes — 3-4 small models on the CPU,
3-4 on the dGPU, multiple across remote+local nodes, each tool-capable, doing
individual tasks all CONCURRENTLY."

## Verdict
~70% already built. `_load_node_pool` + `_AGENT_REGISTRY` + `_pick_fanout_agents`
/`_agent_dag_from_tasks` + the four-gate `_call_agent_complete`
(`_priority_gate`→`_endpoint_sem`→`_lane_sem`→`_admit`) IS a distributed
concurrent swarm with VRAM-aware admission and concurrent multi-NODE fan-out.
What is MISSING is "3-4 small models PER DEVICE running SIMULTANEOUSLY" — because
every dGPU worker collapses onto ONE `lane='gpu'` semaphore AND ONE llama-swap
daemon (`--parallel 1` swaps models serially). Fix = per-engine SUB-LANES +
MULTIPLE single-model llama-server instances. Not a rewrite.

## Why one big model failed (context)
Qwen3-14B-AWQ (9.4GB) will NOT load on this shared 4090: ~13.9GB free after
stopping the lane, but 9.4GB weights + SGLang/cuDNN overhead (~3-4GB) exceeds the
envelope → "Not enough memory" even at mem-fraction 0.55 + fp8 KV (confirmed
2026-06-12; SGLang fails GRACEFULLY, no VM crash). This is the quadlet's own
documented history (the 14B already OOM-cascaded → downsized to Qwen3-8B). So the
swarm-of-small-models is the RIGHT answer to "14b too weak" — distribute, not
enlarge. Heavy lane stays Qwen3-8B (`model-q3-8b` on SGLang :11441, mios-heavy).

## Concurrency model (shared 4090, ~12GB agent budget)
Two operator-selectable dGPU profiles via SSOT `[dispatch].gpu_profile`:
- Profile A "orchestrator" (current default, safe): 1× heavy reasoner on SGLang
  (~9-10GB).
- Profile B "swarm": 3-4 small single-model llama-server instances concurrently,
  e.g. 3× qwen3:1.7b (~2.2GB) + 1× qwen3:4b (~3.4GB) ≈ 10GB + KV < 12GB. Each is
  its OWN process → all generate truly concurrently (no `--parallel 1` swap).
- CPU pool: 3-4× small models (num_gpu 0), RAM-bound, separate `_lane_sem` → fire
  in parallel with the dGPU pool.
- Remote nodes: each `[nodes.*]` overlay node is its own sub_lane → concurrent.

OOM-cascade structurally prevented by: (1) multiple FIXED single-model servers
(no in-server cold-load growth); (2) per-endpoint VRAM lease in `_admit`; (3)
sub_lane keys (`gpu0` pack at concurrency 4, heavy `gpu_heavy` at 1, mutually
exclusive); plus the startup Σvram≤budget guard + health_gate + the hard
`_lane_sem` as three independent backstops.

## 7-phase plan (smallest-valuable-first; all no-hardcode, SSOT, degrade-open)
- **Phase 0 — sub-lane keys** (ZERO VRAM risk, pure refactor): `_lane_sem_key`
  returns `cfg.sub_lane or _agent_lane(cfg)`; `_load_node_pool` reads `sub_lane`;
  fan-out/DAG diversity sort by sub_lane. Byte-identical when unset.
- **Phase 1 — per-worker VRAM/RAM budget + per-endpoint lease in `_admit`** (no
  risk; tightens safety): read `vram_mb`/`ram_mb`/`tool_capable`; `_ENDPOINT_RESERVED`
  counter so siblings co-admitting see each other's pending cost.
- **Phase 2 — templated `mios-llama-worker@.container`** + firstboot
  oversubscription guard (inert until armed; refuses to arm if Σvram>budget).
- **Phase 3 — arm the dGPU small-model pack (Profile B)** ⚠️ VRAM-RISKY,
  OPERATOR-GATED (provision GGUFs, flip gpu_profile, verify nvidia-smi/journal).
- **Phase 4 — A2A-consume client** (no local VRAM risk): `_a2a_send_message_to_peer`
  + inject `a2a:<peer>` as synthetic workers (mirror `_load_node_pool`), opt-in
  `[a2a].council`. Closes the publish-only "ENSEMBLE not FEDERATION" gap.
- **Phase 5 — per-node task re-parameterization** (quality): tailor each facet to
  the worker before dispatch.
- **Phase 6 — intermediate-result replan + tailnet node autodiscovery** (advanced).
- **Phase 7 — per-engine concurrency tuning** ⚠️ measure-then-raise
  `lane_concurrency_gpu0`/`global_concurrency`.

Only Phases 3 & 7 are VRAM-risky/operator-gated; 0,1,2,4,5,6 are inert-by-default
safe additions. Files: server.py (`_lane_sem_key`/`_lane_sem`/`_load_node_pool`/
`_admit`/`_pick_fanout_agents`/`_agent_dag_from_tasks` + new A2A-consume/replan
helpers), mios.toml (`[nodes.*]` new fields + inert `[nodes.local-dgpu-a..d]` +
`[dispatch].gpu_profile`/`lane_concurrency_gpu0` + `[a2a].council`), new
`usr/lib/mios/llamacpp/mios-llama-worker@.container` + firstboot guard.
