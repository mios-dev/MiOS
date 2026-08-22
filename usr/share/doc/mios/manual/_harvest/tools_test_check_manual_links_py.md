<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-manual-links.py: builds throwaway manual trees in a temp dir and asserts the gate exits 0 on a clean ToC and non-zero on a dangling chapter link, a missing anchor, an unreachable chapter file, and a dangling EXPLICITLY-relative link anywhere in the docs tree -- while a repo-root-relative path (usr/share/...) stays out of scope, since resolving those as file-relative would invent ~190 false findings.
AI-related: tools/check-manual-links.py, automation/98-drift-checks.sh, usr/share/doc/mios/manual.md

<!-- mios-src:f43192ddb729 from tools/test_check-manual-links.py:1-3 -->

