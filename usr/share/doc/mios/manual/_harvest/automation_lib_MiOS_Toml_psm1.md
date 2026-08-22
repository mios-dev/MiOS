<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### MiOS is cross-platform, and this module runs under pwsh on...

MiOS is cross-platform, and this module runs under pwsh on Linux too (CI
lints and Pester-tests it there). Every entry must therefore be built
defensively: on Linux $env:USERPROFILE is null, and `Join-Path $null ...`
throws ParameterBindingValidationException under StrictMode +
ErrorActionPreference='Stop', which took out the whole Pester suite.

Order mirrors the layered resolver contract used everywhere else in MiOS:
explicit env override, then user tier, then host tier, then vendor.

<!-- mios-src:59b5c506e354 from automation/lib/MiOS.Toml.psm1:14-21 -->
