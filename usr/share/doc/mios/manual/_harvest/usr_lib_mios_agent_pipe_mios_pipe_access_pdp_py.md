<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A9 Policy Decision Point (PDP) -- the pure capability/risk decision core shared by the agent-pipe's RBAC SURFACE filters (_agent_rbac_filter/_user_rbac_filter) AND the dispatch-time gate in _dispatch_mios_verb_inner, so a verb pruned from a caller's tool surface can NEVER still dispatch (the bypass WS-A9 closes). One decide() applies denied_verbs / allowed_verbs / a max_permission risk ceiling to a verb. Critically it FIXES the fail-OPEN defect: a non-empty-but-UNKNOWN max_permission used to mean "no ceiling" (silently granting everything); resolve_ceiling() now FAILS CLOSED to the safest tier. server.py owns the wiring (contextvars for the dispatching agent + the request user, the audit-event emit, the SSOT [agents.*]/[users.*] policy keys); this module owns only the decision logic.
AI-related: ./server.py, ./mios_sched.py, /usr/share/mios/mios.toml, ./test_mios_pdp.py, ./automation/99-postcheck.sh
AI-functions: permission_rank, resolve_ceiling, decide, class Decision

<!-- mios-src:23461d2f606a from usr/lib/mios/agent-pipe/mios_pipe/access/pdp.py:1-3 -->

