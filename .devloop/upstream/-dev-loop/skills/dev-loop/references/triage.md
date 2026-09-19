# Phantom-Failure Triage Specification (`/triage`, `/tr`)

The Triage suite isolates phantom environment failures, detects test flakiness, and generates standalone reproduction harnesses to prevent agent loops from hallucinating code changes on external failures.

---

## 1. Failure Categories

1. **`INDEX_LOCK`**: Git repository index contention (`.git/index.lock`). Trigger backoff and purge locks.
2. **`RESOURCE_STARVATION`**: Exhaustion of memory, disk space, or process limits. Trigger worktree cleanup.
3. **`FLAKY_TEST`**: Test returns varying exit codes across consecutive runs. Flags timing races or async leaks.
4. **`DETERMINISTIC_BUG`**: Consistent code bug across all runs. Auto-generates `repro.sh` minimal reproduction script.

---

## 2. Execution CLI

```bash
# Analyze a failing test command over 3 iterations
python3 scripts/triage.py "pytest tests/unit" --runs 3

# Scaffold a formal incident investigation report
python3 scripts/triage.py --init
```
