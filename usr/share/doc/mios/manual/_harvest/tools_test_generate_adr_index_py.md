<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/generate-adr-index.py (T-265). Builds throwaway ADR trees and asserts: front-matter scalars and [a, b] lists parse, a file without an `adr:` key is skipped, ordering follows the filename number, the rendered table links every ADR at usr/share/doc/mios/adr/ (a pointer, never a copy -- Law 1 keeps the records baked), --check exits 0 on a fresh file, 1 on a stale one and 1 when the file is missing, and generation is idempotent so the drift gate can regenerate-and-diff. Run: python3 test_generate-adr-index.py
AI-related: ./generate-adr-index.py, ADR.md, usr/share/doc/mios/adr/
AI-functions: mkroot, main

<!-- mios-src:a360d87047c4 from tools/test_generate-adr-index.py:1-4 -->

