<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone unit test for the...

!/usr/bin/env python3
AI-hint: Standalone unit test for the mios-daemon per-verb post-check after the NO-HARDCODE cutover. Proves the verb->check mapping is SSOT-driven (mios.toml [daemon.post_check]) not a code-baked dispatch map: the verb->signal table is READ from the layered toml (vendor value matches the shipped defaults), an unlisted verb degrades-open to checked=False, a NON-DEFAULT [daemon.post_check] layer changes which verbs get checked (behavior follows SSOT), and the check IMPLEMENTATIONS (file_exists / file_nonempty) still execute correctly when dispatched by signal name.
AI-related: ./mios-daemon, /usr/share/mios/mios.toml
AI-functions: _load, _write_toml, check, main

<!-- mios-src:87037ad8db55 from usr/libexec/mios/test_mios_daemon_postcheck.py:1-4 -->

