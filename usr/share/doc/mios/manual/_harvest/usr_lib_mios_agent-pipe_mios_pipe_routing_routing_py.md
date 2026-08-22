<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### ROUTING layer -- deterministic SSOT-config routing loaders...

ROUTING layer -- deterministic SSOT-config routing loaders + the
catalog-derived deterministic pre-router.

Extracted verbatim from ``server.py``. ``_load_routing_domains`` /
``_load_routing_phrases`` / ``_load_launch_fillers`` read the routing
vocabulary from ``mios.toml`` ``[routing]`` (domains, launch fillers,
trigger phrases) -- all SSOT data, no hardcoded English. ``_deterministic
_action_route`` maps an unambiguous launch / type request to a single
concrete verb override before the refine micro can mis-route it.

The fast-path verb sets and launch phrase frozensets (``_FASTPATH_VERBS``,
``_LAUNCH_TRIGGERS``, ``_LAUNCH_FILLERS``, ``_LAUNCH_LEAD_WORDS``,
``_LAUNCH_TRAIL_WORDS``, ``_COMPOUND_ACTION_ALT``) and the module logger
are injected via :func:`configure` -- they stay in ``server.py`` because
they derive from the ``_VERB_CATALOG`` server global. ``server.py``
re-imports every name under its original alias so the module's public
surface is byte-identical (one-way boundary: this module never imports
``server``).

<!-- mios-src:88be9c73b0d1 from usr/lib/mios/agent-pipe/mios_pipe/routing/routing.py:3-21 -->

### Parse mios.toml [routing.domains.*] -> {domain...

Parse mios.toml [routing.domains.*] -> {domain: {"desc","verbs"}} plus the
    router_enable switch. The 2-stage domain router's Stage-1 classifier consumes
    `desc` as each enum label's meaning; Stage-2 filters the planner catalog to the
 chosen domain's `verbs`. SSOT (fix the 82-tool mis-routing
    via schema-routing, NO english prose rules). FAIL-SAFE: router disabled / no
    domains / load error -> ({}, False) -> full-surface behaviour, nothing lost.

<!-- mios-src:6d6e628f7b27 from usr/lib/mios/agent-pipe/mios_pipe/routing/routing.py:67-72 -->

### Research-backed (OpenAI function-calling + AIOS routing)...

Research-backed (OpenAI function-calling + AIOS routing) deterministic
    pre-router. An unambiguous 'launch/open <app>' is a single concrete action;
    bind it to open_app(name=<app>) HERE so the qwen-class refine micro never
    gets to misclassify it as a research swarm -- the failure where 'launch
    epiphany' fired mios_find/list_windows and FABRICATED 'it's open' instead of
    launching. Returns the override dict, or None to fall through to the LLM
    router for compound/ambiguous phrasing (URLs, 'in <app>', conjunctions,
    questions) which the stronger refine model resolves. Triggers are
    catalog-derived (verb names), not hardcoded words (operator no-hardcode rule).

<!-- mios-src:87675a088155 from usr/lib/mios/agent-pipe/mios_pipe/routing/routing.py:144-152 -->
