<#
.SYNOPSIS
    MiOS canonical end-to-end pipeline orchestrator (Windows host).

.DESCRIPTION
    Single linear 11-phase chain. Replaces the historical tangle of
    build-mios.ps1 + install.ps1 + Get-MiOS.ps1 + preflight.ps1 +
    bootstrap.* as the user-facing entry point. The legacy scripts
    remain on disk as workers; this orchestrator calls them in the
    canonical order with clear phase boundaries.

    THE 11-PHASE CHAIN
    ---------------------------------------------------------------------
     1. Questions   Interactive prompts -> mios.toml (vendor + host +
                    user layered overlay). Source of truth for every
                    other phase. Re-runnable: existing answers are
                    pre-filled; -NoPrompt skips and uses on-disk values.
     2. Stage       Clone mios.git + mios-bootstrap.git, run
                    seed-merge.{sh,ps1} (mios-bootstrap onto mios.git
                    working tree), prepare %APPDATA%\MiOS\repo as the
                    canonical build context.
     3. MiOS-DEV    Create the Podman-WSL2 backend distro
                    (formerly MiOS-BUILDER). Imports the rootfs once
                    and registers the WSL distro; idempotent on re-run.
     4. Overlay     Apply usr/, etc/, var/ overlays from the staged
                    repo into MiOS-DEV via Invoke-MiosOverlaySeed.
                    Applies mios.toml [packages.dev_overlay] sections
                    LIVE so the dev distro tracks the same package set
                    its build-target images do.
     5. Account     Native Fedora user account creation at OVERLAY
                    TIME (per the project's "no firstboot patching"
                    feedback): systemd-sysusers materializes
                    /etc/passwd + /etc/group; automation/31-user.sh
                    bakes /etc/subuid + /etc/subgid + password hash;
                    /usr/lib/tmpfiles.d/mios-user.conf seeds /var/home
                    + linger marker at first boot declaratively.
     6. Install     Package install per mios.toml [packages].sections.
                    Uses automation/lib/packages.sh as the resolver,
                    reading the layered TOML chain (vendor < host <
                    user). Strict on missing packages.
     7. Smoketest   automation/99-postcheck.sh: image lint, SBOM
                    presence check, sigstore policy validation,
                    architectural-law audits (#1-#12), container/Quadlet
                    coverage, file-perm normalization.
     8. Build       OCI build: `podman build` against ./Containerfile,
                    producing localhost/mios:latest. Then bib for the
                    full deployable suite -- qcow2, vhdx, wsl tar, iso,
                    raw -- under %DOCUMENTS%\MiOS\images\.
     9. Deploy      Pick the locally-compatible images and stage them:
                       * Hyper-V available  -> import vhdx as MiOS VM
                       * KVM/libvirt        -> import qcow2
                       * Plain Windows host -> register WSL2 tar as MiOS
                       * USB requested      -> dd iso to a removable
                    Operator confirms before any non-reversible step.
    10. Boot        First-boot the chosen deployment. systemd-tmpfiles
                    materializes user state (Phase-5's declarative
                    work); Quadlets pull their images; mios-firstboot
                    target completes.
    11. Repeat      Print a short re-run hint. The chain is fully
                    idempotent; re-running picks up incremental
                    changes (mios.toml edits, automation script
                    updates, new packages) without a full rebuild.

    USAGE
    ---------------------------------------------------------------------
        # Full chain end-to-end (default):
        ./mios-pipeline.ps1

        # Single phase:
        ./mios-pipeline.ps1 -Phase 5

        # Resume from a phase (e.g. after a failure):
        ./mios-pipeline.ps1 -From 7

        # Stop at a phase:
        ./mios-pipeline.ps1 -To 6

        # List the chain and exit:
        ./mios-pipeline.ps1 -ListPhases

        # Non-interactive (CI / unattended; uses on-disk mios.toml):
        ./mios-pipeline.ps1 -NoPrompt

    LEGACY ENTRY POINTS
    ---------------------------------------------------------------------
    The following remain functional as workers but are no longer the
    operator-facing entry point:

        build-mios.ps1            -> dispatched by Phase 1-8
        install.ps1               -> dispatched by Phase 9-10
        Get-MiOS.ps1              -> dispatched by Phase 8 (image pull)
        preflight.ps1             -> dispatched by Phase 1 (prerequisite check)
        mios-build-local.ps1      -> redirector to build-mios.ps1 (kept for old URLs)
        Justfile                  -> per-target invocations from Phase 8

    A future cleanup pass will fold their unique logic into this
    orchestrator's phase functions and reduce them to thin redirector
    stubs. Until then, the chain calls them in the canonical order
    documented above.

.PARAMETER Phase
    Run only the specified phase number (1-11) and exit.

.PARAMETER From
    Resume the chain starting at the specified phase (inclusive).

.PARAMETER To
    Stop the chain after the specified phase (inclusive).

.PARAMETER ListPhases
    Print the phase index and exit without running anything.

.PARAMETER NoPrompt
    Run non-interactively; use on-disk mios.toml values for every
    decision and abort if a required value is missing.

.EXAMPLE
    ./mios-pipeline.ps1
    Run the full 11-phase chain.

.EXAMPLE
    ./mios-pipeline.ps1 -From 4 -To 7
    Re-run the dev-overlay + install + smoketest section after editing
    mios.toml [packages].
#>
#Requires -Version 7.1
[CmdletBinding()]
param(
    [ValidateRange(1,11)] [int]$Phase = 0,
    [ValidateRange(1,11)] [int]$From  = 1,
    [ValidateRange(1,11)] [int]$To    = 11,
    [switch]$ListPhases,
    [switch]$NoPrompt
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Acknowledgment gate (the canonical thorough version, with the MiOS
# ASCII banner and Acknowledged/No-thanks choice). Same as every other
# entry point in the project.
$_bannerPath = Join-Path -Path $PSScriptRoot -ChildPath 'automation/lib/agreements-banner.ps1'
if (Test-Path $_bannerPath) {
    . $_bannerPath; Invoke-MiOSAgreementBanner -Entry 'mios-pipeline.ps1'
}

# ── Admin elevation (centralized) ────────────────────────────────────
# Both build-mios.ps1 and install.ps1 historically self-elevated mid-
# chain via Start-Process -Verb RunAs, then `return`-ed from the un-
# elevated copy. That pattern silently breaks under any non-interactive
# parent (CI, agent-driven runs, this orchestrator under a captured
# stdout): the elevated copy spawns a UAC consent prompt the parent
# can't see / accept, the un-elevated copy exits 0, and the pipeline
# happily marches forward against an empty deployment.
#
# Lift the check to here and elevate the WHOLE chain once, passing
# every arg + relevant env var through. build-mios.ps1 and install.ps1
# detect MIOS_PIPELINE_ELEVATED=1 and skip their own self-elevation,
# so the chain runs in one elevated process from start to finish.
function Test-MiOSAdmin {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()) `
        .IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-MiOSInteractiveConsole {
    if ($env:CI -or $env:GITHUB_ACTIONS) { return $false }
    try {
        $null = [Console]::CursorTop
        return [Environment]::UserInteractive -and ($Host.Name -ne 'Default Host')
    } catch {
        return $false
    }
}

if (-not $env:MIOS_PIPELINE_ELEVATED) {
    if (Test-MiOSAdmin) {
        $env:MIOS_PIPELINE_ELEVATED = '1'
    } elseif (Test-MiOSInteractiveConsole) {
        Write-Host '[mios-pipeline] elevating to Administrator (UAC prompt)...' -ForegroundColor Yellow
        $argList = @(
            '-NoProfile',
            '-ExecutionPolicy','Bypass',
            '-File', $PSCommandPath
        )
        if ($Phase)      { $argList += @('-Phase', "$Phase") }
        if ($From -ne 1) { $argList += @('-From',  "$From")  }
        if ($To   -ne 11){ $argList += @('-To',    "$To")    }
        if ($ListPhases) { $argList += '-ListPhases' }
        if ($NoPrompt)   { $argList += '-NoPrompt' }
        $env:MIOS_PIPELINE_ELEVATED = '1'
        # -Wait so the un-elevated parent observes the real exit code
        # of the elevated child. Without it the elevated process becomes
        # an orphan and we'd return 0 the moment UAC dispatches it.
        $proc = Start-Process pwsh -ArgumentList $argList -Verb RunAs -Wait -PassThru
        exit $proc.ExitCode
    } else {
        Write-Host '[mios-pipeline] FATAL: not running as Administrator and no interactive console available to elevate.' -ForegroundColor Red
        Write-Host '                Re-run from a foreground PowerShell window opened "Run as administrator", or' -ForegroundColor Red
        Write-Host '                from an already-elevated parent process.' -ForegroundColor Red
        exit 1
    }
}

# ── Unified global flattened log file ────────────────────────────────
# Single log file per pipeline invocation, captured at the orchestrator
# level (not per-phase) so that every line of every legacy worker
# (build-mios.ps1, install.ps1, Get-MiOS.ps1, ...) and every native
# command they shell out to (wsl.exe, podman, bib, ...) lands in one
# flat chronologically-interleaved file at a stable, predictable path.
#
#   M:\MiOS\logs\mios-install-YYYYMMDD-HHMMSS.log    per-invocation
#   M:\MiOS\logs\latest.log                          copy of most recent
#
# (The exact drive depends on $PSScriptRoot; on a typical Windows host
# after Phase-2 migration this resolves to M:\MiOS\logs\, which the
# build dashboard already advertises as the canonical log location.)
#
# Transcript captures Write-Host / Write-Output / Write-Error / Verbose
# / Warning + native-command stdout that the orchestrator dispatches
# via `&`, so this single file is everything the operator needs to
# diagnose a failed run -- no scattered phase logs.
$script:MiosLogDir  = Join-Path -Path $PSScriptRoot -ChildPath 'logs'
$script:MiosLogFile = $null
$script:MiosLogOK   = $false
try {
    if (-not (Test-Path -LiteralPath $script:MiosLogDir)) {
        New-Item -Path $script:MiosLogDir -ItemType Directory -Force | Out-Null
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $script:MiosLogFile = Join-Path -Path $script:MiosLogDir -ChildPath ("mios-install-{0}.log" -f $stamp)
    Start-Transcript -Path $script:MiosLogFile -Force | Out-Null
    $script:MiosLogOK = $true
    Write-Host ('[mios-pipeline] unified log: {0}' -f $script:MiosLogFile) -ForegroundColor DarkGray
} catch {
    # Some constrained-language hosts reject Start-Transcript; emit a
    # warning rather than failing the whole pipeline -- a missing log
    # file is far less important than a missing build.
    Write-Host ('[mios-pipeline] WARN: Start-Transcript failed ({0}); continuing without unified log.' -f $_.Exception.Message) -ForegroundColor DarkYellow
}

# ── Phase index ──────────────────────────────────────────────────────
$Phases = @(
    [pscustomobject]@{Id=1;  Name='Questions';  Desc='Interactive prompts -> mios.toml'                              ; Fn={ Invoke-PhaseQuestions  } }
    [pscustomobject]@{Id=2;  Name='Stage';      Desc='Clone + seed-merge + prepare build context'                    ; Fn={ Invoke-PhaseStage      } }
    [pscustomobject]@{Id=3;  Name='MiOS-DEV';   Desc='Create the Podman-WSL2 backend distro'                         ; Fn={ Invoke-PhaseDevDistro  } }
    [pscustomobject]@{Id=4;  Name='Overlay';    Desc='Apply rootfs overlay into MiOS-DEV'                            ; Fn={ Invoke-PhaseOverlay    } }
    [pscustomobject]@{Id=5;  Name='Account';    Desc='Overlay-time user provisioning (sysusers + tmpfiles)'          ; Fn={ Invoke-PhaseAccount    } }
    [pscustomobject]@{Id=6;  Name='Install';    Desc='Package install per mios.toml [packages]'                      ; Fn={ Invoke-PhaseInstall    } }
    [pscustomobject]@{Id=7;  Name='Smoketest';  Desc='postcheck.sh + lint + arch-law audits'                         ; Fn={ Invoke-PhaseSmoketest  } }
    [pscustomobject]@{Id=8;  Name='Build';      Desc='OCI build + bib for qcow2/vhdx/wsl/iso/raw'                    ; Fn={ Invoke-PhaseBuild      } }
    [pscustomobject]@{Id=9;  Name='Deploy';     Desc='Pick + stage host-compatible image'                            ; Fn={ Invoke-PhaseDeploy     } }
    [pscustomobject]@{Id=10; Name='Boot';       Desc='First-boot the deployed image'                                 ; Fn={ Invoke-PhaseBoot       } }
    [pscustomobject]@{Id=11; Name='Repeat';     Desc='Print re-run hint and exit'                                    ; Fn={ Invoke-PhaseRepeat     } }
)

function Write-PhaseBanner {
    param([int]$Id, [string]$Name, [string]$Desc)
    $bar = '=' * 78
    Write-Host ''
    Write-Host $bar -ForegroundColor DarkGray
    Write-Host (' Phase {0,2}/11 -- {1,-12} {2}' -f $Id, $Name, $Desc) -ForegroundColor Cyan
    Write-Host $bar -ForegroundColor DarkGray
}

function Invoke-LegacyScript {
    param([string]$Script, [string[]]$ScriptArgs = @())
    $path = Join-Path -Path $PSScriptRoot -ChildPath $Script
    if (-not (Test-Path $path)) {
        throw "Pipeline expected legacy worker at $path but it was not found."
    }
    & pwsh -NoProfile -ExecutionPolicy Bypass -File $path @ScriptArgs
    if ($LASTEXITCODE -ne 0) { throw "$Script failed with exit $LASTEXITCODE" }
}

# ── Phase function bodies ────────────────────────────────────────────
# Each phase is a thin dispatcher to existing automation.
#
# IMPLEMENTATION NOTE -- TODAY'S COUPLING vs FUTURE STATE
# build-mios.ps1 today is monolithic: a single invocation runs Phases
# 1-8 internally (questions -> stage -> dev-distro -> overlay -> account
# -> install -> smoketest -> build). The phase functions for those IDs
# all delegate to the same script; running `--phase 4` invokes
# build-mios.ps1 in full because no per-phase entry exists yet. This
# is acknowledged in the chain documentation above and will be split
# as the legacy script is decomposed. Phases 9-11 are independently
# dispatchable today -- they correspond to install.ps1 + boot helpers.

$script:_BuildScriptInvoked = $false

function Invoke-BuildScriptOnce {
    # Phases 1-8 share build-mios.ps1; calling it more than once per
    # pipeline run would re-do all the work. Guard with a per-process
    # sentinel.
    if ($script:_BuildScriptInvoked) {
        Write-Host '   (build-mios.ps1 already ran in this pipeline invocation; skipping)' -ForegroundColor DarkYellow
        return
    }
    $args = @()
    if ($NoPrompt) { $args += '-AutoInstall' }
    Invoke-LegacyScript -Script 'build-mios.ps1' -ScriptArgs $args
    $script:_BuildScriptInvoked = $true
}

function Invoke-PhaseQuestions {
    Write-Host '[mios-pipeline] resolving mios.toml and prompting for missing values...' -ForegroundColor Yellow
    Invoke-BuildScriptOnce
}
function Invoke-PhaseStage     { Write-Host '[mios-pipeline] cloning + seed-merging build context...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }
function Invoke-PhaseDevDistro { Write-Host '[mios-pipeline] creating MiOS-DEV (Podman-WSL2 backend)...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }
function Invoke-PhaseOverlay   { Write-Host '[mios-pipeline] overlaying rootfs into MiOS-DEV...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }
function Invoke-PhaseAccount   { Write-Host '[mios-pipeline] account creation (sysusers + tmpfiles, overlay-time)...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }
function Invoke-PhaseInstall   { Write-Host '[mios-pipeline] installing packages per mios.toml [packages]...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }
function Invoke-PhaseSmoketest { Write-Host '[mios-pipeline] running smoke tests (postcheck + lint)...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }
function Invoke-PhaseBuild     { Write-Host '[mios-pipeline] building OCI image + full deployable suite...' -ForegroundColor Yellow; Invoke-BuildScriptOnce }

function Invoke-PhaseDeploy {
    Write-Host '[mios-pipeline] deploying host-compatible image...' -ForegroundColor Yellow
    # install.ps1 has its own credential / hostname prompts that block
    # background pipeline invocation. -NoPrompt at the pipeline level
    # implies "use defaults for everything"; surface that to install.ps1
    # via MIOS_AUTOINSTALL=1, which it already honors for password +
    # hostname (and now also username + GHCR token).
    if ($NoPrompt -and -not $env:MIOS_AUTOINSTALL) {
        $env:MIOS_AUTOINSTALL = '1'
    }
    Invoke-LegacyScript -Script 'install.ps1' -ScriptArgs @()
}

function Invoke-PhaseBoot {
    Write-Host '[mios-pipeline] first-booting the deployed image...' -ForegroundColor Yellow
    # Auto-detection of the deployed shape so the user does not need
    # to track which image went where. WSL is checked first because
    # `wsl --list` is fast and unambiguous; libvirt + Hyper-V follow.
    if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
        $distros = & wsl.exe --list --quiet 2>$null
        if ($distros -and ($distros -split "`n") -match '^MiOS\s*$') {
            Write-Host '   booting MiOS WSL distro...' -ForegroundColor Yellow
            & wsl.exe -d MiOS
            return
        }
    }
    if (Get-Command Get-VM -ErrorAction SilentlyContinue) {
        $vm = Get-VM -Name MiOS -ErrorAction SilentlyContinue
        if ($vm) {
            Write-Host '   starting Hyper-V VM `MiOS`...' -ForegroundColor Yellow
            Start-VM -Name MiOS
            return
        }
    }
    Write-Host '   no recognized MiOS deployment found on this host;' -ForegroundColor DarkYellow
    Write-Host '   re-run -Phase 9 to register one, then -Phase 10.' -ForegroundColor DarkYellow
}

