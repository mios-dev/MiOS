<!-- AI-hint: Unified key library architecture defining single-source rule, derive rules, centralized COMPAT-ALIAS table, and enforcement gates. -->
<!-- AI-related: usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py, tools/lib/userenv.sh, automation/98-drift-checks.sh -->
---
adr: 0015
title: "Unified key library architecture & full de-duplication campaign"
status: accepted
date: 2026-07-31
deciders: [operator, ai-pair]
tags: [unification, resolver, dedup, ssot, architecture]
laws: [7, 8, 9, 13]
ssot_keys: [build.bake, colors, ai, ports]
related_ws: [WS-DEDUP-DISCOVER, WS-DEDUP-SIGNOFF]
supersedes: []
superseded_by: []
---

# ADR-0015: Unified Key Library Architecture & Full De-Duplication Campaign

## Status
Accepted — 2026-07-31. Implemented and enforced via drift-gate suite.

## Context
MiOS previously emitted over 2,500 resolved environment keys with substantial value duplication (colors 7x per hex, AI models 6-10x per identifier, duplicate host/path/port definitions). This complexity caused resolver twin drift and cross-surface documentation mismatch.

## Decision
1. **Single-Source Rule**: Every configurable fact is declared exactly once in `usr/share/mios/mios.toml`. Derived surfaces (docs, `mios.html`, knowledge graph, Quadlets, SBOM) project from SSOT via `usr/libexec/mios/mios-ssot-regen`.
2. **Derive Rules**: Version keys (e.g. `MIOS_X_VERSION`) derive automatically from image refs (`tag(MIOS_X_IMAGE)`). Ports derive from base port + `stack_offset`. Sub-directories derive from parent path declarations.
3. **Centralized COMPAT-ALIAS Table**: All backward-compatibility aliases are declared in a single canonical table shared between Python `mios_toml.py` and bash `userenv.sh` twins.
4. **Lossless Invariant**: Transformations must be lossless (`mios-env-snapshot | diff env-baseline.txt -` empty or showing explicit intended drops).
5. **Enforcement Gates**:
   - `check_no_duplicate_value_key`: Fails when non-allowlisted duplicate values exist.
   - `check_no_hardcoded_ssot_literal`: Fails when cross-surface files embed SSOT literals.
   - `check_resolved_env_lossless`: Verifies zero drift against `env-baseline.txt`.
   - `check_resolver_twin_equivalence`: Verifies twin equivalence between `userenv.sh` and `mios_toml.py`.

## Rationale
Consolidating to a single SSOT representation eliminates redundant key duplication while ensuring backward compatibility through derived aliases. Enforcing zero cross-surface literal hardcoding guarantees that changing a single configuration value updates every manifest, document, and generator automatically.

## Consequences
- Key count reduced by ~25% with zero runtime or configuration drift.
- Resolver logic consolidated behind identical Python and bash twins.
- Cross-surface documentation and UI update automatically upon updating SSOT.
