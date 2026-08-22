<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: VERB/RECIPE CATALOG loader + 3-projection SSOT source, extracted verbatim from server.py (refactor R2 leaf wave). Parses mios.toml [verbs.*]/[recipes.*] into the canonical catalogs (_load_verb_catalog / _load_recipe_catalog) and projects them three ways -- planner prose (_render_verb_catalog / _render_recipe_catalog), OpenAI/MCP function-tool schemas (_verb_to_openai_tool / _recipe_to_openai_tool), and the model_name/hidden_alias reverse map (_build_model_name_map -> _resolve_verb_key) -- plus the per-arg synonym projection (_verb_arg_synonyms_from_catalog / _load_verb_arg_synonyms) and the deterministic identity reply (_identity_answer). Config (CATALOG_FAIL_MODE) and the HOT server-owned globals _VERB_CATALOG / _MODEL_NAME_TO_VERB are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server); server.py keeps OWNERSHIP of those global assignments (it calls the re-imported builders) so the many existing configure(verb_catalog=_VERB_CATALOG) injections across siblings stay valid. _capability_grounding is imported directly from the mios_grounding sibling. server.py re-imports every name verbatim under its original alias (surface-parity zero-diff). NO hardcoded topics/keywords -- everything re-derives from the live mios.toml SSOT.
AI-related: ./server.py, ./mios_config.py, ./mios_grounding.py, ./test_mios_verbcatalog.py
AI-functions: _load_verb_catalog, _verb_arg_synonyms_from_catalog, _render_verb_catalog, _identity_answer, _load_verb_arg_synonyms, _build_model_name_map, _resolve_verb_key, _load_recipe_catalog, _render_recipe_catalog, _recipe_to_openai_tool, _verb_to_openai_tool, configure

<!-- mios-src:ca87d21ee2c0 from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:1-3 -->

