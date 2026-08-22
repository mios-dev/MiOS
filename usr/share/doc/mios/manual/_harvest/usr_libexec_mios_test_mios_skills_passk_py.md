<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone unit test for the...

!/usr/bin/env python3
AI-hint: Standalone unit test for the T-049 (GAP-3) hard pass^k skill-promotion gate embedded in the hyphenated `mios-skills` CLI. Loads the CLI via SourceFileLoader (stdlib, no server/DB/network/pytest) and proves: (1) the per-replay predicate _passk_run_ok reads ONLY structured fields -- success must be true AND no step carries a firewall_blocked/hitl_blocked marker; (2) _passk_gate is all-or-nothing -- 3/3 passes, a 1-of-3 failure vetoes with the "n/k succeeded, required k/k" message, and an unreachable (raising) replay is fail-closed; (3) cmd_promote is DEGRADE-OPEN -- gate OFF promotes without any replay (byte-identical legacy behaviour), gate ON promotes only when every replay passes and otherwise never flips status; (4) --dgm selects the stricter DGM replay count. The /skills/run HTTP hop (_post_skill_run) and the DB status write (_update_status) are stubbed.
AI-related: ./mios-skills, /usr/share/mios/mios.toml
AI-functions: _load, check, stub_run, main

<!-- mios-src:cebb76d172f0 from usr/libexec/mios/test_mios_skills_passk.py:1-4 -->

