<!-- AI-hint: Single front door for AGY tree deployment: installation/mios-install resolves targets to underlying entrypoints without modifying existing scripts. -->
<!-- AI-related: installation/mios-install.sh, installation/mios-install.ps1, installation/mios-common.sh, installation/UNIFY.md -->
---
adr: 0013
title: "Deploy-surface consolidation behind installation/mios-install"
status: accepted
date: 2026-07-28
deciders: [operator, ai-pair]
tags: [installation, deployment, dispatch, CLI, mios-install]
laws: [1, 7, 8, 9]
ssot_keys: [install.target, cat.mode]
related_ws: [WS-INSTALL, WS-CONFIG]
supersedes: []
superseded_by: []
---

# ADR-0013: Deploy-surface consolidation behind installation/mios-install

## Status

Accepted — 2026-07-28. Scoped to the AGY repository tree (`installation/mios-install.{sh,ps1,bat}`). Defers bootstrap and portal entrypoints to ADR-0008.

## Context

Prior deployment options in the repository relied on multiple un-coordinated entry points (`build-mios.sh`, `mios-update`, `MiOS-Cat.sh`, standalone bootstrap scripts). This created fragmented CLI flags, duplicated target resolution logic, and increased user confusion regarding how to invoke live, container, or bare-metal installations.

The AGY tree consolidated these surfaces into `installation/mios-install.{sh,ps1,bat}` as a unified front-door dispatcher, but the decision needed formal architectural documentation.

## Decision

Consolidate all AGY deployment targets behind `installation/mios-install`:

1. **Dispatcher Architecture**:
   - `installation/mios-install` serves as a single entrypoint accepting targets: `live`, `xbox`, `fedora`, `bootc`, `oci`, `seed`, `flash`, `build`, `update`, `config`.
   - The dispatcher resolves parameters and delegates execution to existing specialized scripts (`build-mios.sh`, `mios-update`, etc.) via a shared library contract (`installation/mios-common.{sh,ps1}`).

2. **Dry-Run & Parity**:
   - Implements `--dry-run` to output execution plans without mutating the target system.
   - Parity between PowerShell and Bash wrappers is enforced via drift checks.

3. **Scope Boundaries**:
   - This decision applies strictly to the AGY `installation/` directory. Bootstrap and Portal surfaces (`MiOS-Cat`, `Get-MiOS.ps1`) remain governed by ADR-0008.

## Rationale

- Provides a predictable, single front door for all installation and update workflows.
- Eliminates code duplication by extracting shared path resolution and validation logic into `mios-common`.
- Preserves existing underlying entrypoints, minimizing breaking changes across automation pipelines.

## Alternatives

- **Monolithic Install Script**: Merging all install scripts into one giant file would create an unmaintainable codebase.
- **Multiple Disjoint Scripts**: Retaining uncoordinated entry points perpetuates flags drift and documentation rot.

## Consequences

### Positive
- Consistent CLI flags and help menus across Windows and Linux.
- Easy addition of new deployment targets via dispatcher route tables.
- Standardized dry-run execution planning.

### Negative
- Require maintaining parity between `.sh`, `.ps1`, and `.bat` wrapper frontends.

## Implementation

- Implemented in `installation/mios-install.sh`, `installation/mios-install.ps1`, and `installation/mios-install.bat`.
- Shared logic encapsulated in `installation/mios-common.sh` and `installation/mios-common.ps1`.

## References

- [ADR-0008: MiOS-Cat unified entry point](file:///C:/MiOS/usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md)
- [ADR-0009: Unified config surface](file:///C:/MiOS/usr/share/doc/mios/adr/0009-unified-config-surface.md)
- [Architectural Laws 1, 7, 8, 9](file:///C:/MiOS/usr/share/mios/mios.toml)
