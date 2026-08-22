<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Offline stdlib-assert test for the F2/T-033 Rule-of-Two architectural prompt-injection gate. Two layers: (1) the PURE evaluator mios_ruleof2 -- is_state_change derives property C from the SSOT permission tier via mios_sandbox (read=False, write/interactive=True, unknown=True fail-closed), normalize_mode degrades an unknown token to off, evaluate composes A (passed taint bool) + B (sensitive flag) + C into the all-three verdict, and the per-mode action matrix (all-3 -> gate/audit/proceed; <=2 -> always proceed). (2) the CHOKEPOINT WIRING through mios_dispatch._dispatch_mios_verb_inner with SYNTHETIC non-dictionary verbs -- all-3 (tainted+sensitive+write) is GATED in enforce (rule_of_two_blocked, broker never reached), AUDITED (event, non-blocking) in audit, a NO-OP in off (the evaluator is not consulted -> default-off byte-identical), any 2-of-3 PROCEEDS, an explicit approval downgrades the enforce block, and a taint-read error DEGRADES OPEN (no crash, no new block). No network / no DB / no broker.
AI-related: ./mios_ruleof2.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_sandbox.py, ./mios_firewall.py
AI-functions: (assert script)

<!-- mios-src:0c24b3a66def from usr/lib/mios/agent-pipe/test_mios_ruleof2.py:1-3 -->

