<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for the...

!/usr/bin/env python3
AI-hint: Drift gate for the SSOT<->consumer contract. Shipped Python reads config as _toml_section("<table>").get("<key>"); this asserts that <table>.<key> actually EXISTS in mios.toml. When it does not the consumer silently takes its compiled default, so the SSOT and the code disagree in total silence and every test that stubs the value still passes. That is how nine security controls -- api_require_auth, principal_bind_mode, rule_of_two_mode, quarantine_mode, the firewall verb lists and the host allowlist -- sat unreachable under an unclosed [security.nohc_allowlist] header. A key declared elsewhere in the SSOT is MISPLACED; one declared nowhere is UNDECLARED. Both go in the shrink-only [ssot_consumers].unresolved register with a max_unresolved ratchet.
AI-related: usr/share/mios/mios.toml, tools/test_check-ssot-consumer-keys.py, usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py, automation/98-drift-checks.sh
AI-functions: consumer_reads, resolve, declared_elsewhere, register, max_unresolved, unresolved, violations, main

<!-- mios-src:53351c6b0fb9 from tools/check-ssot-consumer-keys.py:1-4 -->