function Invoke-PhaseRepeat {
    Write-Host ''
    Write-Host '╔══════════════════════════════════════════════════════════════════════════╗' -ForegroundColor Green
    Write-Host '║  MiOS pipeline complete.                                                  ║' -ForegroundColor Green
    Write-Host '║                                                                            ║' -ForegroundColor Green
    Write-Host '║  Re-run any time:                                                          ║' -ForegroundColor Green
    Write-Host '║      ./mios-pipeline.ps1                  full chain (idempotent)          ║' -ForegroundColor Green
    Write-Host '║      ./mios-pipeline.ps1 -From 4          incremental: re-overlay +deploy  ║' -ForegroundColor Green
    Write-Host '║      ./mios-pipeline.ps1 -Phase 8         rebuild image suite only         ║' -ForegroundColor Green
    Write-Host '║                                                                            ║' -ForegroundColor Green
    Write-Host '║  Operator changes propagate via:                                           ║' -ForegroundColor Green
    Write-Host '║      $env:APPDATA\MiOS\mios.toml          host-layer overlay               ║' -ForegroundColor Green
    Write-Host '║      ~/.config/mios/mios.toml             per-user overlay                 ║' -ForegroundColor Green
    Write-Host '╚══════════════════════════════════════════════════════════════════════════╝' -ForegroundColor Green
}

