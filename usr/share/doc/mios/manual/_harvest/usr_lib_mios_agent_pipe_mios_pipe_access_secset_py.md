<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A14 SSOT-derived security sets. Pure-stdlib resolver that derives the agent-pipe's high-privilege verb set (the taint-firewall + HITL gate scope) and the always-taint verb set from the SSOT ([security].firewall_high_privilege_verbs / [security].taint_verbs) UNIONED with the curated in-code base -- so the firewall scope is driven by mios.toml, not a hardcoded literal that silently drifts from the SSOT list. provenance() reports curated-vs-SSOT origin for the introspection endpoint. server.py owns the wiring (read mios.toml, build the module-level sets, feed the firewall/HITL gate); this module owns only the deterministic set math.
AI-related: ./server.py, /usr/share/mios/mios.toml, ./mios_hitl.py, ./mios_pdp.py, ./test_mios_secset.py
AI-functions: high_privilege_set, taint_verb_set, provenance

<!-- mios-src:0b5959d8be47 from usr/lib/mios/agent-pipe/mios_pipe/access/secset.py:1-3 -->

