<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Agent/node REGISTRY builders extracted verbatim from server.py (refactor R3/mios_agentreg wave). Parses mios.toml [agents.*] / [nodes.*] sections (layered vendor<-/etc<-~/.config) into the {name: {endpoint,model,role,...,engines}} registry dict the dispatcher routes over: _load_agent_registry (per-agent template merge + _defaults inheritance + health_gate safe-default + per-engine binding fold + WS-FED/G2 per-agent auth indexed into _AGENT_AUTH_BY_HOSTPORT), _load_node_pool (synthesises ONE canonical research-worker node:<name> agent per [nodes.*] compute node), and _build_agent_engines (folds legacy endpoint/cpu twin + explicit engines/nodes tables into one {label:{endpoint,model}} map). server.py still owns the module-load assignment (_AGENT_REGISTRY = _load_agent_registry(); _load_node_pool(_AGENT_REGISTRY)). Pure config consts (_toml_section/BACKEND/BACKEND_MODEL/_AGENT_AUTH_BY_HOSTPORT) imported directly from mios_config; the server-resident helpers (_is_remote_endpoint, _opt_int_mb), the logger, and the CATALOG_FAIL_MODE / NODES_RESEARCH_ONLY flags are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./mios_config.py, ./server.py, ./test_mios_agentreg.py, /usr/share/mios/mios.toml
AI-functions: _build_agent_engines, _load_agent_registry, _load_node_pool, _agent_lane, _render_agent_catalog, _role_system, _dedup_pool_by_target, configure

<!-- mios-src:25c3432b130e from usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py:1-3 -->

