<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Verb/recipe catalog loader + the three-projection SSOT...

Verb/recipe catalog loader + the three-projection SSOT source.

Extracted verbatim from ``server.py``. Parses the ``mios.toml`` ``[verbs.*]`` and
``[recipes.*]`` sections into the canonical catalogs and projects them into the
planner prose block, the OpenAI/MCP function-tool schemas, and the model_name /
hidden_alias reverse map. Every function is moved byte-for-byte; ``server.py``
re-imports each under its original ``_``-prefixed name so the importable surface
is unchanged.

The HOT globals ``_VERB_CATALOG`` and ``_MODEL_NAME_TO_VERB`` are OWNED by
``server.py`` (it runs the assignments by calling the re-imported builders) and
injected here via :func:`configure` AFTER they are built, so the catalog readers
(``_resolve_verb_key``, ``_identity_answer``, ``_load_verb_arg_synonyms``) see the
live catalog. ``CATALOG_FAIL_MODE`` is injected before the first catalog build.
One-way module boundary: this module never imports ``server``.

<!-- mios-src:9220873cfcff from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:3-18 -->

### Deterministic reply to "who are you / what can you do"...

Deterministic reply to "who are you / what can you do", built from the LIVE
 capability catalog + a generic persona intro (the 14B
    confabulated its identity from the literal model name -- "Zabbix agent",
    "Mio's Pizza" -- and varied wildly run to run, because a small model cannot be
    trusted to self-describe). Composed deterministically, like the `remember`
    handler. All specifics come from _VERB_CATALOG (the mios.toml [verbs.*] SSOT),
    so the reply is accurate AND baked: a freshly-imaged Day-0 agent describes
    itself correctly with zero chat history. Returns '' if no catalog is loaded.

<!-- mios-src:5fe3db3b5887 from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:490-497 -->

### P1 PA-Tool reverse map {model_name -> canonical verb key}...

P1 PA-Tool reverse map {model_name -> canonical verb key} for every verb that
    declares a model_name alias. The model emits tool_calls under the alias; dispatch +
    the permission gate + the tier/selection lookups resolve it back to the key. A
    collision (alias == a real verb key, or two verbs claim the same alias) is logged and
    the offending alias dropped -- real keys always win, so a bad alias degrades to the
    key being shown, never to a mis-dispatch.

<!-- mios-src:32329cdffeb2 from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:519-524 -->

### Parse mios.toml [recipes.*] -> {name: {description, args...

Parse mios.toml [recipes.*] -> {name: {description, args, permission}}.
    SSOT for the os_recipe verb. Rendered into the planner prompt so EVERY
    recipe is natively discoverable by every agent -- no recipe names baked
 in code ("ALL agents know to use these functions";
    "no hardcodes unless modelfile/docs"). Add a [recipes.*] block in TOML
    and it appears here + in every consumer automatically (self-iterating).

<!-- mios-src:406ad1e1993b from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:584-589 -->

### Render one [recipes.*] entry as an OpenAI function-tool...

Render one [recipes.*] entry as an OpenAI function-tool schema --
    the SAME `{type:function, function:{name,description,parameters}}` shape
    as _verb_to_openai_tool / _skill_to_openai_tool. The function name is
    mangled to `mios_recipe__<name>` so a relay (mios-mcp-server) can route a
    returned tool_call back through the opaque `os_recipe` verb -- strip the
    prefix, then POST /v1/dispatch {tool:'os_recipe', args:{name, params}}.
    Recipe args are free-form per [recipes.*].args (SSOT in mios.toml); every
    arg is exposed as a string property, plus an optional `os` selector (some
    recipes branch on the target OS). No arg is marked required -- recipes
    fill sensible defaults, and the os_recipe verb tolerates a partial
    params map. Discover here, execute via os_recipe at /v1/dispatch.

<!-- mios-src:400012602b1b from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:624-634 -->

### Render one [verbs.*] entry as an OpenAI function-tool...

Render one [verbs.*] entry as an OpenAI function-tool schema --
    the SAME `{type:function, function:{name,description,parameters}}`
    shape Hermes/OpenCode already consume from /skills/openai-tools (see
    _skill_to_openai_tool). Tool name == the bare verb name, so a returned
    tool_call executes verbatim via POST /v1/dispatch {tool, args} (the
    launcher-broker path the MCP server also uses). No name mangling ->
    discover here, execute there, one contract.

<!-- mios-src:f0a9e9d59ed5 from usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py:684-690 -->
