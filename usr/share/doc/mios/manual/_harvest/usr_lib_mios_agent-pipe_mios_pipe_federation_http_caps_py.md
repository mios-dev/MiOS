<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Advertised-surface / capability + read-only admin...

Advertised-surface / capability + read-only admin route-handler logic (refactor R-CAPS).

Extracted VERBATIM from ``server.py``: the bodies behind the discovery and
introspection endpoints (verb/tool/resource projections, the RBAC-filtered
capability manifest + DAG, the gossip peer digest, the kernel Router shadow, the
cost ledger, the trace ring-buffer reads, the offline posture, the skill catalog,
the KG lookup, the DCI surface, and the ``/v1/models`` + ``/v1/embeddings``
proxies). Each handler body is moved byte-identically into a ``*_logic`` function;
the ``@app`` routes stay in ``server.py`` as thin wrappers calling these via
``sys.modules`` so the HTTP + importable surface is unchanged.

``mios_capreg`` and the DCI act vocabulary are imported directly; every
server-resident dependency is injected via :func:`configure` (one-way boundary --
this module never imports ``server``). The three MCP Resource projectors
(``_skill_to_mcp_resource`` / ``_recipe_to_mcp_resource`` / ``_verb_to_mcp_resource``)
are moved here in full and re-imported by ``server.py`` under their original names.

<!-- mios-src:13effd9ca4db from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:3-19 -->

### The COMPLETE read-only MiOS capability surface as MCP...

The COMPLETE read-only MiOS capability surface as MCP Resources: every
    verb (the script surface), every recipe, and EVERY skill (promoted AND
    not). Browsable discovery that complements the curated callable /v1/tools
    feed -- so the agent can reach the whole catalog without the flat tool list
    growing past the ~30-50 where selection accuracy drops. Degrade-open: a
    failing section drops only itself. Calls list_resources_logic (same module).

<!-- mios-src:03b051f3ff57 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:610-615 -->

### Fetch ONE mios:// resource (skill body / recipe def / verb...

Fetch ONE mios:// resource (skill body / recipe def / verb doc) in MCP
    resources/read shape: {contents:[{uri,mimeType,text}]}. Unknown scheme ->
    404. Degrade-open on backend error. Calls read_resource_logic (same module).

<!-- mios-src:519d4edac9de from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:621-623 -->

### WS-2 unified, RBAC-filtered capability manifest: the single...

WS-2 unified, RBAC-filtered capability manifest: the single list of
    capabilities (verbs + recipes) the CALLER may use, filtered by their
    permission ceiling (matched [users.*].max_permission via the same lattice the
    PDP uses; default 'interactive' = the full known-tier surface when no
    principal/ceiling is forwarded). One projection over the [verbs.*]+[recipes.*]
    SSOT (mios_capreg) -- the live counterpart of the committed
    ai/v1/capabilities.generated.json. Degrade-open.

<!-- mios-src:cae0156b4870 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:629-635 -->

### WS-2 structured capability DAG

WS-2 structured capability DAG: nodes (verbs|recipes|skills) + edges (each
    skill -> the verb/skill its steps invoke), with detected skill->skill `cycles`
    and `dangling` step targets (a step naming an unknown verb/skill). The
    structural counterpart of the flat /v1/capabilities manifest -- lets a caller
    (or an A2A peer) see WHICH primitives a skill composes + validate the graph is
    acyclic + fully-grounded. Read-only, degrade-open, NOT RBAC-filtered (it is the
    full authored graph; /v1/capabilities is the per-caller filtered view).

<!-- mios-src:bd259560fafd from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:641-647 -->

### WS-A11/WS-3 Router introspection

WS-A11/WS-3 Router introspection: classify a refined plan WITHOUT executing
    it. POST a bare refined dict or {"refined": {...}} -> the typed RouteDecision
    {mode, intent, tool, fanout, reason}. Lets an operator confirm the decomposed
    Router matches the inline chat_completions cascade before the Stage-2b
    execution swap. Pure + read-only.

<!-- mios-src:22d504f82cd1 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:653-657 -->

### WS-RES-GOV cost/energy accounting (CLASSic Cost axis): the...

WS-RES-GOV cost/energy accounting (CLASSic Cost axis): the running ledger
    of dispatch energy (Wh) + $ + tokens, broken down per lane, since process
    start. Observe-only; populated when [cost].enable is on. The power envelope is
    the real constraint on a local-GPU OS, so this surfaces it as a first-class
    signal (complements the token-rate budget tripwire).

<!-- mios-src:40c5444b116b from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:663-667 -->

### WS-LIFECYCLE-VER versioned hop-prompt registry: each live...

WS-LIFECYCLE-VER versioned hop-prompt registry: each live system prompt's
    version + content-hash + length + history depth (content-FREE -- never leaks
    the prompt text). The substrate for self-improve rollback + prompt-drift
    detection. Empty until the startup registration runs. Calls
    prompt_registry_view_logic (same module).

<!-- mios-src:e8f409970da0 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:696-700 -->

### The MiOS verb catalog projected into the OpenAI `tools=`...

The MiOS verb catalog projected into the OpenAI `tools=` array shape.

 include_rare defaults TRUE ("ALL global agents and
    sub-agents able to use ALL the tools"). Broker dispatch access was already
    global; this makes the PRESENTED surface complete too -- no verb (incl
    crawl, and other former tier=rare entries) is hidden behind tool_search.
    Pass include_rare=false for the trimmed set if a context-budget-limited
    client needs it.

    The OpenAI-shape twin of /v1/verbs (which serves the MCP `inputSchema`
    shape for mios-mcp-server). Hermes already carries the full MiOS verb +
    skill surface alongside its own built-in tools, so this is NOT how
    Hermes gets its tools. It exists so any STRICT OpenAI tool-loop client
    that lacks the MiOS plugin -- an external /v1 caller, OpenCode in a
    tools= mode, an A2A/ACP peer -- can be handed the verb surface in the
    standard shape and call it via POST /v1/dispatch {tool,args} (same
    launcher-broker path the MCP server uses). One SSOT (_VERB_CATALOG),
    three projections: MCP (/v1/verbs), OpenAI tools (here), A2A skills
    (the agent card). Discover here, execute at /v1/dispatch.

<!-- mios-src:8cfecd74de47 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:723-741 -->

### The COMPLETE MiOS capability surface as MCP tool specs...

The COMPLETE MiOS capability surface as MCP tool specs: every verb
    PLUS every OS recipe PLUS every promoted skill, in one feed.

    This is the unified discovery endpoint mios-mcp-server's `tools/list`
    consumes so an MCP client sees the WHOLE surface, not just the verb
    catalog. /v1/verbs is left UNCHANGED (verbs only) for existing
    consumers; this is the superset.

    Three projections, one MCP `inputSchema`/function shape:
      (a) verbs   -> _verb_to_openai_tool   (name == bare verb)
      (b) recipes -> _recipe_to_openai_tool (name == mios_recipe__<name>)
      (c) skills  -> _skill_to_openai_tool  (name == mios_skill__<name>)

    The relay routes a returned tool_call by name prefix: a bare name ->
    POST /v1/dispatch {tool,args}; mios_recipe__* -> os_recipe; mios_skill__*
    -> POST /skills/run. Discover here, execute there -- one contract.

    Degrade-open: a recipe-load or skill-DB failure drops only THAT section,
    never the others, so an offline datastore still yields the full verb +
    recipe surface (operator: tools must stay available even when a subsystem
    is down).

<!-- mios-src:176d90aab8c9 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:747-767 -->
