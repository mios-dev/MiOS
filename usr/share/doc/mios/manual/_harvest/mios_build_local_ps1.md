<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Legacy PowerShell redirector that routes local build commands to build-mios.ps1 to maintain backward compatibility for existing MiOS build scripts and one-liners.
AI-related: mios-build-local
Requires -Version 5.1
'MiOS' Windows build orchestrator -- legacy redirector.

This file was renamed to build-mios.ps1 to align with the cross-platform
entry-point convention (build-mios.{sh,ps1}). This redirector exists so
existing irm | iex one-liners and shortcuts that point at the old
mios-build-local.ps1 URL keep working.

<!-- mios-src:9e1fcfb6164c from mios-build-local.ps1:1-9 -->

