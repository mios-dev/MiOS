<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Link-integrity gate for the...

!/usr/bin/env python3
AI-hint: Link-integrity gate for the shipped docs. (1) Every ToC link in usr/share/doc/mios/manual.md resolves to an existing chapter file and, where a fragment is given, a real anchor, and no chapter is unreachable from the ToC. (2) Every EXPLICITLY relative link (./x, ../x) anywhere under usr/share/doc/mios resolves -- that class has exactly one meaning, unlike a repo-root-relative path, and it is how audit-INDEX.md kept pointing at audit-mios-mini.md for the whole time after that name was reassigned to MiOS-Metal.
AI-related: usr/share/doc/mios/manual.md, usr/share/doc/mios/manual, usr/libexec/mios/mios-manual, automation/98-drift-checks.sh

<!-- mios-src:9fd140c671ed from tools/check-manual-links.py:1-3 -->

