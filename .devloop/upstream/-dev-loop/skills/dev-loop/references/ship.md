# Safe Trunk Shipping & Worktree Reconciliation Specification (`/ship`, `/sh`)

The Ship engine automates final branch reconciliation, pre-flight gate verification, atomic merges into `main`, worktree pruning, and `CHANGELOG.md` updates.

---

## 1. Shipping Protocol

1. **Pre-Flight Verification:** Ensures all test suites pass, zero uncommitted changes exist, and `/review` reported zero blockers.
2. **Atomic Merge:** Executes `--no-ff` merge or rebase into target trunk branch, with immediate conflict abort on failure.
3. **Changelog Automation:** Adds a structured entry under `[Unreleased]` in `CHANGELOG.md`.
4. **Worktree Pruning:** Runs `git worktree prune` and deletes ephemeral local lane branches.

---

## 2. Execution CLI

```bash
# Ship lane-backend into main
python3 scripts/ship.py lane-backend --target main --tag v1.4.0

# Scaffold release checklist
python3 scripts/ship.py --init
```
