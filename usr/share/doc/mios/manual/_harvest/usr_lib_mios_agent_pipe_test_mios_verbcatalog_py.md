<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for mios_verbcatalog -- the verb/recipe catalog loader + 3-projection SSOT source. Writes a synthetic mios.toml [verbs.*]/[recipes.*], points MIOS_TOML at it, and asserts _load_verb_catalog parses it, the three projections (planner prose _render_verb_catalog, OpenAI/MCP schemas _verb_to_openai_tool / _recipe_to_openai_tool, model_name reverse map _build_model_name_map -> _resolve_verb_key) render the expected shapes, the per-arg synonym projection, and the deterministic _identity_answer. No network/DB.
AI-related: ./mios_verbcatalog.py
AI-functions: -

<!-- mios-src:f8fbeaaa7900 from usr/lib/mios/agent-pipe/test_mios_verbcatalog.py:1-3 -->

