<!-- AI-hint: Technical reference for the MiOS agentic routing and orchestration decision seams. -->
---
title: Agentic Routing and Orchestration Seam Reference
description: Consolidated reference documenting pure decision seams, owning routing modules, SSOT configuration parameters, and degrade-open postures in MiOS agent-pipe.
type: reference
---

# Agentic Routing and Orchestration Seam Reference

## Overview

The MiOS Agent Pipe orchestrates incoming completions requests across an extensible swarm of localized and remote model endpoints. Routing and execution decisions pass through a sequence of pure decision seams, each managed by a dedicated routing module in `usr/lib/mios/agent-pipe/mios_pipe/routing/`.

Every decision seam is governed by Single Source of Truth (SSOT) configuration parameters defined in `usr/share/mios/mios.toml` under `[agent_pipe]`, `[dispatch]`, `[agent_pipe.council]`, and `[agent_pipe.quality]`. All seams implement a fail-open (degrade-open) posture to ensure system availability if an individual component or threshold evaluation encounters unexpected inputs or failures.

---

## Orchestration Seam Matrix

| Decision Seam | Owning Module | SSOT Configuration Knobs | Degrade-Open / Fallback Posture |
| :--- | :--- | :--- | :--- |
| **Request Classification & Intent Routing** | `router.py` / `smartroute.py` | `[routing.domains]`, `[routing.phrases]`, `[agent_pipe.quality]` | Unmapped intent or classification error defaults to primary agent dispatch without custom filters. |
| **Swarm Dispatch & Fan-out Governor** | `dispatcher.py` / `fanout.py` | `[dispatch].default_hop_budget`, `[dispatch.autonomy].max_dispatch_depth` | Budget exceeded or invalid hop header halts further recursion and executes single-node completion. |
| **Swarm Parallel Topology & Width Bounding** | `swarm.py` / `dag_exec.py` | `[dispatch].swarm_max_width`, `[dispatch].swarm_max_cpu_nodes` | Exception during graph resolution truncates secondary fan-out and proceeds with primary grounded nodes. |
| **Council Secondary Roster Selection & Diversity** | `council_diversity.py` | `[agent_pipe.council].diversity_gate`, `diversity_threshold`, `aggregator_bypass`, `aggregator_bypass_threshold` | Invalid diversity score or threshold evaluation bypasses secondary filtering and admits default roster. |
| **Hop Budget & Wall-Clock/Replan Governance** | `hopbudget.py` / `toolexec.py` | `[agent_pipe].tool_max_iters`, `replan_max`, `no_progress_window`, `max_consecutive_failures`, `wall_clock_budget_s` | Budget exhaustion terminates iterative loop cleanly, returning current partial/last-known response. |
| **Cross-Provider Wire Translation & Escalation** | `provider_translate.py` / `remote_adapter.py` | `[nodes.*].api`, `[ai].remote_escalation` | Unset or unrecognized provider API passes request/response body through unchanged (Passthrough). |

---

## Seam Details and Architectural Constraints

### 1. Intent Classification & Router Seam (`router.py`, `smartroute.py`)
- **Responsibility:** Maps incoming chat completion prompts and tools to target execution domains.
- **SSOT Knobs:** `[routing.domains]`, `[agent_pipe.quality.eval_pass_rate_floor]`.
- **Degrade-Open:** If embedding or rule lookup fails, the router degrades open by forwarding to the default heavy backend model.

### 2. Dispatcher & Recursion Bounds (`dispatcher.py`, `fanout.py`)
- **Responsibility:** Controls sub-agent delegation depth and prevents multi-hop infinite recursion loops.
- **SSOT Knobs:** `default_hop_budget = 2` (`[dispatch]`), `max_dispatch_depth = 2` (`[dispatch.autonomy]`).
- **Degrade-Open:** Hop budget counters automatically clamp at max depth, preventing downstream child dispatches.

### 3. Swarm Fan-Out & Concurrency (`swarm.py`, `dag_exec.py`)
- **Responsibility:** Schedules concurrent node execution across GPU and CPU lanes while protecting VRAM and thread headroom.
- **SSOT Knobs:** `swarm_max_width = 3` (`[dispatch]`), `swarm_max_cpu_nodes = 2` (`[dispatch]`).
- **Degrade-Open:** Excess requested nodes beyond width caps are queued or dropped, ensuring grounded primary execution continues.

### 4. Council Diversity & Gatekeeper (`council_diversity.py`)
- **Responsibility:** Filters candidate secondary council models based on semantic diversity to prevent response redundancy.
- **SSOT Knobs:** `[agent_pipe.council]` (`diversity_gate`, `diversity_threshold`, `aggregator_bypass`, `aggregator_bypass_threshold`).
- **Degrade-Open:** Gate failure or missing metric fallback permits all active candidates or bypasses council evaluation.

### 5. Iterative Execution & Loop Budgets (`toolexec.py`, `hopbudget.py`)
- **Responsibility:** Governs tool loop iterations, replan attempts, and wall-clock safety windows.
- **SSOT Knobs:** `[agent_pipe]` (`tool_max_iters`, `replan_max`, `no_progress_window`, `max_consecutive_failures`, `wall_clock_budget_s`, `reflexion_enable`).
- **Degrade-Open:** Timer or iteration limit triggers graceful turn completion instead of hard process termination.

### 6. Provider Adaptation & Wire Translation (`remote_adapter.py`, `provider_translate.py`)
- **Responsibility:** Translates OpenAI-formatted requests into provider-native payloads (e.g. Anthropic, Gemini) for remote node escalation.
- **SSOT Knobs:** `[nodes.*].api`, `[ai].remote_escalation`.
- **Degrade-Open:** Standard OpenAI endpoints or unconfigured API tags pass through standard HTTP payload format without mutation.
