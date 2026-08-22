<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### SKILLS execution cluster -- skill readers, the step engine...

SKILLS execution cluster -- skill readers, the step engine, and the
OpenAI function-tool projectors.

Extracted verbatim from ``server.py``. ``_skill_fetch`` / ``_skill_list``
read promoted-skill rows (pg-native when pgvector is primary);
``execute_skill`` maps a skill body's steps 1:1 onto ``dispatch_mios_verb``
calls (sequence / try-each modes, ``expand_from`` fan-out, invocation
open/close + tool_call attribution); ``_skill_to_openai_tool`` /
``_mcp_tool_to_openai_tool`` / ``_make_schema_strict`` project skills and
external MCP tools into OpenAI strict function-tool schemas consumed
verbatim by Hermes + OpenCode. ``server.py`` re-imports every name under
its original alias so the module's public surface is byte-identical.

The server-side DB-event helpers, the verb dispatcher, the
invocation/attribution helpers, the arg renderer, the ``$``-token regex
and the ``SKILLS_ENABLED`` flag are injected via :func:`configure`
(one-way module boundary -- this module never imports ``server``).

<!-- mios-src:56ca917a715c from usr/lib/mios/agent-pipe/mios_skills.py:3-20 -->

### Inject the server.py runtime helpers the skills engine...

Inject the server.py runtime helpers the skills engine calls back into.

    The invocation/attribution lifecycle, the arg renderer and the $-token regex
    now LIVE in this module (no longer injected); only the DB-event helpers, the
    verb dispatcher, the pg outcome mirror and the SKILLS_ENABLED flag are
    server-owned. _passport_sign is imported directly from mios_a2a_principal.
    The episodic SKILL.md mirror's target dir + enable flag are server-owned SSOT
    (env-read) and injected here; _a2a_now is imported directly from mios_a2a.

<!-- mios-src:015d29414f58 from usr/lib/mios/agent-pipe/mios_skills.py:53-60 -->

### Run a skill by name. Returns the same envelope shape an...

Run a skill by name. Returns the same envelope shape an
    execute_dag run returns -- success, steps[], failures[],
    aborted -- so every gateway in the stack consumes skill output
    with identical code.

    The skill body steps are mapped 1:1 to dispatch_mios_verb calls;
    each tool_call row produced is attributed to the skill via
    RELATE skill_invocation->emitted->tool_call. The Phase B.3
    firewall, Phase A.3 taint chain, and Phase A.1 reflexion cap
    all apply unchanged because we route through the same
    dispatch_mios_verb the planner uses.

<!-- mios-src:05440901c177 from usr/lib/mios/agent-pipe/mios_skills.py:134-144 -->

### Render one skill row as an OpenAI function-tool schema....

Render one skill row as an OpenAI function-tool schema.
    Hermes + OpenCode consume this dump verbatim so their tool
    surface auto-extends every time the operator promotes a skill --
    no code changes per skill on either client.

<!-- mios-src:818ce79aafbf from usr/lib/mios/agent-pipe/mios_skills.py:311-314 -->

### Substitute $-tokens in skill step args using the params...

Substitute $-tokens in skill step args using the params map.
    Pure helper -- the skill body holds the template, the params
    dict holds the concrete operator-supplied values.

    Operator-supplied params override mined defaults. Missing
    params leave the $-token literal (so the dispatch errors
    visibly instead of silently swallowing the gap).

<!-- mios-src:fbaad9c6a4f1 from usr/lib/mios/agent-pipe/mios_skills.py:429-435 -->

### Open a skill_invocation row; returns the new row id (or...

Open a skill_invocation row; returns the new row id (or
    None if the DB write failed). The caller closes the row via
    _skill_invocation_close with ended_at + success.

    Hand-built CREATE -- _db_create json.dumps-quotes every value,
    but the legacy backend requires record<...> references UNQUOTED
    (`skill = skill:abc123`, not `skill = "skill:abc123"`). The
    quoted form produces a coerce error response that the caller
    can't interpret as success.

<!-- mios-src:df1527cc3747 from usr/lib/mios/agent-pipe/mios_skills.py:521-529 -->

### Render a self-contained SKILL.md (operator brief L6...

Render a self-contained SKILL.md (operator brief L6 'closed-loop self-
    learning'): YAML frontmatter (re-usable by OpenViking-style L0/L1/L2 +
    Obsidian) + Goal + Workflow (per-tool-call line) + Outcome. Kept compact
    so the file fits a single tokenizer window when the next similar query
    recalls it as exemplar context.

<!-- mios-src:1a8135098bf2 from usr/lib/mios/agent-pipe/mios_skills.py:619-623 -->
