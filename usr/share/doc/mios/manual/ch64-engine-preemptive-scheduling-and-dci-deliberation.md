<!-- AI-hint: Chapter 64: AIOS Engine Preemptive Scheduling, Priority Gating & DCI Structured Deliberation. -->
# <a name="64_engine_preemptive_scheduling_and_dci_deliberation"></a>Chapter 64: AIOS Engine Preemptive Scheduling, Priority Gating & DCI Structured Deliberation

> Part II: The Agentic AI Stack of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#64_engine_preemptive_scheduling_and_dci_deliberation`

#### Overview

Local AI operating systems must balance concurrent demands: real-time user-interactive chat, high-throughput IDE code completions, continuous background log analysis, and deep multi-agent deliberation.

Governed by ADR-0019, `WS-SCHED`, and `WS-ORCH`, MiOS implements **Engine-Level Priority Scheduling**, **Token-Boundary Preemption**, and **Consequentiality-Gated Deliberation**.

#### <a name="64_priority_scheduling_preemption"></a>64.1 Priority Tiers & Token-Boundary Preemption

`agent-pipe` (`:8640`) classifies incoming inference requests into three distinct priority classes:
1. **Interactive Tier** (`Priority: 100`): User chat, UI actions, real-time command dispatch.
2. **Batch Tier** (`Priority: 50`): Code generation, document indexing, synthetic dataset generation.
3. **Background Tier** (`Priority: 10`): Log surveillance, memory compaction, ambient reflection.

When an interactive request arrives and GPU VRAM / compute capacity is saturated:
* `agent-pipe` emits a `_CHAT_CANCEL` signal at the nearest token boundary to active background turns.
* The background worker's KV cache slot is serialized to `/var/lib/mios/llamacpp/slots/<task_id>.bin` via `mios_kvfork.py`.
* VRAM is allocated immediately to the interactive turn.
* Upon completion, the background task's KV cache is paged back into VRAM and decoding resumes seamlessly.

#### <a name="64_consequentiality_gated_dci"></a>64.2 Consequentiality-Gated Deliberative Collective Intelligence (DCI)

Heavyweight multi-agent deliberation consumes $\sim 62	imes$ tokens compared to single-agent execution and degrades simple queries. MiOS implements model-driven consequentiality gating:
* **High-Impact Mutations**: System configuration changes, security policies, partition resizing, and large codebase refactors trigger 4-archetype DCI debate:
  * **Framer**: Establishes boundaries, problem statements, and constraints.
  * **Explorer**: Proposes architectural solutions and candidate implementations.
  * **Challenger**: Attacks proposals, uncovers failure modes, and asserts security invariants.
  * **Integrator**: Synthesizes consensus and generates the final **Decision Packet** (action plan, residual caveats, minority report).
* **Routine / Read-Only Queries**: Bypass deliberation entirely and route directly to single-agent execution with greedy decoding.

#### <a name="64_progressive_retrieval_loo"></a>64.3 Progressive Disclosure & IntrospecLOO Evaluation

* **Manifest-Guided Retrieval**: Large codebase trees are organized into hierarchical manifests walked by LLM selection, complementing flat vector similarity search.
* **IntrospecLOO Scoring**: Evaluates each participating agent's marginal contribution without re-running debate rounds, updating the persistent reputation table in PostgreSQL.
