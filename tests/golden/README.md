<!-- AI-hint: Golden-master CLI testing standards and Trycmd harness specifications (AGY-1067 / ADR-0021).
     AI-related: usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md, docs/design/doc-rust-static-port.md, tests/run-suites.sh, tools/ci-suites.py -->
# Golden-Master CLI Testing Standards (AGY-1067 / ADR-0021)

This directory hosts the **golden-master test fixtures and regression harnesses** for the MiOS Script→Rust Static Binary consolidation (ADR-0021 / `doc-rust-static-port.md`).

## 1. Core Principle: Two-Sided Verification Before Code

Per the dev-loop Definition of Done and AGY-1067, **no Rust code is written until a golden-master fixture set exists for the script surface being replaced**.

Every golden-master suite MUST be two-sided:

1. **Positive Controls**:
   - Valid inputs executed against the real repository/system tree.
   - Asserts exit code `0` (`EXIT_CLEAN`).
   - Asserts stdout and stderr match byte-for-byte, including trailing newlines and whitespace formatting.
2. **Negative Controls**:
   - Explicitly planted defects (missing required SSOT keys, malformed arguments, nonexistent file paths, invalid flags).
   - Asserts exit code `1` (`EXIT_VIOLATIONS`) or `2` (`EXIT_CANNOT_RUN`).
   - Asserts that the tool fails **strictly for the planted reason**, matching the expected diagnostic error message. A test that passes unconditionally or cannot fail is a phantom test and is forbidden.

## 2. Directory & Fixture Layout

Each ported surface defines a subdirectory under `tests/golden/<surface>/`:

```
tests/golden/
├── README.md                          # This specification
├── <surface>/                         # e.g., cosign-policy, names-registry, hardcode-lint
│   ├── cmd.toml                       # Trycmd runner configuration
│   ├── cases/
│   │   ├── positive_valid.trycmd      # Positive control (exit 0)
│   │   ├── negative_missing_key.trycmd# Negative control: missing SSOT key (exit 2)
│   │   └── negative_malformed.trycmd  # Negative control: malformed input (exit 1)
│   └── fixtures/                      # Mock trees or temporary inputs for negative testing
```

## 3. Parity Execution Contract

A golden-master harness must be capable of executing against **both** the legacy script and the compiled replacement binary without altering test fixtures:

```bash
# Verify legacy script matches golden baseline
trycmd --bin "python3 tools/generate-<surface>.py" tests/golden/<surface>/cases/

# Verify native Rust binary matches identical golden baseline
trycmd --bin "target/release/mios-<surface>" tests/golden/<surface>/cases/
```

### Exit Code Invariants
- `0`: Clean execution, zero violations.
- `1`: Violations found (lints, schema mismatch, contract failures).
- `2`: Could not run (missing arguments, unreadable files, corrupt TOML). Never emit exit `0` on unread or unparseable input.

### Output Formatting
- Default output format is human-readable text.
- `--format json` emits OpenAI-format structured JSON:
  ```json
  {
    "check": "<surface>",
    "status": "clean" | "violations" | "could_not_run",
    "summary": "...",
    "findings": []
  }
  ```

## 4. Single-Commit Migration Protocol

1. Author golden-master fixtures in `tests/golden/<surface>/` capturing current script behavior.
2. Scaffold crate via `mios new rust-crate <name>`.
3. Implement Rust logic reading from `mios-resolver` without carrying hardcoded literals.
4. Prove 100% byte-parity across positive and negative controls on the real tree.
5. Register the binary in `[build.native.categories]` and `[rust.categories]`.
6. Delete the legacy script in the **same commit** that proves parity. `git revert` of this commit serves as the atomic rollback.
7. Lower `[legibility]` line count ceilings using `mios-size-ceiling` and ensure all standing gates pass.
