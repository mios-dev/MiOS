<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Tool-call execution primitive + narrated-tool-call rescue...

Tool-call execution primitive + narrated-tool-call rescue corpus.

Extracted verbatim from ``server.py``. Holds the universal pipe-side tool
executor (``_exec_tool_calls``), the hard-won narrated-tool-call salvage
(``_rescue_tool_calls`` / ``_norm_tool_call`` + the ``_RESCUE_*`` regexes), the
ACI result capping (``_cap_verb_result`` / ``_verb_result_cap``) and the broker
error shaper (``_format_tool_error``). ``server.py`` re-imports every name under
its original alias so the module's public surface is byte-identical.

The moved bodies are unchanged. ``_loads_lenient`` (mios_jsonsalvage),
``_aci_normalize`` (mios_aci) and ``execute_skill`` (mios_skills) are imported
directly from their sibling modules; every other server-side symbol they touch
(the verb/recipe/security catalogs, the orchestrator-context ContextVar, the
config scalars and the DB / dispatch / swarm helpers) is injected via
:func:`configure` (one-way module boundary -- this module never imports
``server``).

<!-- mios-src:a4659ed89ee1 from usr/lib/mios/agent-pipe/mios_pipe/routing/toolexec.py:3-19 -->

### Promote a NARRATED tool call in `content` into OpenAI...

Promote a NARRATED tool call in `content` into OpenAI tool_calls[].
    Parses (a) Qwen <function=NAME><parameter=K>V</parameter></function> XML,
    and (b) JSON objects -- bare or in a ```fence -- of shape
    {"name","arguments"|"args"|"parameters"}, OpenAI {"function":{"name",
    "arguments"}}, or {"tool","args"}. Returns [] when nothing matches a known
    tool. GUARD: only names in _allowed_tool_names are promoted.

<!-- mios-src:380929d682a0 from usr/lib/mios/agent-pipe/mios_pipe/routing/toolexec.py:210-215 -->

### Cap a verb result to its char budget, FLAGGING truncation...

Cap a verb result to its char budget, FLAGGING truncation loudly.

    A bare mid-record slice (the old `out[:cap]`) invites the model to FABRICATE
 the omitted tail -- "what's open" invented window PIDs/
    titles + a whole process list PAST a cut-off list_windows/process_list,
    because the slice looked like a complete (just short) list. This marker +
    the grounding instruction make the model report ONLY the complete entries
    shown and say the list continues, instead of completing it from imagination.
    Returns `out` unchanged when within budget.

<!-- mios-src:e4c4371acd66 from usr/lib/mios/agent-pipe/mios_pipe/routing/toolexec.py:270-278 -->

### Execute the verbs in an OpenAI tool_calls[] list via the...

Execute the verbs in an OpenAI tool_calls[] list via the broker and return
    (tool_result_messages, ran_any). Shared by every pipe-side sub-agent tool-loop
 (every sub-agent lane, all /v1) so the OpenAI loop is ONE mechanism ('full
    loop ... to OpenAI Standards'). tool_call_id is preserved for OpenAI-spec
    linkage; the result is also keyed by `name` (some models match by name).

    allow_write: when False (the PRIMARY's pipe-side pre-resolution) only
    permission=read verbs auto-execute -- the primary's OWN loop performs writes.
    When True (a WORKER/agent loop) write/launch verbs execute too: the MiOS
    agents ACT -- the no-live-launch binding is CLAUDE's alone, not the agents'
. The broker's conversation-scoped single-flight dedup
    collapses duplicate actions across the parallel swarm, so a write fires once.

<!-- mios-src:8e5a3bf79ceb from usr/lib/mios/agent-pipe/mios_pipe/routing/toolexec.py:331-342 -->
