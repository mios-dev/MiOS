# Project: Dev-Loop Lane Isolation & Concurrent Worker Harness

## Architecture
The dev-loop orchestration harness coordinates autonomous AI coding agents across multiple harnesses (Antigravity/AGY, Claude Code CLI `claude -p`, Codex, OpenCode, Copilot, Cursor).
The core system architecture consists of:
1. **Execution Engine & Multi-Lane Orchestration (`devloop.sh`, `DevLoop.ps1`)**:
   Manages the lifecycle of worker lanes, partitioning tasks into dependency waves (`adapters.py waves`), provisioning isolated git worktrees (`<worktree_root>/<id>`), launching concurrent jobs via detached supervisor (`job.py spawn`), executing sequential pre-merge verification gates (`gate_merge`), and atomically reconciling git commits (`--no-ff`).
2. **Harness Adapters & Gating Engine (`adapters.py`)**:
   Synthesizes execution commands (`build_argv`) for diverse CLI agents, prepares isolated prompt contracts, and executes two-sided verification gates (`positive_cmd` and `negative_control_cmd`). Validates path ownership (`cmd_owned`), detects tool permission denials (`cmd_denials`), and enforces supply-chain / security scans.
3. **Base-Tree State Guard & Leakage Enforcement (`adapters.py`, `agy_session.py`, `devloop.sh`)**:
   Enforces absolute immutability of the base git repository. Captures baseline `git status --porcelain` snapshots prior to execution and ensures that only designated metadata paths (`.devloop/`, `.git/`, `AGENTS.md`, `TASKS.md`, `<worktree_root>/`) can ever be modified in the base working tree. Halts execution immediately with diagnostic error reporting if stray files or fixture leaks are detected.
4. **Git Lock & Concurrency Manager (`git_lock.py`, `adapters.py:git`)**:
   Resolves git directories for primary and linked worktrees, arbitrating concurrent git operations with exponential backoff, jitter, and stale lock eviction (>45s) to eliminate index lock contention.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Worktree Layout Isolation | Enforce worker and manager isolation within dedicated git worktrees under `<worktree_root>/<id>` with narrow `.git/info/exclude` | M1 | R1, Survey §1.1 |
| 2 | Clean Worktree Provisioning | Fix worktree reuse bug in `devloop.sh` to clean/reset existing worktrees before lane execution | M1 | R1, Survey §1.1 |
| 3 | Prompt & Dispatch Alignment | Update `manager.md` and `dispatch.*.md` to eliminate unisolated subagent fictions and mandate dedicated worktrees | M1 | R1, Survey §1.2 |
| 4 | Base-Tree Snapshot Protocol | Implement pre- and post-execution snapshotting (`base_tree_state`) in `adapters.py` and `devloop.sh` | M2 | R2, Survey §1.2 |
| 5 | Two-Sided Gate Base-Tree Audit | Enforce base-tree immutability inside `adapters.py:cmd_gate`; halt with exit 2 on stray modifications outside allowed metadata paths | M2 | R2, Survey §1.2 |
| 6 | Orchestrator Pre/Post Leak Audit | Implement automated pre/post execution audits in `devloop.sh` halting with non-zero exit on stray files | M2 | R2, Survey §1.2 |
| 7 | Diagnostic Stray Path Reporting | Report exact stray file paths on stderr when base tree leakage is detected | M2 | R2, Survey §1.2 |
| 8 | Fail-Closed Session Guard | Enforce immediate fail-closed termination in `agy_session.py` when base tree mutations are detected | M2 | R2, Survey §1.2 |
| 9 | Concurrent Detached Execution | Enable parallel detached worker job spawning (`job.py spawn`) across waves for headless and multi-lane runs | M3 | R3, Survey §1.3 |
| 10 | Claude Code CLI Worker Harness | Full production support for `claude -p` workers with `cwd=wt`, JSON envelope, schema validation, and tool allowlists | M3 | R3, Survey §1.3 |
| 11 | Concurrent Worktree Index Isolation | Ensure zero index lock contention during concurrent worker builds and gate runs via worktree-specific index files and `git_lock.py` backoff | M3 | R3, Survey §1.3 |
| 12 | Atomic Diff Reconciliation | Reconcile diffs sequentially via two-sided gate, path ownership audit, and `--no-ff` merge with instant conflict abort | M3 | R3, Survey §1.4 |
| 13 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box test suite covering worktree isolation, stray leakage detection, and concurrent Claude Code/AGY spawning | E2E | Acceptance Criteria |
| 14 | Adversarial Hardening (Tier 5) | White-box stress testing of edge cases, rapid lock contention, dirty baselines, and nested negative controls | M4 | Project Pattern |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven test suite (Tiers 1-4) covering R1, R2, R3, and publishing `TEST_READY.md` | none | DONE |
| M1 | Strict Worktree Isolation | Enforce worktree provisioning, sanitization, and prompt alignment for all manager and worker runs | none | DONE |
| M2 | Leakage Detection & Enforcement | Implement base-tree snapshotting, two-sided gate leakage audit in `adapters.py`, orchestrator audits in `devloop.sh`, and diagnostic error reporting | M1 | DONE |
| M3 | Concurrent Worker Lanes & Claude Code CLI | Multi-lane concurrent spawning via `job.py`, Claude Code CLI (`claude -p`) harness verification, and atomic diff reconciliation | M1, M2 | DONE |
| M4 | Final Milestone & Hardening | Pass 100% of E2E tests (Tiers 1-4) and adversarial coverage hardening (Tier 5) | E2E, M3 | DONE |

