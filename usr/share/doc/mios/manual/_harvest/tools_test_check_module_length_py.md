<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-module-length.py -- the agent-pipe module-size ratchet (check 149). Builds throwaway repo roots with a synthetic mios.toml [refactor] block and fake module files, and asserts all four directions: a NEW file over max_lines fails, a NESTED file over max_lines fails (the -maxdepth 1 blind spot the bash predecessor had), a grandfathered file at or below its recorded length passes, a grandfathered file that GREW fails, a grandfathered file that SHRANK fails so the register ratchets down, and a stale register entry naming a deleted file fails. Run: python3 test_check-module-length.py
AI-related: ./check-module-length.py, usr/share/mios/mios.toml [refactor]
AI-functions: mkroot, run, main

<!-- mios-src:f5757ee286bb from tools/test_check-module-length.py:1-4 -->

