# Antigravity Workflow: /workflows:goal

Identifier: `goal`
Purpose: Goal-directed autonomous engineering with stopping conditions.

1. **Phase 1: Goal Anchoring:** Parse objective; write `GOALS.md` and `tasks.jsonl`.
2. **Phase 2: Execution Heartbeat:** Launch isolated worktrees under `.worktrees/`.
3. **Phase 3: Condition Evaluation:** Execute `goal.py eval`. If failed, diagnose phantoms and repeat.
4. **Phase 4: Reconciliation:** Run pre-merge test gate, atomic merge, and cleanup.
