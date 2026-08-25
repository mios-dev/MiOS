<!-- AI-hint: Defines engine-level priority preemption and consequentiality-gated Deliberative Collective Intelligence (DCI). -->
<!-- AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_sched.py, usr/lib/mios/agent-pipe/mios_dci.py, usr/share/mios/mios.toml [dispatch], [ai.lanes] -->
---
adr: 0019
title: "Preemptive context switching, priority scheduling, and consequentiality-gated deliberation"
status: accepted
date: 2026-08-25
deciders: [operator, ai-pair]
tags: [scheduling, preemption, kv-cache, deliberation, dci, looeval, inference]
laws: [2, 5, 8, 12]
ssot_keys: [dispatch.tenants, tools.execution, ai.models, ai.lanes]
related_ws: [WS-SCHED, WS-ORCH, WS-AI]
supersedes: []
superseded_by: []
---

# ADR-0019: Preemptive context switching, priority scheduling, and consequentiality-gated deliberation

## Status

**Accepted.** Settles AIOS kernel scheduling preemption mechanics and DCI deliberation activation gating.

## Context

MiOS operates multiple concurrent AI inference workloads across interactive operator requests, IDE completions, background batch indexing, autonomous daemon monitoring, and multi-agent deliberation rounds.

On resource-constrained local GPU hardware, background agent turns can monopolize VRAM and compute lanes, causing unacceptably high time-to-first-token latency for user-facing interactive queries. Furthermore, invoking heavyweight multi-agent deliberation on simple read queries introduces unnecessary token overhead and delay.

## Decision

### 1. Priority-Gated Preemptive Context Switching
`agent-pipe` implements strict priority tiers (`interactive > batch > background`):
* Interactive requests propagate high-priority HTTP headers (`X-MiOS-Priority: 100`) to inference engines.
* When GPU capacity is saturated, `agent-pipe` issues a `_CHAT_CANCEL` signal at the nearest discrete token/turn boundary to lower-priority background tasks.
* The background task's active KV cache slot is dumped to disk (`/var/lib/mios/llamacpp/slots/<task_id>.bin`), its status marked `suspended` in PostgreSQL, and GPU memory allocated immediately to the foreground turn.
* Once the high-priority turn completes, the background KV cache is paged back into VRAM and generation resumes seamlessly.

### 2. Consequentiality-Gated Deliberation Activation
Structured Deliberative Collective Intelligence (DCI) multi-agent debate is triggered dynamically based on task consequentiality:
* **High-Impact Mutations** (system configuration, security policy, partition resizing, large code refactoring): Automatically activate 4-archetype DCI debate (Framer, Explorer, Challenger, Integrator) with formal tension tracking and IntrospecLOO evaluation.
* **Low-Impact / Read-Only Inquiries**: Direct single-agent turn execution with greedy decoding, minimizing latency and compute token consumption.

### 3. Progressive Disclosure Retrieval
Context retrieval utilizes hierarchical manifest matching:
* Fast vector similarity over high-level component manifests narrows search scope before pulling detailed code files and AST triples.
* Re-ranking using a local cross-encoder (`bge-reranker-large`) ensures high precision@5 retrieval before prompt injection.

## Rationale

Preemptive GPU scheduling ensures sub-second interactive latency for human operator requests while allowing background agentic reflection and distillation to run continuously on host hardware.

## Consequences

- Interactive user turns achieve sub-second response times even under heavy multi-agent background loads.
- Multi-agent deliberation is reserved for high-stakes operational decisions, maximizing compute efficiency.
