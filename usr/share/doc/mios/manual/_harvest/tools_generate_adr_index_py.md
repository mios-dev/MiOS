<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Generates the repo-root...

!/usr/bin/env python3
AI-hint: Generates the repo-root ADR.md breadcrumb from the front-matter of usr/share/doc/mios/adr/NNNN-*.md (T-265). The ADRs themselves stay baked under /usr per Law 1 -- a running MiOS carries its own why -- so this is a pointer, never a copy: one hop from either repo root to the index, a second to the decision itself. Derived, never hand-maintained (Law 8): check_adr_index regenerates and diffs it. --check exits 1 when the committed file is stale.
AI-related: usr/share/doc/mios/adr/, ADR.md, automation/98-drift-checks.sh, tools/test_generate-adr-index.py
AI-functions: parse_front_matter, collect, render, main

<!-- mios-src:d122786ab4f3 from tools/generate-adr-index.py:1-4 -->

