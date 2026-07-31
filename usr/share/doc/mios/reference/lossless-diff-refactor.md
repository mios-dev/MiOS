<!-- AI-hint: Document describing the refactor methodology and invariant enforcement for the Global Unification Plan (GUP) and environment configuration in MiOS. -->
<!-- AI-related: usr/libexec/mios/mios-env-snapshot, usr/share/mios/reference/env-baseline.txt, automation/98-drift-checks.sh, usr/lib/mios/mios_toml.py -->

# Lossless-Diff Refactor Method (GUP Invariant)

This document describes the refactor methodology for the Global Unification Plan (GUP) and environment configuration in MiOS.

## The Invariant

For every refactor, key-deduplication, or resolver modification:
```bash
usr/libexec/mios/mios-env-snapshot | diff usr/share/mios/reference/env-baseline.txt -
```
Must be **EMPTY**, or contain ONLY the exact `MIOS_*` keys that the task explicitly intends to drop or collapse.

## Refactor Steps

1. **Capture Ground Truth**:
   Run `usr/libexec/mios/mios-env-snapshot` to verify current resolved state matches `usr/share/mios/reference/env-baseline.txt`.

2. **Execute Code / Configuration Changes**:
   Modify `mios.toml`, `mios_toml.py`, or `userenv.sh`.

3. **Verify Zero Drift**:
   Re-run `usr/libexec/mios/mios-env-snapshot` and diff against `env-baseline.txt`.

4. **Intentional Baseline Bumps**:
   When dropping dead keys or collapsing alias-dupes, re-generate `env-baseline.txt`:
   ```bash
   usr/libexec/mios/mios-env-snapshot > usr/share/mios/reference/env-baseline.txt
   ```
   Set `MIOS_ENV_BASELINE_BUMP=1` in the commit environment or commit message note to signal an intentional baseline update to `check_resolved_env_lossless`.

## Enforcement

- **Pre-commit**: `.githooks/pre-commit` runs the snapshot diff prior to local commits.
- **Drift Gate**: `automation/98-drift-checks.sh` check `check_resolved_env_lossless` validates the baseline in CI.
