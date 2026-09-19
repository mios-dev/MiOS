# Upstream Dependency & Pattern Audit — Dev-Loop Architectures

**Audit ID:** `UPSTREAM-DEVLOOP-2026-09`  
**Package / Component:** `dev-loop` Multi-Harness Autonomous Engineering Loop  
**Upstream Repositories / Sources:**
- Agent Skills Open Standard ([agentskills.io](https://agentskills.io), 2025-12, Agentic AI Foundation)
- [`nwiizo/ccswarm`](https://github.com/nwiizo/ccswarm) (`1cec7fe72886b2fffc4424637350f28f3130e6b4`)
- [`mraza007/baton`](https://github.com/mraza007/baton) (`7bb5fb73c08f31d897b7b64e85b3247a0292eebd`)
- [`ai-boost/awesome-harness-engineering`](https://github.com/ai-boost/awesome-harness-engineering) (`fa3275de3db67ccf7f0c84912af6ea27f3d3719e`)
- Claude Code CLI Reference (`v2.1.278`) & Antigravity CLI Reference (`v1.2.6`)
**Audit Date:** 2026-09-19  
**Auditor:** Antigravity AIOS Pair Assistant  
**DevLoop Telemetry:** `.devloop/research_devloop_patterns.json`  

---

## 1. Executive Summary & Architecture Verdict
- **Verdict:** `UPGRADE_WITH_MIGRATION`
- **Risk Level:** `LOW`
- **Summary:** Upstream 2026 autonomous engineering architectures have converged on a deterministic control plane wrapped around stochastic LLM worker harnesses. State lives strictly on disk (the Ralph pattern) rather than inside model context. Isolated git worktrees serve as the universal execution boundary, and task queues (issues/tasks) drive scheduling. MiOS dev-loop's key differentiator is the host-enforced two-sided verification gate (positive control + negative planted mutation) with automated base-tree leakage guards.

---

## 2. Upstream Pattern Breakdown & Convergence Points

### 2.1 Orchestrator–Worker Topology (L0 / L1 / L2)
* **Upstream Standard (`ccswarm`, Modern Agent Harness Blueprint):** Master orchestrators decompose specifications, own shared repository state, and dispatch narrow briefs to specialist worker lanes. Workers return only structured JSON envelopes and artifact paths.
* **Adoption in Dev-Loop:** 
  - `L0 Host / Orchestrator`: Owns `AGENTS.md`, `TASKS.md`, worktree provisioning, merge gates, and `.devloop/LEDGER.md`.
  - `L1 Supervisor`: Domain auditing (`role: auditor`), schema drift validation.
  - `L2 Worker (Lane)`: Dedicated git worktree, exclusive `owned_paths`, two-sided gate, structured report (`report-<id>.json`).

### 2.2 Worktree Isolation & Git Index Safety
* **Upstream Standard (`baton`, `ccswarm`, Sandcastle):** Every worker executes in an isolated `git worktree` (`base_ref = HEAD`), preventing concurrent checkout collisions.
* **Critical Finding & Patch:** Root-walking repo linters (such as `tools/drift-checks.py`) walk into `.worktrees/` unless explicitly pruned, multiplying violations by $N+1$ live workers and causing planted negative test fixtures to leak into host checks. Upstream best practice mandates strict exclusion of `.worktrees/` and `.devloop/run-*/` from all file-walking gates.

### 2.3 On-Disk State Machines & Context Resets (The Ralph Pattern)
* **Upstream Standard (Addy Osmani, "Agent Harness Engineering"):** Context windows degrade over multi-turn sessions. The orchestrator resets worker context between task waves, re-injecting fresh instructions and reading all persistent state from disk (`.devloop/LEDGER.md`, `.devloop/tasks.jsonl`).

### 2.4 Multi-Harness Worker Execution (`claude -p` & `agy -p`)
* **Flag Surface Drift Audit:**
  - **Claude Code CLI (`claude` v2.1.278):** `--max-turns` was deprecated/removed by 2.1.276. Turn budgets are now governed by process timeouts and `--max-budget-usd`. Uses `--output-format json`, `--permission-mode dontAsk`, and `--json-schema` for structured reporting.
  - **Antigravity CLI (`agy` v1.2.6):** Employs `--output-format json`, `--print-timeout`, `--dangerously-skip-permissions`, and model slugging (`gemini-3.8-flash-high`).
  - **Process Lifetime Invariant:** Background shell dispatches kill child processes when headless managers exit. Upstream requires foreground setsid/daemon execution (`job.py`) or session management (`agy_session.py`).

### 2.5 Two-Sided Verification ("Verify, Don't Believe")
* **Dev-Loop Innovation:** Uniquely combines positive controls (exit code 0) with diff-scoped mutation testing (`mutmut`, `cargo mutants`) and planted negative-control sentinels (`DEVLOOP-PLANTED-<LANE_ID>`). If a planted mutation does not trigger a deterministic test failure, the check is classified as a *Self-Certifying Predicate* or *Check That Cannot Fail* and rejected.

---

## 3. Invariant & Contract Verification

| Invariant | Requirement | Verification Mechanism | Status |
| :--- | :--- | :--- | :--- |
| **Base Tree Immutability** | Manager and worker runs must never write to base checkout during worktree execution. | Automated pre/post `git status --porcelain` check; hard abort with exit code 6 on stray mutations. | **Verified** (E2E Tier 1) |
| **Index Lock Isolation** | Concurrent worker git operations must not contend on `.git/index.lock`. | Backoff retries in `git_lock.py` + dedicated worktree index files. | **Verified** (E2E Tier 3) |
| **Gate Non-Vacuity** | Negative controls must fail only for the planted reason. | Unique sentinels (`DEVLOOP-PLANTED-<LANE_ID>`) with clean restoration via copy-back trap. | **Verified** (`test_planted_naming.py`) |
| **Harness Agnosticism** | Identical task definition executable across Claude Code and AGY. | Agent Skills open standard schema (`lanes.json` -> `adapters.py`). | **Verified** (Dual CLI probe) |

---

## 4. Local Implementation & Evolution Plan

1. **Phase 1 (Isolation Hardening — Active in Teamwork Track):**
   - Finalize `tests/test_e2e_lane_isolation.py` (40/40 tests passing).
   - Ensure all `drift-checks.py` root-walking checks prune `.worktrees/`.
   - Remediate `mios_worktree.py` to merge via isolated ephemeral trees rather than base checkout.

2. **Phase 2 (Continuous Scheduling — Active in Campaign Track):**
   - Automatically ingest tasks from `TASKS.md` into dependency-sorted `lanes.json` manifests.
   - Schedule concurrent worker lanes across Claude Code CLI (`claude -p`) and AGY (`agy -p`).

3. **Phase 3 (Durable Handoffs):**
   - Commit atomic `--no-ff` merges with `Task-Id: <ID>` trailers.
   - Persist cycle ledger records to `.devloop/LEDGER.md` with zero context memory dependencies.

---

## 5. Unverified / Open Spikes
- **Windows / WSL Index Locking:** Git index locking behavior under concurrent NTFS/9P filesystem bridges requires a real Windows host probe (currently verified on Linux overlayfs).
- **Subagent Depth Limits:** Claude Code CLI nested subagent limits (default depth 3) under headless `--json-schema` invocation require benchmarking under large refactor waves.
