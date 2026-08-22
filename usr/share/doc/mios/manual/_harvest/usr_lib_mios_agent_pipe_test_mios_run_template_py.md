<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_pipe.routing.run_template -- the WS-6 capture half plus the T-225 replay read side, extracted out of dag_exec. Proves the structural plan-shape class is phrasing-independent and edge-count sensitive, that a captured row carries a NON-EMPTY intent key and is matchable by the very turn that produced it (an empty key silently kills replay while looking wired), that an empty DAG and a disabled flag both write nothing, and that load_run_templates filters to keyed rows, honours the limit, and degrades open on a read failure rather than raising into the planner.
AI-related: ./mios_pipe/routing/run_template.py, ./mios_pipe/routing/replay.py, ./mios_pipe/routing/dag_exec.py, /usr/share/mios/postgres/schema-init.sql
AI-functions: check, t_class, t_capture, t_capture_disabled, t_load, main

<!-- mios-src:ab1beb35209c from usr/lib/mios/agent-pipe/test_mios_run_template.py:1-4 -->

