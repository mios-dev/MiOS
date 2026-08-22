<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Isolation tests for...

!/usr/bin/env python3
AI-hint: Isolation tests for mios_pipe.routing.dispatch_cmd -- the verb->bash command BUILDER extracted from the dispatch chokepoint (T-273). Imported directly, never through mios_dispatch, so it proves the extraction really is standalone: configure() alone is enough to drive it. Covers the sandbox OPT-IN gate that keeps launch/OS-control verbs (which bwrap would break) from ever being wrapped, docker->podman + tty normalisation, template rendering through the injected catalog, and the unknown-verb None. The chokepoint-level tests (taint, HITL, Rule-of-Two, quarantine, broker I/O) stay in test_mios_dispatch.py. Run: python3 test_mios_dispatch_cmd.py
AI-related: ./mios_pipe/routing/dispatch_cmd.py, ./mios_dispatch.py, ./test_mios_dispatch.py
AI-functions: main

<!-- mios-src:7fa8ce172148 from usr/lib/mios/agent-pipe/test_mios_dispatch_cmd.py:1-4 -->

