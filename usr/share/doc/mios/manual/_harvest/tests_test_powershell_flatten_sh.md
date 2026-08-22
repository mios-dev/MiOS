<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Guards the object-pipeline...

!/usr/bin/env bash
AI-hint: Guards the object-pipeline flattening in usr/libexec/mios/mios-powershell (OAI-03). Two tiers: a stub-pwsh tier that always runs and asserts the wrapper the broker builds (Out-String width, PlainText rendering, `& '<staged script>'` call form, and that [powershell].flatten=false really removes them), and a live tier that runs a real pwsh and proves the defect it fixes -- with no console PowerShell sizes every formatter column against a window width of -1, so an object-returning cmdlet reaches the model as a BLANK LINE.
AI-related: usr/libexec/mios/mios-powershell, usr/share/mios/mios.toml, tests/powershell/run-pester.sh
AI-functions: log, die, ok, need, find_pwsh

<!-- mios-src:b0e2d2a92aa8 from tests/test-powershell-flatten.sh:1-4 -->

