<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: GENERATED IN FULL from usr/share/mios/mios.toml by tools/render-globals.py. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
AI-related: usr/share/mios/mios.toml, automation/lib/globals.sh, tools/render-globals.py
AI-functions: Resolve-MiosVersion

PowerShell sibling of automation/lib/globals.sh -- both are rendered from the
same SSOT by the same generator, so they cannot diverge. Dot-source from any
entry point:

    . (Join-Path $PSScriptRoot 'automation/lib/globals.ps1')

Override any constant with an environment variable BEFORE dot-sourcing -- e.g.
`$env:MIOS_VERSION = ' - rc1'; . globals.ps1`.

<!-- mios-src:03d54d6ab97e from automation/lib/globals.ps1:1-12 -->

