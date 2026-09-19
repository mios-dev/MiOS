# e2e: mixed AGY + Claude Code lanes

Proves the whole mixed-lane path on a real, throwaway repo: two seeded bugs,
one **Antigravity** lane (`agy -p`) and one **Claude Code** lane (`claude -p`)
in parallel git worktrees, host-run two-sided gates, `--no-ff` merges, and the
integration command on the merged base.

```sh
sh tests/e2e-mixed-lanes/setup-sandbox.sh     # builds <repo>/.sandbox-e2e, verifies seeds FAIL
```

Then run one (or both) of the printed commands:

- **A — direct orchestrator** (any host drives `devloop.sh`): validates lane
  plumbing, adapters, gates, merge.
- **B — AGY as L0 manager** (`agy_host.sh … --session`): the full
  topology-A test — Antigravity manages all sub-agents and dispatches the same
  lane file itself. `--session` and not `--headless`: single-turn print mode forbids
  native subagents, because the process exits when the turn ends and takes any
  unfinished subagent with it.

Success criteria (both modes): exit 0; `git -C .sandbox-e2e log --oneline`
shows both `lane(...)` merges; `.devloop/run-*/report-*.json` has
`status: done` with the negative control matched; the integration command
passes on `main`.

Prerequisites: `agy` installed **and authenticated** (`scripts/env/agy-login.sh`),
`claude` on PATH and authenticated, keyring live (`scripts/env/agy-doctor.sh`).
Each run costs a handful of small model calls.

Lessons this fixture already taught (kept so they stay learned):

- Seed verification matters: the script fails if the seeded tests already
  pass, otherwise every lane would no-op and the e2e would be vacuous.
- `__pycache__/` from the seed check dirties the tree and `devloop.sh`
  (correctly) refuses to start — the sandbox ships a `.gitignore`.
- A lane's `allowed_tools` must cover its own `negative_control_cmd`: scoped
  `Bash(python3:*)` does not match the compound `trap …; printf …` control, so
  the worker self-reports `blocked` and is never merged. Lanes here get plain
  `Bash`; the worktree is the fence.
- Negative controls must restore by **copy-back** (`cp f .nc.bak; trap 'mv
  .nc.bak f' EXIT`), never `git checkout -- f`: checkout restores from the
  index, and the lane's fix is uncommitted at host-gate time, so the trap
  replaced the fix with the seeded bug and the gate (correctly) refused with
  "did not restore the tree". The gate now parks the pre-control diff so a
  broken control can no longer destroy the evidence.
