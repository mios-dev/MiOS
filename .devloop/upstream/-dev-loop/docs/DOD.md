# Definition of Done (project default; a task may tighten, never loosen)

A change is done when ALL hold, with evidence recorded in the task's `verification_evidence` and the lane report:

- [ ] Objective stated in one observable sentence; scope and non-goals listed (task `acceptance_criteria`, EARS or Given/When/Then).
- [ ] Positive control: `<gate command>` exits 0 on the finished tree.
- [ ] Negative control: a planted violation fails and the output NAMES the planted thing; the control restores the tree.
- [ ] Full project gate run once, exactly as CI runs it.
- [ ] No new suppressions, widened types, loosened assertions, raised thresholds, or deleted tests (or the commit proves the test was wrong).
- [ ] Explicit-path staging; secrets scan clean; supply-chain audit clean if a lockfile changed.
- [ ] Docs/ADR/CHANGELOG updated when behaviour, interface, or a decision changed.
- [ ] `.devloop/tasks.jsonl` status flipped; `Task-Id:` trailer on the commit; handoff note in `.devloop/LEDGER.md` if the session ends before the task does.
- [ ] Anything NOT verified is listed under `unverified` in the report.
