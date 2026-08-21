<!-- AI-hint: Manual pages distilled from the source comments of lib, sanitized, each passage anchored to the comment it came from. -->

# lib

### MiOS is cross-platform, and this module runs under pwsh on...

MiOS is cross-platform, and this module runs under pwsh on Linux too (CI
lints and Pester-tests it there). Every entry must therefore be built
defensively: on Linux $env:USERPROFILE is null, and `Join-Path $null ...`
throws ParameterBindingValidationException under StrictMode +
ErrorActionPreference='Stop', which took out the whole Pester suite.

Order mirrors the layered resolver contract used everywhere else in MiOS:
explicit env override, then user tier, then host tier, then vendor.

<!-- mios-src:59b5c506e354 from automation/lib/MiOS.Toml.psm1:14-21 -->

### A trailing '_' means the regex stopped on a non-name...

A trailing '_' means the regex stopped on a
non-name character, so this is a FRAGMENT, not a
variable: an f-string prefix (f"MIOS_A2A_{name}"),
a build-time template placeholder
(__MIOS_COCKPIT_PORT__), or a doc wildcard
(MIOS_COLOR_*). No emitted name ends in '_', so
these can never be satisfied and would wedge the
gate permanently.

<!-- mios-src:257291d28a99 from automation/lib/mios_var_closure.py:71-78 -->
