<!-- AI-hint: Full De-duplication Campaign Tracking & Architecture (AGY-856..930). The **Full De-duplication Campaign** ("one value, one name, everywhere") enforces single-sourcing across the entire MiOS environment and derived surfaces. Every configuration value is declared exactly once in `usr/share/mios/mios.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# Full De-duplication Campaign Tracking & Architecture (AGY-856..930)

## Overview
The **Full De-duplication Campaign** ("one value, one name, everywhere") enforces single-sourcing across the entire MiOS environment and derived surfaces. Every configuration value is declared exactly once in `usr/share/mios/mios.toml`, derived deterministically, and projected without duplication.

## Baseline Measurement
- **Initial Key Count**: 2,523 resolved environment keys
- **Measured Value Groups**: Analyzed via `tools/mios-dup-report` (`usr/share/mios/reference/value-dup-report.tsv`)
- **Target Key Count**: ~1,850 minimal canonical keys

## Campaign Workstreams
1. **WS-DEDUP-DISCOVER (AGY-856..864)**: Tooling, scanners, and drift-gate enforcement (`mios-dup-report`, `mios-cross-surface-scan`, `check_no_duplicate_value_key`, `check_no_hardcoded_ssot_literal`).
2. **WS-DEDUP-COLOR (AGY-865..872)**: Reconciles `COLOR_*` vs `COLORS_*` and ANSI color aliasing.
3. **WS-DEDUP-AIPLANE (AGY-873..882)**: Consolidates AI embeddings (`MIOS_AI_EMBED_MODEL`), models (`MIOS_AI_MODEL`), endpoints (`MIOS_AI_ENDPOINT`), and vLLM naming.
4. **WS-DEDUP-NETPATH (AGY-883..889)**: Single-sources bind hosts, browser flags, sub-dir paths, and port derivation logic.
5. **WS-DEDUP-STRUCTURAL (AGY-890..897)**: Eliminates double-emission rules in `mios_toml.py` and `userenv.sh` via a centralized `COMPAT-ALIAS` table.
6. **WS-DEDUP-CROSSSURFACE (AGY-898..907)**: Projects `mios.html`, `knowledge-graph.json`, SBOM, Quadlets, and docs directly from SSOT via `mios-ssot-regen`.
7. **WS-DEDUP-GUP56 (AGY-908..918)**: Floats sidecar refs to `:latest`, records digests in SBOM, and derives minimal namespace.
8. **WS-DEDUP-SIGNOFF (AGY-919..930)**: Permanent enforcement, negative tests, ADR-0015, and campaign signoff.

## Lossless Invariant
For every change across the campaign:
1. `mios-env-snapshot | diff env-baseline.txt -` must show **ONLY** deliberate key drops or re-mappings.
2. `check-resolver-twin.py` (twin equivalence between Python `mios_toml.py` and bash `userenv.sh`) must remain **100% PASS**.
3. `bash automation/98-drift-checks.sh` must remain **100% PASS**.