## Interface Contracts
### `adapters.py` ↔ `devloop.sh`
- `adapters.py base-audit --root <root> --before <snapshot_file> [--lanes <lanes_json>]`:
  - Returns exit code 0 if base tree has no modifications outside allowed metadata paths (`.devloop/`, `.git/`, `AGENTS.md`, `TASKS.md`, `<worktree_root>/`).
  - Returns exit code 6 if stray modifications or untracked files exist, outputting the newline-delimited list of stray paths to `stderr`.
- `adapters.py gate --lane <lane_json> --wt <worktree_dir> --run <run_dir> [--root <base_root>]`:
  - Executes positive and negative controls.
  - Takes snapshots of both worktree (`wt`) and base repository (`root`).
  - Verifies worktree restoration and asserts base repository has zero stray edits.
  - If stray edits exist in base repository: outputs `BASE TREE LEAKAGE DETECTED: <paths>` to stderr and exits with code 2.

### Harness Runner ↔ Claude Code CLI (`claude-code`)
- Invocation:
  `claude -p "{prompt}" --output-format json --permission-mode dontAsk --allowedTools "{allowed_tools}" --model "{model}" --effort "{effort}" --json-schema "{schema}"`
- Working Directory: `cwd=wt` (must run strictly within allocated `<worktree_root>/<id>`).
- Output parsing: Extracts `devloop_report` JSON; checks `permission_denials` and downgrades status to `partial` if non-empty.

## Code Layout
- Dev-loop core harness:
  - `/home/mios-dev/.dev-loop/skills/dev-loop/scripts/`
    - `adapters.py`: Universal adapter and CLI subcommands
    - `devloop.sh`: Multi-lane bash orchestrator
    - `agy_session.py`: Antigravity session manager and base tree monitor
    - `agy_host.sh`: Antigravity host launcher
    - `job.py`: Detached process runner
    - `git_lock.py`: Git concurrency and lock helper
  - Mirrored under `/home/mios-dev/.gemini/config/skills/dev-loop/scripts/`
- Test suites:
  - `/home/mios-dev/.dev-loop/tests/`: Harness unit and integration tests
  - `/workspaces/MiOS/tests/`: Project E2E and CI test suites
  - `/workspaces/MiOS/tools/`: Project tools and test suites
