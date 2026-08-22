<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: CaMeL dual-context QUARANTINE boundary -- the deeper half of the F2/T-033 prompt-injection defense (Debenedetti et al., "Defeating Prompt Injections by Design"), composed as a DETERMINISTIC (not probabilistic) dispatch gate that is STRICTER than the Rule-of-Two sibling. The CaMeL principle: untrusted/attacker-controllable content (web/file/tool output that TAINTS the session) must not be able to make the privileged action-planner take a sensitive OR state-changing action it would not otherwise. The MiOS expression: the boundary BITES when the session is TAINTED (axis A -- the EXISTING provenance-taint signal, passed in as session_tainted) AND the verb is PRIVILEGED -- i.e. it READS sensitive/private data (axis B -- the SSOT [verbs.*].sensitive flag) OR mutates state / has side-effects (axis C -- derived from the SSOT [verbs.*].permission tier via the EXISTING mios_ruleof2.is_state_change policy). Where Rule-of-Two gates the all-three case (A AND B AND C), quarantine-enforce additionally gates the tainted+(B OR C) case -- a STRICTER posture for full CaMeL isolation. Pure + stdlib + composes EXISTING signals (the SAME taint bool, the SAME SSOT verb metadata, the SAME tier->side-effect derivation as T-033) -- no re-invented taint/privilege logic, no English-keyword classifier. The SSOT [security].quarantine_mode (off|audit|enforce) enum + its degrade-open normaliser are SHARED VERBATIM with mios_ruleof2 so the two architectural gates can never drift. This module owns ONLY the deterministic decision so it unit-tests in isolation; mios_dispatch / server.py own the wiring (the mode flag, the chokepoint placement, the mios_hitl.decide routing). NEVER imports server.
AI-related: ./mios_ruleof2.py, ./mios_sandbox.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_firewall.py, /usr/share/mios/mios.toml, ./test_mios_quarantine.py
AI-functions: normalize_mode, evaluate, quarantined_extract, class QuarantineVerdict

<!-- mios-src:c7e709781b27 from usr/lib/mios/agent-pipe/mios_pipe/access/quarantine.py:1-3 -->

