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
### Import this before importing `server`. Nine suites each...

Import this before importing `server`.

Nine suites each pointed the import search at the INSTALLED directory. A CI
runner has no such directory, so importing the server raised and every one of
those suites failed -- which is why none was ever wired into a workflow. A
developer machine that does have MiOS installed ran them against the installed
copy instead of the working tree, so the change under test was not the code
being tested.

Resolving from this file's own location fixes both: the repository copy comes
first, and the installed directory stays as a fallback for a suite executed
outside a checkout.

<!-- mios-src:0ab56d83257e from tests/_agentpipe_path.py:3-15 -->

### The suite mutates tracked files and is supposed to put them...

The suite mutates tracked files and is supposed to put them back. A test that
dies between the two leaks its fixture into the tree. Five reached the working
tree in one session -- an injected table in the shipped SQL schema, a root
password in a Ventoy firstboot script, a rewritten cockpit port, a capability
requirement replaced by an injected name, a port entry repeated twice -- and
each one surfaced as some unrelated suite failing, so the cost was paid several
times before anyone read the diff.

Snapshot everything the suite can reach before running, and put back whatever a
test failed to restore. The target list is derived from this file's own source,
so a test that starts touching a new path is covered without anyone updating a
list.

<!-- mios-src:59b3532038ab from tests/drift-gate-negatives.sh:10-21 -->

### 55-bake-quickshell.sh was renumbered to 66-. The whole body...

55-bake-quickshell.sh was renumbered to 66-. The whole body used to sit
inside `if [[ -f ]]`, so once the file moved the test skipped everything
and logged "passed" -- a test that reports success precisely when its
subject is gone. A missing target is now a failure.

<!-- mios-src:5b27437275f6 from tests/drift-gate-negatives.sh:1762-1765 -->

### Subshell

Subshell: die() exits the test, not the suite. One CI run then reports
every failure instead of the first, which is what turned a queue of
latent breakages into one round trip each.

<!-- mios-src:56662eab3f3b from tests/drift-gate-negatives.sh:2935-2937 -->

### REQUIRE_TOOLS is forwarded deliberately

REQUIRE_TOOLS is forwarded deliberately: checks that shell out to a built
binary choose between "skip" and "fail" on it, so a test that cannot set
it cannot exercise the failing path -- the path that matters.
Output is kept, not discarded: "failed after restoration" with no reason
has cost two CI round trips, and die() prints this on the way out.

<!-- mios-src:f84b0295a436 from tests/drift-gate-negatives.sh:2942-2946 -->

### A C-style header in a systemd unit is not a comment: the...

A C-style header in a systemd unit is not a comment: the line is rejected,
and one such line in a WSL config failed a build twenty-nine minutes in.

<!-- mios-src:252855120d3e from tests/drift-gate-negatives.sh:3134-3135 -->

### The previous probe flipped `enabled` from false to true...

The previous probe flipped `enabled` from false to true, but the key has
been true for some time, so the sed matched nothing and the test asserted
against an unmodified tree. The check requires every merge-rule key to
have a table carrying origin_node and logical_ts, so declaring a rule with
no such table is the edit that loses data silently on rejoin (ADR-0017 D5).

<!-- mios-src:52fddbc14295 from tests/drift-gate-negatives.sh:3570-3574 -->

### The old probe moved bootc-fetch-apply-updates.timer aside...

The old probe moved bootc-fetch-apply-updates.timer aside, but that file
ships from an RPM and has never existed in this tree: it moved nothing and
the check "failed" for a reason the test never created -- a broken probe
and a broken check agreeing. The check now asserts the SSOT declares an
updater package and a bake phase wires its timer, so break the wiring.

<!-- mios-src:76296fd5fe57 from tests/drift-gate-negatives.sh:3728-3732 -->
### Adversarial Verification Suite (Challenger 1). Executes...

Adversarial Verification Suite (Challenger 1).

Executes stress tests, edge cases, boundary conditions, fuzzing payloads,
and security attack scenarios across the roadmap modules:
- T-377: MCP Bubblewrap Sandbox Engine
- T-378: HITL Interactive Approval Engine
- T-379: Knowledge Graph Recursive CTE Traversal
- T-380: Contextual Prompt Token Pruning Engine
- T-381: Agent-to-Agent (A2A) Ed25519 Attestation

<!-- mios-src:fef635956dcf from tests/test-adversarial-roadmap.py:4-14 -->

### Adversarial Observation

Adversarial Observation: When operator username contains a colon (e.g. 'admin:ops'),
        token serialization creates extra delimiters, causing validation failure.

<!-- mios-src:8346ccde2a47 from tests/test-adversarial-roadmap.py:219-222 -->

