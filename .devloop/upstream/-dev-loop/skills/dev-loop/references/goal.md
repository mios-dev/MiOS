# Dev Loop Goal Engine Specification (`/goal` & `/goal dev`)

The Goal Engine couples continuous execution loops with explicit, verifiable stopping conditions.

---

## 1. The Core Paradigm: Heartbeat + Stopping Condition

In autonomous agentic engineering:
- **`/dev-loop` (or `/loop`):** Provides the **heartbeat** — iteratively polling, pulling updates, spawning worktrees, making edits, running test suites, and handling merge gates.
- **`/goal` (or `/goal dev`):** Provides the **stopping condition** — defining the acceptance invariants that must hold true before the agent is permitted to conclude its autonomous work.

```
       +---------------------------------------------+
       |   /goal dev "Migrate Auth to OAuth2 OIDC"    |
       |   - Stopping Condition: All 45 tests green  |
       |   - Positive Control: OAuth2 login passes   |
       |   - Negative Control: Bad token rejected    |
       |   - Invariant: Manifest SHA-256 verified    |
       +----------------------+----------------------+
                              |
                              v
                  [Initialize GOALS.md]
                  [Decompose tasks.jsonl]
                              |
+-----------------------------v-----------------------------+
|                     The Execution Loop                    |
|                                                           |
|    1. Provision Worktree per task                         |
|    2. Precision Edit (Atomic .tmp -> mv)                  |
|    3. Evaluate Stopping Condition (goal.py eval)          |
|         - If FAILED -> Continue iteration turn            |
|         - If PASSED -> Proceed to Reconcile               |
|    4. Reconcile & Atomic Merge (--no-ff)                  |
|    5. Register Manifest & Explicit Commit                 |
+-----------------------------+-----------------------------+
                              |
                              v
                [Goal Status: COMPLETED]
                [Autonomous Loop Terminated]
```

---

## 2. The `/goal dev` Command

When invoking `/goal dev <objective>`, the agent executes the complete goal-driven development lifecycle:

1. **Goal Initialization:**
   - Evaluates the objective and formulates concrete, testable criteria in `GOALS.md`.
   - Defines explicit non-goals to establish blast radius bounds.
2. **Task Decomposition:**
   - Translates criteria into a dependency DAG in `tasks.jsonl`.
3. **Execution Heartbeat:**
   - Launches `devloop_worker.py` across isolated worktrees.
4. **Stopping Condition Enforcement:**
   - The loop will not stop prematurely. It continuously evaluates `goal.py eval` until every invariant is satisfied.
5. **Verified Teardown:**
   - Merges worktrees, cleans branches, generates the final audit report in `.devloop_reports/`, and reports completion to the operator.
