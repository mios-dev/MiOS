<!-- AI-hint: Manual pages distilled from the source comments of tests, sanitized, each passage anchored to the comment it came from. -->

# tests

### Read the component lists from SSOT. A missing or empty list...

Read the component lists from SSOT. A missing or empty list is FATAL, not a
fallback: `for x in ${EMPTY}` runs zero iterations and the loop still prints
"OK", so an SSOT edit that dropped a list would turn this whole harness into a
vacuous pass. The old fallbacks also hardcoded paths (Law 7) and capitalised
them ("Usr/..."), so they could never have matched anything anyway.

<!-- mios-src:91e227c14aae from tests/bake-smoke.sh:22-26 -->

### MUST run before anything else. check_ai_manifests_fresh...

MUST run before anything else. check_ai_manifests_fresh compares the
manifests against a fresh walk of automation/ and tools/, and dozens of
the tests below create, mutate and restore files in exactly those trees
(some restore via `echo "$orig" >`, which drops a trailing newline). Run
it last and it grades the wreckage of every preceding test instead of the
committed state.

<!-- mios-src:1a2b377668f5 from tests/drift-gate-negatives.sh:2373-2378 -->

### Verify the ReWOO #E<id> substitution now smart-extracts a...

Verify the ReWOO #E<id> substitution now smart-extracts a single
field instead of pasting the whole upstream JSON blob.

Test cases derived from operator's failure trace where the planner
emitted open_app(name=#En1) and substitution pasted mios_apps's
entire NDJSON output as the arg.

<!-- mios-src:fd04fe58468c from tests/test-ek-smart-extract.py:5-11 -->

### Smoke-test _substitute_ek_refs. Verifies the ReWOO #E<id>...

Smoke-test _substitute_ek_refs.

Verifies the ReWOO #E<id> placeholder substitution across the
shapes a planner might emit:
  * simple string substitution
  * multiple refs in one arg
  * refs to non-existent ids (preserved literal so dispatch errors)
  * non-string args (passed through)

<!-- mios-src:a9fa0f5051af from tests/test-ek-substitution.py:5-13 -->

### Smoke-test the skill engine's expand_from semantics. Calls...

Smoke-test the skill engine's expand_from semantics.

Calls execute_skill('open-url-fallback-chain', ...) with 3 browsers
and a deliberately-bad URL; verifies the engine fanned 1 step into
3 (one per browser) by inspecting the returned `steps` list length.

Exits 0 on PASS, 1 on FAIL.

<!-- mios-src:2cc352692064 from tests/test-expand-from.py:5-12 -->

### Smoke-test the refine chat-promotion guard. Calls...

Smoke-test the refine chat-promotion guard.

Calls refine_intent() with three actionable inputs that a small
refine model has historically misclassified as chat (operator-
flagged trace: 'mios-open-url https://...' returned intent=chat
+ fabricated 'Wikipedia has been opened' confirmation when nothing
was actually executed). Verifies the post-parse guard rewrites
chat -> dispatch.

<!-- mios-src:eeb00086dc8c from tests/test-refine-guard.py:5-13 -->

### Verify the new refine post-parse guards demote...

Verify the new refine post-parse guards demote misclassified
intents to `agent`. Three cases:

  1. Long multi-step prompt -- exact operator-flagged trace:
     "find all of my installed games; research all their ratings,
     review and launch the highest reviewed game I have installed
     for me on my PC". Refine model may emit intent=dispatch (as
     it did in the failure trace); the length guard should promote
     to agent so the planner can decompose.
  2. Short legitimate dispatch -- "open chrome". Should pass
     through as intent=dispatch (length under threshold).
  3. Multi-word arg value -- simulate a refine output via direct
     guard invocation (refine model is non-deterministic, so we
     can't always force it; this case is exercised by calling the
     guard logic directly with a forged envelope).

Live test against the real refine endpoint -- slow (15-30s per
call on CPU).

<!-- mios-src:7f133c2ab83a from tests/test-refine-guards.py:5-23 -->

### Smoke-test reflect_on_step_failure. Calls the reflection...

Smoke-test reflect_on_step_failure.

Calls the reflection helper with a deliberately-bad failed_node
(unknown verb) and verifies the small refine model returns a
correction with a non-empty tool name + rationale.

Live test -- hits the actual refine endpoint -- so it's slow
(15-30s on CPU) but exercises the real path.

<!-- mios-src:d63f63fff4d6 from tests/test-reflection.py:5-13 -->
### An Image= whose variable resolves nowhere used to be...

An Image= whose variable resolves nowhere used to be skipped silently,
which resurfaced as "core image is not referenced by any Quadlet" --
an error naming a different file entirely. The probe tag is deliberately
not MIOS_-prefixed: generate-names-registry harvests every MIOS_* token it
sees, so a MIOS_-named probe writes itself into referenced_names.txt and
the test starts editing the SSOT it guards.

<!-- mios-src:7140d10222ad from tests/drift-gate-negatives.sh:414-419 -->

### neg_gate once contained a literal backslash-n instead of...

_neg_gate once contained a literal backslash-n instead of line
continuations, so the command word became `n` and it returned 127 every
time. Under that, all 61 tests that call it could never detect anything --
`if _neg_gate X; then die` simply never fired -- while their restoration
arms died unconditionally. A helper 61 tests depend on has to be proven
before it is trusted, and proven in BOTH directions.

<!-- mios-src:631badca875f from tests/drift-gate-negatives.sh:2956-2961 -->

### !/usr/bin/env bash AI-hint: Self-contained test harness for...

!/usr/bin/env bash
AI-hint: Self-contained test harness for automation/97-ssot-lint.sh -- builds throwaway fixture trees (a fully-wired key, a both-sides orphan, a userenv-only and a render-only half-orphan) to assert the lint's PASS/FAIL exit codes and orphan detection, then asserts it flags the real known dead key (MIOS_SGLANG_TOOL_PARSER) in the live repo tree.
AI-related: ../97-ssot-lint.sh, ../34-render-quadlets.sh, ../../tools/lib/userenv.sh, ../../usr/share/containers/systemd
AI-functions: _mk_fixture, _expect, main

<!-- mios-src:a64282216d09 from automation/tests/test-97-ssot-lint.sh:1-4 -->
### Linux Clean Worktree Test & Drift Gate Execution

To run the full suite of drift checks and negative gate tests on a clean Linux environment:

```bash
# Set repository environment variables
export MIOS_DRIFT_ROOT="$(pwd)"
export MIOS_DRIFT_CHECK_ROOT="$(pwd)"
export MIOS_DRIFT_REQUIRE_TOOLS=1

# Run full drift check suite
bash automation/98-drift-checks.sh

# Run negative gate tests
bash tests/drift-gate-negatives.sh
```

Note: A stale installed MiOS on the host machine can fake SSOT-projection drift if `/etc/mios` or `/usr/share/mios` contains un-projected overrides. Always run with `MIOS_DRIFT_ROOT` pointing explicitly to the local workspace root.

<!-- mios-src:agy-1620 from docs/manual/tests.md -->
