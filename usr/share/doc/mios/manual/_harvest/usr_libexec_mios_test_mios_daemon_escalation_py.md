<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone unit test for the...

!/usr/bin/env python3
AI-hint: Standalone unit test for the mios-daemon escalation governor (GUARD-01): loads the hyphenated CLI by path with its side-effecting main guarded, then asserts _escalation_allowed enforces escalation_cooldown_s, parks a concern after escalation_max_attempts, keeps distinct concerns independent, and degrades open when the cooldown is non-positive.
AI-related: /usr/libexec/mios/mios-daemon, /usr/share/mios/mios.toml, mios-daemon.service

<!-- mios-src:e8db5dc06f70 from usr/libexec/mios/test_mios_daemon_escalation.py:1-3 -->

