<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Planner / DAG-decomposition layer extracted verbatim from server.py. Holds the Phase-A.1 _PLANNER_SYSTEM prompt (renders the SSOT verb/recipe/agent catalogs into the function-calling-shaped DAG planner prompt), the Stage-2 domain-prompt narrowers _planner_system_for / _action_domain_verbs (swap the full verb-catalog block for the routed domain's slice), decompose_intent (calls the planner LLM -> validated DAG of dispatch-verb / sub-agent nodes), and the executor orderers _topological_order (dependency order, cycle-safe) + _dag_levels (Kahn concurrent-level layering). Config (PLANNER_*) re-read from os.environ with _STACK_MODEL/_LIGHT_BASE bases imported from mios_config; _render_verb_catalog imported from mios_verbcatalog; the rendered catalogs + the routed-domain contextvar + the raw verb-catalog/routing-domains SSOT + _is_action_domain/_build_dispatch_cmd helpers + the live _AGENT_REGISTRY are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server; _AGENT_REGISTRY is re-injected on membership reload). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_verbcatalog.py, ./test_mios_planner.py
AI-functions: decompose_intent, _topological_order, _dag_levels, _planner_system_for, _action_domain_verbs, configure

<!-- mios-src:61f3fc91dece from usr/lib/mios/agent-pipe/mios_pipe/routing/planner.py:1-3 -->

