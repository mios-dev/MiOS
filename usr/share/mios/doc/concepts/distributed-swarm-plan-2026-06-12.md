<!-- AI-hint: Architectural roadmap for the MiOS distributed agent swarm — the design for moving the AI plane from single-large-model execution to concurrent multi-small-model, tool-capable execution across the CPU pool, the shared dGPU, and remote/local nodes, all behind the one MIOS_AI_ENDPOINT.
     AI-related: mios-agent-pipe, mios-llm-light, mios-llm-heavy, mios-llm-heavy-alt, mios-llm-worker, mios-swarm-pack-firstboot, mios-heavy -->
# MiOS Distributed Concurrent Multi-(small)-Model Tool-Swarm — Design + Plan (2026-06-12)

> **Status (2026-06-13):** roadmap doc — partially landed. The SSOT scaffolding
> (sub-lane keys, `[dispatch].gpu_profile`/`vram_budget_mb`/`lane_concurrency_gpu0`,
> the `mios-llm-worker@.container` template + `mios-swarm-pack-firstboot` guard) is
> SHIPPED and inert-by-default; arming the dGPU small-model pack (Phase 3) and
> raising per-engine concurrency (Phase 7) remain VRAM-risky and operator-gated.
> Naming reflects the function-based engine rename (`mios-llm-light` /
> `mios-llm-heavy` / `mios-llm-heavy-alt` / `mios-llm-worker@`).

## Purpose — where this fits in MiOS as a whole

