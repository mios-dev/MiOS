<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_memguard (WS-MEM-VALIDATE / OWASP ASI08 write-time memory-poisoning guard, de-hardcoded to a MODEL-driven severity judge). Pure stdlib, no server.py/DB/real-network/pytest. Verifies (1) the PURE structural scan flags only language-neutral SHAPES (control-token delimiter -> HIGH escalation, inert URL/code-fence -> LOW, clean -> NONE) and carries NO English keyword/phrase gate (a plain-prose injection sentence is NOT structurally HIGH; _INJECTION/_DANGER_CODE no longer exist); (2) the MODEL path -- validate_for_store awaits the stubbed _judge_severity so a PARAPHRASED injection the old regex missed is rejected, judge:low stores, and the judge flag is recorded; (3) the DEGRADE path -- judge None (lane down) falls back to the structural verdict (control-token still escalates, benign + plain-prose injection still store -- proving no keyword list drives the degrade decision); (4) judge_mode off skips the model; (5) the policy modes (off/log/strip/reject) + fail-open contract.
AI-related: ./mios_memguard.py
AI-functions: check, run, t_scan_structural, t_model_driven, t_degrade_failsafe, t_judge_off, t_modes, t_fail_open, main

<!-- mios-src:8380cffce95c from usr/lib/mios/agent-pipe/test_mios_memguard.py:1-4 -->