# ── Dispatch ─────────────────────────────────────────────────────────
if ($ListPhases) {
    Write-Host ''
    Write-Host 'MiOS pipeline phases (canonical 11-phase chain):' -ForegroundColor Cyan
    Write-Host ''
    foreach ($p in $Phases) {
        '  {0,2}. {1,-12} {2}' -f $p.Id, $p.Name, $p.Desc
    }
    Write-Host ''
    return
}

# Phase shorthand: -Phase N == -From N -To N
if ($Phase -ne 0) {
    $From = $Phase
    $To   = $Phase
}
if ($From -gt $To) {
    throw "From ($From) cannot be greater than To ($To)."
}

$selected = $Phases | Where-Object { $_.Id -ge $From -and $_.Id -le $To }
try {
    foreach ($p in $selected) {
        Write-PhaseBanner -Id $p.Id -Name $p.Name -Desc $p.Desc
        & $p.Fn
    }
} finally {
    # Always stop the unified log -- even on phase failure -- so the
    # operator gets a complete record of what ran before the abort.
    if ($script:MiosLogOK) {
        try { Stop-Transcript | Out-Null } catch { }
        # Refresh the `latest.log` pointer to the just-finished run so
        # any post-build helper that wants "the most recent log" has a
        # stable target. Plain Copy-Item rather than a symlink because
        # symlink creation requires Developer Mode or admin token,
        # neither of which we want to require here.
        try {
            $latest = Join-Path -Path $script:MiosLogDir -ChildPath 'latest.log'
            Copy-Item -LiteralPath $script:MiosLogFile -Destination $latest -Force -ErrorAction Stop
        } catch { }
        Write-Host ('[mios-pipeline] log written: {0}' -f $script:MiosLogFile) -ForegroundColor Green
    }
}
