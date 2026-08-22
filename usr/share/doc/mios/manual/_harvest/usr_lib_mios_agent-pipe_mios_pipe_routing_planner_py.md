<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Planner / DAG-decomposition layer (Phase A.1). Extracted...

Planner / DAG-decomposition layer (Phase A.1).

Extracted verbatim from ``server.py``. ``_PLANNER_SYSTEM`` is the
function-calling-shaped planner system prompt -- it embeds the SSOT verb /
recipe / agent catalogs (rendered server-side and injected via
:func:`configure`) so the planner only emits real verbs / agents.
``decompose_intent`` calls the planner LLM and returns a validated DAG of
dispatch-verb / sub-agent nodes (or ``None`` to fall through to the backend).
``_topological_order`` / ``_dag_levels`` order that DAG for the executor.

``_planner_system_for`` / ``_action_domain_verbs`` narrow that prompt to a
single routed domain's verb slice (Stage-2 of the domain router); they live
here beside their only caller (``decompose_intent``).

Config constants (``PLANNER_*``) are re-read from ``os.environ`` (bases
``_STACK_MODEL`` / ``_LIGHT_BASE`` from ``mios_config``); ``_render_verb_catalog``
is imported from ``mios_verbcatalog``; the rendered catalogs, the routed-domain
contextvar, the raw verb-catalog / routing-domains SSOT, the
``_is_action_domain`` / ``_build_dispatch_cmd`` helpers and the live
``_AGENT_REGISTRY`` are injected via :func:`configure` (one-way boundary --
this module never imports ``server``).

<!-- mios-src:6b9bc902f148 from usr/lib/mios/agent-pipe/mios_pipe/routing/planner.py:3-24 -->

### Inject the server.py runtime deps the planner calls back...

Inject the server.py runtime deps the planner calls back into, then
    (re)build _PLANNER_SYSTEM once the rendered catalogs are available. The
    verb_catalog / routing_domains args feed the now-native _planner_system_for /
    _action_domain_verbs helpers (raw SSOT they read at call time). The
    short_prompt_chars / short_prompt_words args carry the SSOT [planner]
    short-prompt-skip cutoffs (None = keep the baseline).

<!-- mios-src:2a1ffbee28a0 from usr/lib/mios/agent-pipe/mios_pipe/routing/planner.py:81-86 -->

### Call the planner LLM to emit a DAG of dispatch verbs for a...

Call the planner LLM to emit a DAG of dispatch verbs for a
    multi-step user intent. Returns the parsed dict, or None on
    error / unparseable response.

    Short-prompt skip: short inputs (heuristic: under the SSOT
    [planner] char/word cutoffs) almost always map to a SINGLE
    dispatch verb, not a multi-step plan. Return None so the chain
    falls through to the backend single-dispatch path -- mios-launch
    resolves the verb directly. The planner used to over-decompose
    these into 2-step DAGs whose ReWOO substitution then misfired
    on NDJSON-emitting tools.

<!-- mios-src:fe317328c969 from usr/lib/mios/agent-pipe/mios_pipe/routing/planner.py:362-372 -->

### Group nodes into concurrent execution LEVELS (Kahn...

Group nodes into concurrent execution LEVELS (Kahn layering): each
    level is the set of not-yet-run nodes whose deps are ALL already
    satisfied, so every node in a level can run CONCURRENTLY. A level only
    starts after all earlier levels finish, preserving topological order
    (so ReWOO #E<id> refs resolve). Cyclic / dangling deps degrade to one
    forced node per round (declaration order) so the DAG never hangs --
    same safety stance as _topological_order.

<!-- mios-src:96292ba56b64 from usr/lib/mios/agent-pipe/mios_pipe/routing/planner.py:473-479 -->
