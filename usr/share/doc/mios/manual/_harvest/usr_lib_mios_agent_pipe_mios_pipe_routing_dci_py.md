<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Deliberative Collective Intelligence (DCI) subsystem extracted verbatim from server.py (refactor R6 wave). 14 typed epistemic acts (Habermas-rooted, arxiv 2603.11781) grouped into 6 families -> _DCI_ACTS/_DCI_ACT_NAMES/_DCI_ACT_SCHEMA; the Phase B.1 single-persona Challenger critic (dci_critic_pass, _DCI_CRITIC_SYSTEM); the Phase B.2 4-persona convergent flow (run_dci_flow + _dci_call_persona over Framer/Explorer/Challenger/Integrator personas built by _persona_prompt with _PERSONA_ALLOWED_ACTS); and the Phase B.3 conditional escalation (critic_then_maybe_flow: cheap critic -> heavy flow -> taint-on-dissent). Config (_STACK_MODEL/_LIGHT_BASE) imported from mios_config; the DB-event helpers (_db_post/_db_create/_db_fire) + outbound-auth stamper (_apply_outbound_auth) are dependency-INJECTED via configure() (one-way boundary -- mios_dci NEVER imports server, enforced by 98-drift-checks check 6). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff). The CRITIC_REFINE_* heavy-path executor-critic-refiner stays in server.py (uses _emit_session_event) and consumes dci_critic_pass re-imported from here.
AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./test_mios_dci.py
AI-functions: _persona_prompt, _dci_call_persona, run_dci_flow, critic_then_maybe_flow, dci_critic_pass, configure

<!-- mios-src:a2958a7f426b from usr/lib/mios/agent-pipe/mios_pipe/routing/dci.py:1-3 -->

