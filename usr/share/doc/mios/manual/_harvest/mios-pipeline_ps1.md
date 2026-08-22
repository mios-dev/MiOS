<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Requires -Version 7.1

>
Requires -Version 7.1

<!-- mios-src:eb77760c7a6e from mios-pipeline.ps1:127-128 -->

### ── Admin elevation (centralized)...

── Admin elevation (centralized) ────────────────────────────────────
Both build-mios.ps1 and install.ps1 historically self-elevated mid-
chain via Start-Process -Verb RunAs, then `return`-ed from the un-
elevated copy. That pattern silently breaks under any non-interactive
parent (CI, agent-driven runs, this orchestrator under a captured
stdout): the elevated copy spawns a UAC consent prompt the parent
can't see / accept, the un-elevated copy exits 0, and the pipeline
happily marches forward against an empty deployment.

Lift the check to here and elevate the WHOLE chain once, passing
every arg + relevant env var through. build-mios.ps1 and install.ps1
detect MIOS_PIPELINE_ELEVATED=1 and skip their own self-elevation,
so the chain runs in one elevated process from start to finish.

<!-- mios-src:b77a676aae79 from mios-pipeline.ps1:149-161 -->

### ── Unified global flattened log file...

── Unified global flattened log file ────────────────────────────────
Single log file per pipeline invocation, captured at the orchestrator
level (not per-phase) so that every line of every legacy worker
(build-mios.ps1, install.ps1, Get-MiOS.ps1, ...) and every native
command they shell out to (wsl.exe, podman, bib, ...) lands in one
flat chronologically-interleaved file at a stable, predictable path.

  M:\MiOS\logs\mios-install-YYYYMMDD-HHMMSS.log    per-invocation
  M:\MiOS\logs\latest.log                          copy of most recent

(The exact drive depends on $PSScriptRoot; on a typical Windows host
after Phase-2 migration this resolves to M:\MiOS\logs\, which the
build dashboard already advertises as the canonical log location.)

Transcript captures Write-Host / Write-Output / Write-Error / Verbose
/ Warning + native-command stdout that the orchestrator dispatches
via `&`, so this single file is everything the operator needs to
diagnose a failed run -- no scattered phase logs.

<!-- mios-src:e611f8c8f9b3 from mios-pipeline.ps1:205-222 -->

### ── Phase function bodies...

── Phase function bodies ────────────────────────────────────────────
Each phase is a thin dispatcher to existing automation.

IMPLEMENTATION NOTE -- TODAY'S COUPLING vs FUTURE STATE
build-mios.ps1 today is monolithic: a single invocation runs Phases
1-8 internally (questions -> stage -> dev-distro -> overlay -> account
-> install -> smoketest -> build). The phase functions for those IDs
all delegate to the same script; running `--phase 4` invokes
build-mios.ps1 in full because no per-phase entry exists yet. This
is acknowledged in the chain documentation above and will be split
as the legacy script is decomposed. Phases 9-11 are independently
dispatchable today -- they correspond to install.ps1 + boot helpers.

<!-- mios-src:f65ffa437a6e from mios-pipeline.ps1:276-287 -->
