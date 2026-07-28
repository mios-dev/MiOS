<!-- AI-hint: Unified deployment dispatcher installation/mios-install resolves N target types to underlying specialized entrypoints without rewriting them; read before modifying installer CLI interfaces or adding new install surfaces. -->
<!-- AI-related: installation/mios-install.sh, installation/mios-install.ps1, installation/mios-common.ps1, installation/UNIFY.md -->
---
adr: 0013
title: "Deploy-surface consolidation behind installation/mios-install"
status: accepted
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [deploy, consolidation, installer, dispatch, UNIFY]
laws: [1, 7, 8, 9]
ssot_keys: [verbs, ports, install, cat]
related_ws: [WS-INSTALL, WS-CONFIG]
supersedes: []
superseded_by: []
---

# ADR-0013: Deploy-surface consolidation behind installation/mios-install

## Status

Accepted — 2026-07-28. Implemented for Linux (`installation/mios-install.sh`) and Windows (`installation/mios-install.ps1`).

## Context

Prior to consolidation, the MiOS codebase contained multiple independent, non-standardized installation scripts across different directories (`build-mios.sh`, `mios-update`, `MiOS-Cat.bat`, `Deploy-MiOSXbox.ps1`, `install.sh`, etc.). Users and automated pipelines had to invoke different entrypoints depending on whether they were building an OCI container, flashing a Ventoy USB drive, deploying a Hyper-V virtual machine, or upgrading an existing bootc host.

This fragmentation caused:
1. **Inconsistent CLI Parameters**: Target names, flags (`--dry-run`, `-Unattended`), and verbose output options differed across scripts.
2. **Duplicate Logic**: Environment validation, administrator privilege elevation, and logging were independently re-implemented in multiple scripts.
3. **High Cognitive Load**: Automated agents and human operators had to maintain complex conditional logic to select the correct script.

## Decision

Consolidate all deployment and installation surfaces behind a single, unified entrypoint: **`installation/mios-install`** (`mios-install.sh` on Linux, `mios-install.ps1` on Windows).

Key architecture rules:
1. **Pure Dispatcher Pattern**: `mios-install` acts as a high-level dispatcher. It parses standard CLI parameters, validates environment state, resolves the target action, and delegates execution to specialized entrypoints without altering or destroying the underlying scripts.
2. **Unified Target Matrix**: Standard targets (`live`, `xbox`, `fedora`, `bootc`, `oci`, `seed`, `flash`, `build`, `update`, `config`) are resolved through a shared resolution contract (`installation/mios-common`).
3. **Shared Common Library**: Common tasks (elevating privileges, logging, reading SSOT defaults from `mios.toml`, `--dry-run` plan preview) are implemented once in `installation/mios-common.{sh,ps1}`.
4. **Non-Interactive & Unattended Parity**: All targets accept a standard `-Unattended` / `--unattended` / `NONINTERACTIVE=1` flag for non-interactive automated pipeline execution.

## Rationale

- **Single Front Door**: Users and automated workflows execute `mios install <target>` regardless of operating system or target infrastructure.
- **Backward Compatibility**: Existing specialized entrypoints (`MiOS-Cat.bat`, `New-MiOSISO.ps1`) remain functional for direct invocation while benefiting from standardized dispatching.
- **Maintainability**: Centralizes CLI argument parsing and error logging in one audited module.

## Alternatives

- **Complete Script Rewrite**: Replace all existing scripts with a single monolithic 10,000-line script. *Rejected*: High risk of regressions, destroys modularity, and breaks existing direct tool callers.
- **Status Quo**: Keep separate uncoordinated installation scripts. *Rejected*: Leads to parameter drift and maintenance overhead.

## Consequences

### Positive
- Standardized CLI syntax across Linux and Windows (`mios install flash`, `mios install xbox`, etc.).
- Robust `--dry-run` execution preview across all targets.
- Clear separation between dispatch logic and underlying deployment implementation.

### Negative
- Require maintaining wrapper logic in `mios-common` when target script signatures evolve.

## Implementation

- Implemented `installation/mios-install.sh` and `installation/mios-install.ps1`.
- Standardized `installation/mios-common.sh` and `installation/mios-common.ps1`.
- Added UNIFY spec document `installation/UNIFY.md`.

## References

- [ADR-0008: MiOS-Cat unified entry point + repo minification](file:///C:/MiOS/usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md)
- `installation/mios-install.ps1`
- `installation/UNIFY.md`
