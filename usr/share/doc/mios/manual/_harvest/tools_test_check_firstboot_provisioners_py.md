<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-firstboot-provisioners.py. Builds throwaway repo roots holding a synthetic fetcher/unit/preset/tmpfiles set and asserts each half-wiring is caught: a missing fetcher, an ExecStart pointing at something else, no ConditionPathExists gate (so the oneshot re-runs every boot), a gate naming a sentinel path the fetcher never writes (so the unit runs forever), a unit absent from the preset (installed but never started), and a /var dir the fetcher writes that no tmpfiles.d file declares (Law 2). Also asserts a whole triple passes. Run: python3 test_check-firstboot-provisioners.py
AI-related: ./check-firstboot-provisioners.py
AI-functions: mkroot, run, main

<!-- mios-src:2db2682db437 from tools/test_check-firstboot-provisioners.py:1-4 -->

