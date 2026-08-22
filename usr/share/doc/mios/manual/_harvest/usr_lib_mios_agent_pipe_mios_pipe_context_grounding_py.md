<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Per-turn ENV-GROUNDING subsystem extracted verbatim from server.py (refactor R2 leaf wave). Builds the native system-role <env> grounding block the agent-pipe orchestrator threads into EVERY grounded prompt (refine/synthesis/polish/swarm/council/native-loop): the structured _env_block() <env> key:value view + the prose helpers _identity_guard (non-negotiable local-only identity), _arch_grounding (self-architecture), _temporal_grounding (date/time from the client locale), _client_grounding (location/locale/cwd/surface), _capability_grounding (live tool-surface summary), and _client_env (normalise the OWUI-forwarded metadata.variables into a flat env dict). _env_grounding() composes them. Config (_toml_section) imported from mios_config; the per-request _client_env_var ContextVar and the _current_date_str helper that STAY in server.py are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff). NO hardcoded topics/keywords -- capability lines re-derive from the live verb catalog.
AI-related: ./server.py, ./mios_config.py, ./test_mios_grounding.py
AI-functions: _capability_grounding, _temporal_grounding, _get_os_info, _host_timezone, _client_grounding, _identity_guard, _arch_grounding, _env_block, _env_grounding, _principal_bind_mode, _bound_account, _client_env, configure

<!-- mios-src:c9dba7f62079 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:1-3 -->