MiOS is one system built two ways at once: an **immutable bootc/OCI Fedora
workstation** (the whole OS is a single container image you `bootc upgrade` like a
`git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a **local,
self-replicating, agentic AI operating system**. The same image that ships
GNOME/Wayland, GPU passthrough, and a k3s+Ceph cluster path also ships a complete
local agent stack behind **one** OpenAI-compatible endpoint (`MIOS_AI_ENDPOINT`,
Architectural Law 5).

A user request enters from a front-end (OWUI `:3030`, the Discord gateway, the
`mios` CLI) and flows into the **agent-pipe** orchestrator (`:8640`), which refines
it, fans it out across a council/swarm, and dispatches tool/verb calls;
**MiOS-Hermes** (`:8642`) is the OpenAI-compatible gateway and tool-loop agent;
**pgvector** (`:5432`) is the unified agent memory (tiered memory, knowledge,
sessions, skills, RAG embeddings); the **inference lanes** below do the actual
generation and embeddings; **MCP** exposes the tool surface and **A2A** federates
peer agents.

This document specifies the design and rollout for the *generation* half of that
brain: turning the agent plane from "route one request to one big model" into a
**distributed concurrent tool-swarm** that spreads many small, tool-capable models
across all available compute — the CPU pool, the shared dGPU, and remote/local
nodes — and synthesises their results. The orchestration, memory, and tool
surfaces around it already exist; this is about making the inference *fan-out*
real and OOM-safe.

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
every dGPU worker collapses onto ONE `lane='gpu'` semaphore AND ONE
**mios-llm-light** daemon (the llama.cpp lane behind the upstream mios-llm-light
proxy runs `--parallel 1`, so it swaps models serially). Fix = per-engine
SUB-LANES +
MULTIPLE single-model llama-server instances (`mios-llm-worker@`). Not a rewrite.

## Why one big model failed (context)
Qwen3-14B-AWQ (9.4GB) will NOT load on this shared 4090: ~13.9GB free after
stopping the lane, but 9.4GB weights + SGLang/cuDNN overhead (~3-4GB) exceeds the
envelope → "Not enough memory" even at mem-fraction 0.55 + fp8 KV (confirmed
2026-06-12; SGLang fails GRACEFULLY, no VM crash). This is the heavy lane's own
documented history (the 14B already OOM-cascaded → downsized). So the
swarm-of-small-models is the RIGHT answer to "14b too weak" — distribute, not
enlarge. The heavy lane stays a single bounded reasoner: **Qwen3-8B-AWQ**
(text-only, 4-bit, ~5.5GB) served as `mios-heavy` on **mios-llm-heavy** (SGLang,
`:11441`), which fits the shared 4090 cleanly alongside the light lane.

## Concurrency model (shared 4090, ~11GB agent VRAM budget)
The dGPU budget is SSOT: `[dispatch].vram_budget_mb` (currently 11000). Two
operator-selectable dGPU profiles via `[dispatch].gpu_profile`:
- Profile A "orchestrator" (current default, safe): 1× heavy reasoner on the
  **mios-llm-heavy** SGLang lane (Qwen3-8B-AWQ, ~5.5GB + KV).
- Profile B "swarm": 3-4 small single-model **mios-llm-worker@** instances
  concurrently (each one independent `llama-server`), e.g. 3× `lfm2:700m`
  (~2.2GB) + 1× a small 4B (~3.4GB) ≈ 10GB + KV < budget. Each worker is its OWN
  process → all generate truly concurrently (no `--parallel 1` swap on the shared
  light lane).
- CPU pool: 3-4× small models with `ngl=0` (n-gpu-layers 0), RAM-bound, on a
  separate `_lane_sem` → fire in parallel with the dGPU pool.
- Remote nodes: each `[nodes.*]` overlay node is its own sub_lane → concurrent.

All workers serve the same OpenAI/Ollama-compatible API the rest of the stack
speaks, so the agent-pipe dispatches to them exactly like any other `[nodes.*]`
endpoint — no special-casing.

OOM-cascade structurally prevented by: (1) multiple FIXED single-model servers
(no in-server cold-load growth); (2) per-endpoint VRAM lease in `_admit`; (3)
sub_lane keys (`gpu0` packs at `lane_concurrency_gpu0`, heavy `gpu` at its low
ceiling, mutually exclusive); plus the firstboot Σvram≤`vram_budget_mb` guard +
`health_gate` + the hard `_lane_sem` as three independent backstops.

## 7-phase plan (smallest-valuable-first; all no-hardcode, SSOT, degrade-open)
- **Phase 0 — sub-lane keys** (ZERO VRAM risk, pure refactor): `_lane_sem_key`
  returns `cfg.sub_lane or _agent_lane(cfg)`; `_load_node_pool` reads `sub_lane`;
  fan-out/DAG diversity sort by sub_lane. Byte-identical when unset. *(SSOT keys
  `sub_lane` / `lane_concurrency_gpu0` are present in mios.toml.)*
- **Phase 1 — per-worker VRAM/RAM budget + per-endpoint lease in `_admit`** (no
  risk; tightens safety): read `vram_mb`/`ram_mb`/`tool_capable`; `_ENDPOINT_RESERVED`
  counter so siblings co-admitting see each other's pending cost.
- **Phase 2 — templated `mios-llm-worker@.container`** + firstboot
  oversubscription guard (inert until armed; refuses to arm if Σvram>budget).
  *(SHIPPED: `usr/share/containers/systemd/mios-llm-worker@.container` +
  `mios-swarm-pack-firstboot`, both gated on `/run/mios/swarm/%i.env` and the
  provisioned-GGUF marker `/usr/share/mios/llamacpp/models/.ready`.)*
- **Phase 3 — arm the dGPU small-model pack (Profile B)** ⚠️ VRAM-RISKY,
  OPERATOR-GATED (provision GGUFs, flip `gpu_profile="swarm"`, verify
  nvidia-smi/journal).
- **Phase 4 — A2A-consume client** (no local VRAM risk): `_a2a_send_message_to_peer`
  + inject `a2a:<peer>` as synthetic workers (mirror `_load_node_pool`), opt-in
  `[a2a].council`. Closes the publish-only "ENSEMBLE not FEDERATION" gap.
- **Phase 5 — per-node task re-parameterization** (quality): tailor each facet to
  the worker before dispatch.
- **Phase 6 — intermediate-result replan + tailnet node autodiscovery** (advanced).
- **Phase 7 — per-engine concurrency tuning** ⚠️ measure-then-raise
  `lane_concurrency_gpu0`/`lane_concurrency_gpu`/`global_concurrency`.

Only Phases 3 & 7 are VRAM-risky/operator-gated; 0,1,2,4,5,6 are inert-by-default
safe additions. Files:
- `usr/lib/mios/agent-pipe/server.py` — `_lane_sem_key`/`_lane_sem`/`_load_node_pool`/
  `_admit`/`_pick_fanout_agents`/`_agent_dag_from_tasks` + new A2A-consume/replan
  helpers.
- `usr/share/mios/mios.toml` — `[nodes.*]` fields (`sub_lane`/`vram_mb`/`ram_mb`/
  `tool_capable`) + the inert `[nodes.swarm-*]` worker examples +
  `[dispatch].gpu_profile`/`vram_budget_mb`/`lane_concurrency_gpu0` +
  `[a2a].council`.
- `usr/share/containers/systemd/mios-llm-worker@.container` + the
  `mios-swarm-pack-firstboot` Σvram guard.

All of the above stay within MiOS's contract: capabilities and tunables live in
`mios.toml` (SSOT, no command literals in code), every lane resolves
`MIOS_AI_ENDPOINT` (Law 5), the worker Quadlet is unprivileged + bound (Laws 3/6),
and nothing arms until the operator both provisions weights and flips the profile —
so the immutable-image guarantees and the OOM-safety guarantees hold together.