### MiOS Empirical Adversarial Test Harness (Challenger 2)....

MiOS Empirical Adversarial Test Harness (Challenger 2).

Executes stress-testing, boundary attacks, cyclic recursion tests, cryptographic
malleability checks, AST preservation tests, and fuzzing payloads against:
- MCP Bubblewrap Sandbox Engine (T-377 / MCP-01)
- Interactive HITL Permission Escalation & Approval Engine (T-378 / SEC-06)
- Recursive CTE Knowledge Graph Traversal Engine (T-379 / GRAPH-01)
- Contextual Prompt Compression & Token Pruning Engine (T-380 / PROMPT-01)
- A2A Cryptographic Capability Attestation Engine (T-381 / A2A-01)

<!-- mios-src:2d05ccc7a701 from tests/test-empirical-challenger-2.py:4-14 -->

### Adversarial Stress Test Suite for Milestone 1: 1....

Adversarial Stress Test Suite for Milestone 1:
1. Self-Healing Circuit Breaker & Safe Remediation Engine (T-382)
   - Rapid bursts of failures (100 rapid events)
   - Multi-unit isolation & interleaved failure/recovery sequences
   - Circuit breaker window expiration & quarantine timing
   - Invalid / binary / corrupted journal logs
   - Malformed & traversal /usr immutability attack paths
   - Corrupted state JSON recovery and schema validation
   - SafeConfigEditor atomic file operations & error handling

2. Synthetic Training Q&A Data Pipeline (T-383)
   - Secret redactor: nested keys (JSON/YAML/TOML/Env), multi-line keys (RSA/EC/SSH), tokens, bearer auth
   - Secret redactor: multi-word passwords inside quotes
   - Secret redactor: false-positive preservation on standard prose and config keys
   - Hierarchical markdown parser: 6-level deep headers, header level jumping, headers inside code blocks
   - Unclosed code fences, malformed tables, empty sections, unicode/emoji handling
   - Q&A synthesis schema adherence & JSONL single-line validation

<!-- mios-src:d333e27d454b from tests/test-m1-adversarial.py:4-22 -->

### Adversarial Stress Test Suite for Milestone 1 (Challenger...

Adversarial Stress Test Suite for Milestone 1 (Challenger 2):
1. Dynamic Persona Synthesis (T-384 / AGY-1982)
   - Conflicting multi-domain queries & score balancing across 6 specialized domains
   - Zero-keyword, whitespace, punctuation, and emoji-only inputs
   - Multilingual queries (Chinese, Japanese, French, German, Russian, Arabic)
   - Adversarial prompt injections & canonical law override resistance
   - Boundary confidence thresholds & synthesis idempotency
   - Long-text stress (50,000+ words) & zero degradation

2. Bounded Reflection Loop Convergence (T-385 / AGY-1983)
   - Identical successive texts (0.0 delta) -> instant diminishing returns exit
   - Sub-5% micro-edits in realistic paragraph -> diminishing returns exit
   - Oscillating / adversarial critiques -> strict max_iteration ceiling enforcement
   - Semantic delta mathematical properties (identity, range [0, 1], high disjoint delta)
   - Configurable max_iterations and min_iterations enforcement
   - Extreme corpus size (10,000+ words) delta calculation performance
   - Critique approval pattern matching & false-positive negation analysis
   - Deliberation state tracking & dictionary serialization integrity

<!-- mios-src:863b31713931 from tests/test-m1-challenger2-adversarial.py:4-23 -->

### Adversarial Stress Test Suite for Milestone 2: 1. Async TCP...

Adversarial Stress Test Suite for Milestone 2:
1. Async TCP Framing & Wire Codec (T-386)
   - Byte-by-byte (1-byte chunk) stream feeding across 50 multi-opcode frames
   - Irregular/randomized chunk slicing across packet boundaries
   - High-concurrency async TCP client/server throughput (30 concurrent clients, 300 frames)
   - Corrupted CRC32 injection across head, middle, and tail of payload
   - Corrupted magic, version, opcode, and underflow rejection
   - Oversized payload length header rejection (> 64MB)
   - Zero-byte payload valid frame roundtrip (CRC32=0)
   - Stream buffer partial frame drainage and resume
   - NodeWireDispatcher error response generation for unhandled opcodes

2. Heartbeat Monitor & Dead-Peer Eviction (T-387)
   - Mathematical boundary precision (0s, 4.999s, 5.0s, 9.999s, 10.0s, 14.999s, 15.0s)
   - Rapid flapping and state churn across 20 peers for 100 timesteps
   - Mass simultaneous eviction of 100 peers in a single sweep
   - Complete listener notification dispatch on mass eviction
   - Clean re-admission after eviction with strike and state reset
   - Local node ID self-filtering rejection
   - Monotonic time jitter / backward timestamp protection
   - Custom threshold configuration lifecycle

