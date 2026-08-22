<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: CaMeL-class architectural prompt-injection defense -- Meta's "Agents Rule of Two" composed as a DETERMINISTIC (not probabilistic) dispatch gate. A turn/verb may hold AT MOST TWO of three properties without human review: (A) untrusted-input -- the session ingested attacker-controllable content (the EXISTING provenance-taint signal, passed in as session_tainted); (B) sensitive-access -- the verb READS sensitive/private/cross-tenant data (the SSOT [verbs.*].sensitive flag, additive); (C) state-change -- the verb mutates state / has external side-effects (the SSOT [verbs.*].permission tier, mapped via the EXISTING mios_sandbox tier->confinement policy: read=pure-info, write/interactive=side-effecting). When ALL THREE hold the chain is the classic prompt-injection kill-chain (untrusted text -> reads secrets -> exfiltrates/acts) and must be gated. Pure + stdlib + composes EXISTING signals (no re-invented taint/privilege logic, no English-keyword classifier): A is the caller's taint bool, B is SSOT metadata, C is derived from the SSOT permission tier through mios_sandbox (FAIL-CLOSED: unknown tier -> side-effecting). server.py / mios_dispatch own the wiring + the mode flag; this module owns only the deterministic decision so it unit-tests in isolation. NEVER imports server.
AI-related: ./mios_sandbox.py, ./mios_hitl.py, ./mios_dispatch.py, ./mios_firewall.py, /usr/share/mios/mios.toml, ./test_mios_ruleof2.py
AI-functions: normalize_mode, is_state_change, evaluate, class RuleOfTwoVerdict

<!-- mios-src:fe4d149f1c21 from usr/lib/mios/agent-pipe/mios_pipe/routing/ruleof2.py:1-3 -->

