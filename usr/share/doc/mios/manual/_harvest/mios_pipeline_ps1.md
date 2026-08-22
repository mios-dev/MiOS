<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: The primary entry point for Windows hosts to execute the 11-phase MiOS build/install pipeline, orchestrating the transition from interactive configuration to Podman-WSL2 environment provisioning and package installation.
AI-related: mios-bootstrap, mios-user, mios-firstboot, mios-pipeline, mios-build-local, mios-install-YYYYMMDD-HHMMSS, mios-install
AI-functions: Test-MiOSAdmin, Test-MiOSInteractiveConsole, Write-PhaseBanner, Invoke-LegacyScript, Invoke-BuildScriptOnce, Invoke-PhaseQuestions, Invoke-PhaseStage, Invoke-PhaseDevDistro, Invoke-PhaseOverlay, Invoke-PhaseAccount, Invoke-PhaseInstall, Invoke-PhaseSmoketest

<!-- mios-src:5ccc74c8fe3e from mios-pipeline.ps1:1-3 -->