<!-- mios-src:2212811d9cc6 from tests/test-m2-adversarial.py:5-27 -->

### Adversarial Stress Test Suite for Milestone 2 / T-388...

Adversarial Stress Test Suite for Milestone 2 / T-388 (Challenger 2):
1. Cryptographic Handshake Adversarial Tests:
   - Exhaustive single-bit and multi-byte signature tampering across Init and Resp packets (all 64 bytes fuzzed).
   - Signature truncation (< 64 bytes) and extension (> 64 bytes) rejection.
   - Forged identity pubkeys and ephemeral pubkeys injection / MITM rejection.
   - Imposter node identity spoofing and unauthorized packet creation.
   - Replay attack resilience and ephemeral key freshness (no key reuse).
   - Key derivation symmetry, directional TX/RX key separation, and anti-reflection guarantee.

2. Wire AEAD Encryption Adversarial Tests:
   - Exhaustive bit-flip fuzzing across all payload ciphertext bytes.
   - Exhaustive bit-flip fuzzing across all 16 bytes of the Poly1305 MAC tag.
   - Ciphertext truncation (< 16 bytes) and partial MAC tag drop handling.
   - AAD / Node ID spoofing and cross-node ciphertext injection rejection.
   - Strict nonce sequence progression, out-of-order packet drop, and wire replay attack prevention.
   - High-volume multi-frame stream stress (1,000 frames) with boundary payload sizes (0B, 1B, 15B, 16B, 17B, 64B, 65B, 64KB).
   - Layered defense validation: Wire CRC32 transport integrity vs Poly1305 cryptographic authenticity.

3. Concurrency & RFC Standards Compliance:
   - Concurrent multi-session thread isolation across 20 distinct mesh nodes.
   - Session renegotiation & zero cross-session decryption leakage.
   - RFC 8439 / RFC 7748 / RFC 5869 cryptographic correctness verification.

<!-- mios-src:d20bb811f899 from tests/test-m2-challenger2-adversarial.py:5-28 -->

### Unit and integration test suite for WS-NODE: Async TCP...

Unit and integration test suite for WS-NODE: Async TCP frame reader, writer actor,
stream buffer management, partial packet chunking, and channel dispatch.

<!-- mios-src:328b88702d66 from tests/test-node-async-net.py:4-7 -->

### Unit test suite for WS-NODE

Unit test suite for WS-NODE: Ed25519 node identity signing/verification, X25519 Diffie-Hellman
key exchange, HKDF-SHA256 session key derivation, ChaCha20-Poly1305 authenticated symmetric payload
encryption, MAC tag validation, tamper detection, and imposter rejection.

<!-- mios-src:8f6cd66980af from tests/test-node-crypto-handshake.py:4-8 -->

### Unit test suite for WS-NODE

Unit test suite for WS-NODE: Heartbeat interval (5s), 3-strike dead peer detection (15s threshold),
degraded status transitions, routing table pruning, eviction event dispatching, and re-admission.

<!-- mios-src:559815f2ca99 from tests/test-node-heartbeat-eviction.py:4-7 -->
### 1. T-392: Stress & Invariant Tests for Work-Stealing...

=========================================================================
1. T-392: Stress & Invariant Tests for Work-Stealing Scheduler
=========================================================================

<!-- mios-src:0862d143d1c2 from src/mios-rs/mios-node/tests/mesh_m2_stress_challenger_test.rs:23-25 -->

### 2. T-393: Stress & Invariant Tests for Zero-Copy Buffer Pool

=========================================================================
2. T-393: Stress & Invariant Tests for Zero-Copy Buffer Pool
=========================================================================

<!-- mios-src:ea343ab95afb from src/mios-rs/mios-node/tests/mesh_m2_stress_challenger_test.rs:170-172 -->

### 1. T-392: Stress & Invariant Tests for Work-Stealing...

-------------------------------------------------------------------------
1. T-392: Stress & Invariant Tests for Work-Stealing Scheduler
-------------------------------------------------------------------------

<!-- mios-src:7b8e2b29186c from tests/test-node-m2-adversarial-challenger.py:59-61 -->

### 2. T-393: Stress & Invariant Tests for Zero-Copy Buffer Pool

-------------------------------------------------------------------------
2. T-393: Stress & Invariant Tests for Zero-Copy Buffer Pool
-------------------------------------------------------------------------

<!-- mios-src:844288c053a9 from tests/test-node-m2-adversarial-challenger.py:155-157 -->
