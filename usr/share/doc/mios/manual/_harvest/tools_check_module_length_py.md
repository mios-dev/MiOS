<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Module-size ratchet for the...

!/usr/bin/env python3
AI-hint: Module-size ratchet for the agent-pipe extraction (drift check 149). Walks usr/lib/mios/agent-pipe/mios_pipe RECURSIVELY (the bash predecessor scanned find -maxdepth 1, so it certified "all modules <= 800 lines" while eleven files 820-1786 lines long sat one directory deeper). A file not in [refactor].oversize must be <= max_lines; a file that IS listed must be <= its recorded length and is reported when it shrinks, so the register can only ratchet down. Prints one line per violation and exits 1; prints a one-line summary and exits 0 when clean.
AI-related: usr/share/mios/mios.toml [refactor], automation/98-drift-checks.sh, tools/test_check-module-length.py
AI-functions: load_policy, scan, main

<!-- mios-src:7f89d02a70a7 from tools/check-module-length.py:1-4 -->

