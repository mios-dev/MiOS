<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for render-globals.py -- proves shell and PowerShell constants are escaped so the generated resolvers always parse, that ${MIOS_X} templates stay live in both languages, and that dependency ordering puts a template after the name it references.
AI-related: tools/render-globals.py, automation/lib/globals.sh, automation/lib/globals.ps1
AI-functions: load_module, TestShAssign, TestPsAssign, TestOrdering, TestSanitize

<!-- mios-src:3e8cd568dfcd from tools/test_render_globals.py:1-4 -->

