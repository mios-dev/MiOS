---
name: agy-subagents
description: Multi-Subagent Orchestrator for Antigravity CLI (AGY) in MiOS Development
tools: ['read', 'edit', 'search', 'shell']
---

# Antigravity Multi-Subagent Orchestrator

Coordinates specialized subagents declared in `.agents/subagents.json`:
- **`pipeline-auditor`**: Scans standing gates, ratchet ceilings, and secret literals.
- **`pipeline-worker`**: Implements core Linux OS features, static Rust binaries, and FHS overlays.
- **`pipeline-reviewer`**: Audits two-sided test controls and performs SCOPE staged reviews.
- **`artifact-publisher`**: Synchronizes SSOT projections and publishes release metadata.
- **`pipeline-orchestrator`**: Manages isolated git worktree lanes and task convergence.
