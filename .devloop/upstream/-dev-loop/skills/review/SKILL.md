---
name: review
description: SCOPE staged code oversight of a diff (Staged Code Oversight with Proportional Escalation) - Stage 1 agent review (contract preservation, invariant and security audit, suppression/threshold drift, dead code, test strength), Stage 2 steering-developer ownership check, Stage 3 proportional peer escalation, recorded in a Living Oversight Record. Use before merging a lane, before /ship, or when asked to review changes.
argument-hint: "[target_ref|--staged]"
context: fork
agent: dev-loop:auditor
allowed-tools: Read, Grep, Glob, Bash
---
# /review — SCOPE review (read-only)

_Paths: `${CLAUDE_SKILL_DIR}/../dev-loop/scripts/` resolves in Claude Code; in other harnesses use `<skills dir>/dev-loop/scripts/` (the shims in `shims/<harness>/` already do)._

Target: `$ARGUMENTS` (default: staged changes, else HEAD).

1. **Stage 1 — agent review:** `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/review.py <target>` → `.devloop/scope_review_*.json` + `OVERSIGHT_RECORD.md` (rubric: `assets/templates/REVIEW_RUBRIC.md`; record template: `assets/templates/OVERSIGHT_RECORD.md`). Findings carry severity (BLOCKER/CRITICAL/WARNING/SUGGESTION) × dimension (SECURITY/HYGIENE/CONTRACTS/TESTS/OPERATIONS/SIMPLIFICATION).
2. Manually verify what the tool cannot: does the diff widen types, loosen assertions, raise thresholds, add `# noqa`/`@skip`/baseline entries, or delete tests (SKILL §8)? Does every claim of "tested" cite a positive AND a negative control (§6)? Do the changed paths stay inside the task's scope? Is the change within Agent-Dev Loop sizing (≤ 600 lines / ≤ 20 files) — if not, recommend splitting before human review.
3. Secrets: `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/adapters.py secrets --wt .`; dependency change staged → `adapters.py deps --wt .`.
4. **Stages 2–3 are people, not you:** the engine computes the proportional-escalation tier (Understanding Need × Change Risk × Established Assurance → async challenge or synchronous walkthrough); the steering developer accepts ownership and peers review at that tier. Report the tier; never sign the record yourself.
5. Verdict: PASSED | REVISE (list exact fixes with file:line) | BLOCKED (why). Never edit files in this skill; return the verdict, the escalation tier, and the report path.
