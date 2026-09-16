<!-- AI-hint: The project default Definition of Done for MiOS, grounded in this repo's actual gates. A task may tighten it, never loosen it. Write the task-specific DoD BEFORE the code. -->
<!-- AI-related: AGENTS.md, CLAUDE.md, TASKS.md, docs/design/operating-agreement.md, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh -->
# Definition of Done (project default)

A change is done when ALL of these hold, with the evidence recorded in the commit message.

## Verification

- [ ] Objective stated in one observable sentence; scope and non-goals listed.
- [ ] **Positive control** — the exact command, exit 0, on the finished tree.
- [ ] **Negative control** — a planted violation FAILS and the output names *the thing planted*,
      not something adjacent. The control restores the tree (`git status --porcelain` equals its
      pre-control value).
- [ ] **A degenerate diff is not parity.** When the shipped SSOT makes a renderer take its
      do-nothing path, a matching diff proves only that both implementations agree on doing
      nothing. Plant a realistic non-default value in a COPY of the SSOT and diff again.
- [ ] **Full gate run once**, exactly as CI runs it, and the violation count compared to the
      standing baseline **by check name**, not by total.
- [ ] Anything NOT verified is stated plainly in the commit message.

## This repo's actual gates

| Gate | Command | Meaning |
|---|---|---|
| Drift gate | `bash automation/98-drift-checks.sh` | The release gate. Baseline is **20 violations from seven standing-red checks**; compare the SET, not the number. |
| Negative suite | `bash tests/drift-gate-negatives.sh` | Proves each check CAN fail. Baseline is **8 failures, identical on `origin/main`** — a ninth is yours. |
| Generators | `bash tools/sync-generated.sh` | Must be idempotent: a second run produces zero diff. **`git add` the new files BEFORE syncing** — the manual-corpus census reads the git index, not the worktree. |
| Shell | `bash automation/lint-shell.sh` | Modified scripts are graded at *warning* level, so a pattern 66 stages share becomes a violation the moment you touch one of them. |
| Rust | `cd src/mios-rs && cargo fmt --all --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace` | Same for `tools/native` (`--exclude mios-wallpaperd`). |
| Resolver parity | `python3 tools/drift-checks.py resolver-differential-parity` | **Build `mios-resolver` first.** It "advisory skips" and exits 0 when the binary is absent, so a local gate run reports green while never comparing the resolvers. |

## Must not

- [ ] No new suppressions, widened types, loosened assertions, **raised ratchet ceilings**, or
      deleted tests — unless the commit proves the test was wrong.
- [ ] A ratchet ceiling left ABOVE its measurement is also a violation: that slack is where the
      next regression hides.
- [ ] No `git add -A` / `.` / `-u`. Explicit paths, then read `git diff --cached --stat`.
- [ ] Secrets scan before every commit.

## Record

- [ ] Docs / ADR / task status updated when behaviour, interface, or a decision changed.
- [ ] Commit message carries the reasoning — in an agent-authored repo it is often the only place
      the *why* survives, because the narrative ratchet pushes it out of the code.
- [ ] A handoff entry appended to `.devloop/LEDGER.md` if the session ends before the task does.

## Where the other records live

MiOS has its own tracking; this maps onto it rather than duplicating it.

| Role | MiOS path |
|---|---|
| Constitution | `AGENTS.md`, `CLAUDE.md` |
| Goals / north star | `docs/design/operating-agreement.md` §2 |
| Roadmap | `ROADMAP.md` (workstreams `WS-*`) |
| Decisions | `usr/share/doc/mios/adr/` |
| Tasks | `TASKS.md` (machine-readable source: **T-1023, not yet built**) |
| Handoff | `.devloop/LEDGER.md` |
