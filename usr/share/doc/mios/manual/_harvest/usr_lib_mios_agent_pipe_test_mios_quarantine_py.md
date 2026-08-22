<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Offline stdlib-assert test for the F2 CaMeL dual-context QUARANTINE gate (the deeper half of T-033, mios_quarantine). Two layers: (1) the PURE evaluator -- evaluate() composes A (passed taint bool) with the SSOT-derived B (sensitive flag) + C (permission tier -> mios_ruleof2.is_state_change) and BITES on tainted AND (sensitive OR state-change) -- the STRICTER superset of Rule-of-Two's all-three; normalize_mode delegates to the shared T-033 enum, the action matrix is bite->gate/audit/proceed by mode and <no-bite>->always proceed, the seam stub quarantined_extract degrades to None. (2) the CHOKEPOINT WIRING through mios_dispatch with SYNTHETIC non-dictionary verbs -- enforce+tainted+sensitive(read) is GATED (quarantine_blocked, broker never reached), enforce+tainted+write GATED, enforce+tainted+read-only-non-sensitive PROCEEDS, enforce+UNtainted+privileged PROCEEDS (quarantine only bites on untrusted-present), audit logs a quarantine_audit event WITHOUT blocking, off mode is BYTE-IDENTICAL (the evaluator is never consulted), an explicit approval downgrades the enforce block, a taint-read error DEGRADES OPEN. SOUNDNESS: the SAME tainted+privileged dispatch is gated via BOTH the public dispatch_mios_verb (chat) entry AND the direct _dispatch_mios_verb_inner chokepoint -- the broker cmd-builder is never reached through either path (no bypass). No network / no DB / no broker.
AI-related: ./mios_quarantine.py, ./mios_ruleof2.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_sandbox.py, ./mios_firewall.py
AI-functions: (assert script)

<!-- mios-src:b45a9c312a5b from usr/lib/mios/agent-pipe/test_mios_quarantine.py:1-3 -->

