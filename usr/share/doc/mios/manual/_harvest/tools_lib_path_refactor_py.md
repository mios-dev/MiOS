<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Refactors hardcoded MiOS...

!/usr/bin/env python3
AI-hint: Refactors hardcoded MiOS system paths into environment variable constants (e.g., ${MIOS_LOG_DIR}) in configuration files while preserving comments and bootstrap logic.
AI-related: .../paths.sh, /usr/lib/mios/logs, mios-foo
AI-functions: substitute_line, process

<!-- mios-src:cff47e9e92af from tools/lib/path-refactor.py:1-4 -->

