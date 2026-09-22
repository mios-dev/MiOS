<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### GENERATED IN FULL from usr/share/mios/mios.toml by...

GENERATED IN FULL from usr/share/mios/mios.toml by tools/render-globals.py. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
AI-related: usr/share/mios/mios.toml, automation/lib/globals.sh, tools/render-globals.py
AI-functions: Resolve-MiosVersion

PowerShell sibling of automation/lib/globals.sh -- both are rendered from the
same SSOT by the same generator, so they cannot diverge. Dot-source from any
entry point:

    . (Join-Path $PSScriptRoot 'automation/lib/globals.ps1')

Override any constant with an environment variable BEFORE dot-sourcing -- e.g.
`$env:MIOS_VERSION = ' - rc1'; . globals.ps1`.

<!-- mios-src:ab0c43f38a23 from automation/lib/globals.ps1:1-12 -->

### !/usr/bin/env bash GENERATED IN FULL from...

!/usr/bin/env bash
GENERATED IN FULL from usr/share/mios/mios.toml by tools/render-globals.py. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
AI-related: usr/share/mios/mios.toml, automation/lib/globals.ps1, tools/render-globals.py
AI-functions: _mios_resolve_version

Shell sibling of automation/lib/globals.ps1 -- both are rendered from the same
SSOT by the same generator, so they cannot diverge. Dot-source from any entry
point; every constant uses `:=` so an environment variable exported BEFORE
sourcing still wins.

<!-- mios-src:158168333d31 from automation/lib/globals.sh:1-9 -->

### !/usr/bin/env bash AI-hint: Shared container-runtime...

!/usr/bin/env bash
AI-hint: Shared container-runtime, registry and image helpers for the workflows, so both publishers execute one implementation.
AI-related: .github/workflows/mios-ci.yml, .forgejo/workflows/build-mios.yml, tools/lib/userenv.sh

Every function here replaced a block that had been pasted into two or more
workflow steps. The registry-name validation existed four times, the storage
configuration twice, the label verification twice, and the version parse three
times; the copies had already diverged. Source this instead.

shellcheck shell=bash

<!-- mios-src:6516484e61ee from tools/lib/ci-runtime.sh:1-10 -->
