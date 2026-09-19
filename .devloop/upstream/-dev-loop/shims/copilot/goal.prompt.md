---
name: goal
description: Goal-driven engineering workflow with strict stopping conditions
version: 2.0.0
---

# GitHub Copilot /goal Workflow

When invoked with `/goal dev <objective>`:
- **Anchoring:** Establish testable stopping conditions and non-goals in `GOALS.md`.
- **Iteration:** Execute the Dev Loop heartbeat across worktrees until all acceptance invariants are satisfied.
- **Verification:** Confirm positive and negative test controls. Verify manifest hashes in `.devloop/`.
