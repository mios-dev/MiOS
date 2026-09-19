# OpenCode /goal Command

Autonomous goal-oriented engineering workflow:
1. When called as `/goal dev <objective>`, establish stopping criteria in `GOALS.md`.
2. Decompose into worktree tasks.
3. Run iterations until all tests, invariants, and manifest hashes pass.
4. Merge cleanly with `git merge --no-ff`.
