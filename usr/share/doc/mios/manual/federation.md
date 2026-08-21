<!-- AI-hint: Manual pages distilled from the source comments of federation, sanitized, each passage anchored to the comment it came from. -->

# federation

### A2A federation publish/server surface for the agent-pipe...

A2A federation publish/server surface for the agent-pipe (refactor R11).

Extracted VERBATIM from ``server.py`` -- the agent-card / passport / AGNTCY-OASF
discovery BUILDERS, the A2A JSON-RPC 2.0 task lifecycle (message/send, tasks/*,
pushNotificationConfig/*, message/stream over SSE), the shared inter-agent
context projection, and the signed-delegation principal helpers (send-side
metadata + receive-side verify with the CRL). Every name is moved
byte-identically and re-imported by ``server.py``; the @app A2A routes stay there
as thin wrappers, so the module's public + HTTP surface is unchanged.

``PORT`` / ``MCP_SERVER_PORT`` / ``_toml_section`` import from :mod:`mios_config`;
the interop projectors (:mod:`mios_capreg`, :mod:`mios_interop`, :mod:`mios_crl`,
:mod:`mios_a2a_principal`) import directly. Every server-resident dependency --
the FastAPI ``app`` (for description/version), the agent registry / verb catalog
/ scratchpad blackboard, the agent-lane / skill-tag / capability-skill / user-cfg
helpers, the passport key-load / sign / verify primitives and ``PASSPORT_*``
scalars, the HTTP client factory, the auth-gate flag + the per-request env
contextvar -- is injected via :func:`configure` (one-way boundary: this module
never imports ``server``).

<!-- mios-src:fae559cdf10a from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:4-23 -->

### The chat's shared-context checkpoints rendered as A2A v1.0...

The chat's shared-context checkpoints rendered as A2A v1.0 Message objects:
    role=ROLE_AGENT, one text Part per checkpoint, grouped by contextId=key. This is
    the SAME blackboard _scratchpad_note writes + _scratchpad_render injects --
    exposed in the open A2A/ACP shape so context is SHARED between agents over the
    standard, not only via the bespoke prose injection ('context should be shared
    inter agents -- A2A/ACP'). v1.0 Message{role,parts[],contextId} (no `kind` tag).

<!-- mios-src:bc71d7a62799 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:543-548 -->

### FED-G6

FED-G6: the A2A signed-delegation principal posture, read from SSOT
    ([agent_passport].principal_mode; env MIOS_A2A_PRINCIPAL_MODE wins). Tri-state:

      off     -- degrade-open default: verify-and-attribute only; a bad/absent
                 principal is logged at most, never blocks (today's behaviour).
      verify  -- run the SAME check enforce does, but on a failed/absent principal
                 emit a STRUCTURED audit record and ALLOW the request through. A
                 non-blocking observability tier: watch what enforce WOULD reject
                 before flipping the gate.
      enforce -- reject an unsigned / forged / absent principal.

    Legacy truthy synonyms (require/1/true/yes) map to enforce so an existing
    deployment keeps its posture; any unrecognised value -> off (degrade-open).
    The tokens are an enum read from SSOT, not a content/keyword decision gate.

<!-- mios-src:9fa99e9f93ac from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:584-597 -->

### FED-G6 verify-tier audit

FED-G6 verify-tier audit: emit ONE structured (JSON) record for a principal
    check that verify-mode lets pass but enforce-mode would reject -- so an operator
    can watch what enforcing WOULD block before flipping the gate. Best-effort: an
    audit failure must never block the request it is only observing.

<!-- mios-src:3136a8fafd09 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:614-617 -->

### WS-A10 principal/cert revocation list, loaded from...

WS-A10 principal/cert revocation list, loaded from MIOS_CRL_PATH (a JSON
    list or {"revoked":[...]}) + cached by mtime. INERT BY DEFAULT: no CRL file
    -> an empty CRL (nothing revoked), so the revocation check is a no-op until an
    operator publishes a CRL. Degrade-open.

<!-- mios-src:e0b55c90dc58 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:648-651 -->

### True if this caller key is on the CRL -- matched by the...

True if this caller key is on the CRL -- matched by the bearer token's
    FINGERPRINT or by the entry's stored id/kid/fingerprint/principal. server.py's
    _check_inbound_principal consults this so POST /v1/admin/keys/revoke takes effect at
    the inbound gate immediately (the CRL is hot-reloaded on revoke). Degrade-open: any
    CRL fault -> not revoked, so a revocation error never locks out a valid caller.

<!-- mios-src:aaa9caa545f7 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:711-715 -->

### FED-G8 logic for POST /v1/admin/keys/revoke (server.py...

FED-G8 logic for POST /v1/admin/keys/revoke (server.py keeps the thin route on
    a2a_router). Appends the named caller key to the CRL + hot-reloads it so the
    credential is refused on the very next check, no restart. ADMIN: credential-gated
    by the inbound-principal resolver -- a control-plane mutation, always-on
    independent of the global api_require_auth flag, matching the peers/reload route.
    Body names the key by token | id | fingerprint | kid | principal.

<!-- mios-src:e90ec7eb4efd from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:753-758 -->

### Receive-side check (thin wrapper over...

Receive-side check (thin wrapper over mios_a2a_principal.verify): binds the
    delivered text + routes to the passport verifier. (verdict, reason, claims);
    verdict None = no principal block (legacy / non-MiOS peer).

    WS-A10: a validly-SIGNED principal is still REJECTED if its principal/agent id
    is on the CRL (mios_crl) -- revocation overrides a good signature. Inert when
    no CRL file exists (empty CRL); degrade-open.

<!-- mios-src:f931f6f8c0df from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:783-789 -->

### Synchronously run a freshly-created Task through the...

Synchronously run a freshly-created Task through the agent-pipe's own
    /v1/chat/completions, marshal the answer back as an Artifact + an
    agent-role Message in history, and advance state to completed/failed.
    Internal localhost POST: zero new code paths -- the task gets the same
    refine/swarm/council/polish treatment as any OWUI chat, and threads on the
    same scratchpad via metadata.chat_id=contextId.

<!-- mios-src:057501f97288 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:931-936 -->

### P2: bridge an A2A SendStreamingMessage onto SSE -- emit a...

P2: bridge an A2A SendStreamingMessage onto SSE -- emit a `working` Task
    frame, run the same dispatch path SendMessage uses, then the final
    `completed`/`failed` Task frame. Honest, non-incremental streaming (no live
    token bus). Each SSE result is a v1.0 StreamResponse payload (a Task wrapped
    under "task"); v1.0 dropped the `final` flag -- the stream simply closes after
    the terminal frame. Fields captured into locals BEFORE the generator (the
    request body is consumed once). MIOS_A2A_STREAM=0 reverts.

<!-- mios-src:694c7ac11cca from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:1203-1209 -->

### WS-11 passport-gated A2A capability DIRECTORY: EVERY MiOS...

WS-11 passport-gated A2A capability DIRECTORY: EVERY MiOS capability
    (verb/recipe/skill) projected into the A2A AgentCard skill shape via
    mios_interop -- the THIRD interop projection alongside the MCP tool + OpenAI
    function surfaces this server already emits, so an A2A peer can discover the
    full surface in the open standard, not only via MCP/OpenAI. RBAC-filtered by
    the caller's permission ceiling (the SAME mios_capreg lattice as
    /v1/capabilities -> a matched [users.*].max_permission), so a peer is shown
    only what it may invoke -- the 'passport-gated directory'. The AgentCard
    itself stays lean (the agent PEERS); this is the capability crawl. Read-only,
    degrade-open.

<!-- mios-src:2d1eee7d4df7 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:1378-1387 -->

### A2A/ACP shared inter-agent context

A2A/ACP shared inter-agent context: the conversation's blackboard
 rendered as A2A Message history grouped by contextId (
    "context should be shared inter agents -- A2A/ACP"). Any A2A/ACP-aware
    agent or client reads the shared context by contextId here, in the open
    standard shape, instead of relying only on the bespoke prose injection.
    LOCAL-ONLY, like the rest of the A2A surface.

<!-- mios-src:7203f8552f2d from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:1393-1398 -->

### A2A peer-client consumer half for the agent-pipe (refactor...

A2A peer-client consumer half for the agent-pipe (refactor R11 follow-up).

Extracted VERBATIM from ``server.py`` -- the consumer half of the A2A
federation: the layered peer-registry read, the per-peer agent-card probe +
skill indexing, the optional tailnet auto-discovery, the startup fan-out, the
JSON-RPC ``message/send`` delegation to a chosen peer (with peer-reputation
recording), and the A2A Task-envelope text extractor. Every name is moved
byte-identically and re-imported by ``server.py``; the @app /v1/a2a/dispatch
route and the peer-discovery startup on_event stay there as thin wrappers, so
the module's public + HTTP surface is unchanged.

``_a2a_principal_metadata`` imports from :mod:`mios_a2a`,
``_mcp_render_headers`` from :mod:`mios_mcp` and ``loads_lenient`` from
:mod:`mios_jsonsalvage` directly. The self-peer-loop guard / agent-card fetch /
tailnet candidate discovery helpers live HERE (``_a2a_self_peer_url`` /
``_a2a_fetch_card`` / ``_a2a_tailnet_candidates``). Every remaining
server-resident dependency -- the live ``_A2A_PEERS`` / ``_A2A_PEER_SKILLS``
registries + lock, the outbound ``_A2A_REPUTATION``, the ``_AGENT_REGISTRY``,
the peer-registry paths + ``A2A_COUNCIL`` / ``A2A_SELF_ID`` scalars, the HTTP
client factory, and the worker-tool-surface cache invalidator -- is injected via
:func:`configure` (one-way boundary: this module never imports ``server``).

<!-- mios-src:a5096accbfb4 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:4-25 -->

### True if a peer URL is THIS orchestrator (loopback :8640)....

True if a peer URL is THIS orchestrator (loopback :8640). Delegating or
    fanning out to it re-enters the pipe and recurses UNBOUNDED -- the per-request
    recursion bound is process-local and does NOT cross the a2a HTTP hop (operator
 dGPU runaway: ~35 native-loop turns/sec pegged the GPU). The
    A2A_SELF_ID guard missed it because mios-a2a-discover registers the self as
    "mios-local" while A2A_SELF_ID defaults to "local-mios" -- an id mismatch. So
    exclude by URL (id-agnostic). Only LOOPBACK :8640 is self; a remote node on
    :8640 (real host/tailnet IP) is a legitimate peer and is NOT excluded.

<!-- mios-src:f235ade235ad from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:98-105 -->

### Candidate base-URLs to probe for an A2A agent-card: every...

Candidate base-URLs to probe for an A2A agent-card: every ONLINE tailnet
    peer at the agent-pipe port (`tailscale status --json`) + any explicit
    MIOS_A2A_DISCOVER_URLS. Best-effort -- if the tailscale CLI is unreachable
    from the agent uid, only the explicit list is used. SSOT: the mios.toml
    [a2a] block feeds MIOS_A2A_DISCOVER_PORT / MIOS_A2A_DISCOVER_URLS via the
    userenv slot (no hardcoded node IPs in code).

<!-- mios-src:54b4f984c03e from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:224-229 -->

### Layered peer registry read

Layered peer registry read: vendor < /etc < user. Later overlays
    REPLACE earlier entries with the same id (matches MCP client semantics)
    so an operator can disable a vendor peer by re-declaring it disabled.
    The LOCAL self-peer (loopback :8640) is EXCLUDED -- it is a self-loop vector
    (see _a2a_self_peer_url); delegation to oneself is a no-op on a single node.

<!-- mios-src:ecedcd420174 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:261-265 -->

### Probe tailnet/explicit candidate URLs for an A2A...

Probe tailnet/explicit candidate URLs for an A2A agent-card; return peer
    cfgs for responders (skip URLs already in the registry, skip non-cards). So
    a NEW MiOS agent-pipe node auto-joins the mesh with zero registry editing
. OFF unless MIOS_A2A_TAILNET_DISCOVER is truthy; never
    raises; fast-fails on the compute-only nodes (e.g. oscontrol) that 404 the
    card.

<!-- mios-src:0371e1296483 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py:367-372 -->

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

<!-- mios-src:13effd9ca4db from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:4-20 -->

### The COMPLETE read-only MiOS capability surface as MCP...

The COMPLETE read-only MiOS capability surface as MCP Resources: every
    verb (the script surface), every recipe, and EVERY skill (promoted AND
    not). Browsable discovery that complements the curated callable /v1/tools
    feed -- so the agent can reach the whole catalog without the flat tool list
    growing past the ~30-50 where selection accuracy drops. Degrade-open: a
    failing section drops only itself. Calls list_resources_logic (same module).

<!-- mios-src:03b051f3ff57 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:611-616 -->

### Fetch ONE mios:// resource (skill body / recipe def / verb...

Fetch ONE mios:// resource (skill body / recipe def / verb doc) in MCP
    resources/read shape: {contents:[{uri,mimeType,text}]}. Unknown scheme ->
    404. Degrade-open on backend error. Calls read_resource_logic (same module).

<!-- mios-src:519d4edac9de from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:622-624 -->

### WS-2 unified, RBAC-filtered capability manifest: the single...

WS-2 unified, RBAC-filtered capability manifest: the single list of
    capabilities (verbs + recipes) the CALLER may use, filtered by their
    permission ceiling (matched [users.*].max_permission via the same lattice the
    PDP uses; default 'interactive' = the full known-tier surface when no
    principal/ceiling is forwarded). One projection over the [verbs.*]+[recipes.*]
    SSOT (mios_capreg) -- the live counterpart of the committed
    ai/v1/capabilities.generated.json. Degrade-open.

<!-- mios-src:cae0156b4870 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:630-636 -->

### WS-2 structured capability DAG

WS-2 structured capability DAG: nodes (verbs|recipes|skills) + edges (each
    skill -> the verb/skill its steps invoke), with detected skill->skill `cycles`
    and `dangling` step targets (a step naming an unknown verb/skill). The
    structural counterpart of the flat /v1/capabilities manifest -- lets a caller
    (or an A2A peer) see WHICH primitives a skill composes + validate the graph is
    acyclic + fully-grounded. Read-only, degrade-open, NOT RBAC-filtered (it is the
    full authored graph; /v1/capabilities is the per-caller filtered view).

<!-- mios-src:bd259560fafd from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:642-648 -->

### WS-A11/WS-3 Router introspection

WS-A11/WS-3 Router introspection: classify a refined plan WITHOUT executing
    it. POST a bare refined dict or {"refined": {...}} -> the typed RouteDecision
    {mode, intent, tool, fanout, reason}. Lets an operator confirm the decomposed
    Router matches the inline chat_completions cascade before the Stage-2b
    execution swap. Pure + read-only.

<!-- mios-src:22d504f82cd1 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:654-658 -->

### WS-RES-GOV cost/energy accounting (CLASSic Cost axis): the...

WS-RES-GOV cost/energy accounting (CLASSic Cost axis): the running ledger
    of dispatch energy (Wh) + $ + tokens, broken down per lane, since process
    start. Observe-only; populated when [cost].enable is on. The power envelope is
    the real constraint on a local-GPU OS, so this surfaces it as a first-class
    signal (complements the token-rate budget tripwire).

<!-- mios-src:40c5444b116b from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:664-668 -->

### WS-LIFECYCLE-VER versioned hop-prompt registry: each live...

WS-LIFECYCLE-VER versioned hop-prompt registry: each live system prompt's
    version + content-hash + length + history depth (content-FREE -- never leaks
    the prompt text). The substrate for self-improve rollback + prompt-drift
    detection. Empty until the startup registration runs. Calls
    prompt_registry_view_logic (same module).

<!-- mios-src:e8f409970da0 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:697-701 -->

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

<!-- mios-src:8cfecd74de47 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:724-742 -->

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

<!-- mios-src:176d90aab8c9 from usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py:748-768 -->

### External-MCP consume client for the agent-pipe federated...

External-MCP consume client for the agent-pipe federated tool surface (refactor R-MCP).

Extracted VERBATIM from ``server.py``. MiOS CONSUMES external MCP servers (not
just publishes its own): a layered registry read, an initialize handshake over
Streamable-HTTP or a spawned stdio subprocess, ``tools/list`` registration of
every remote tool namespaced ``mcp.<server>.<tool>``, and ``tools/call``
forwarding. The ``GET /v1/mcp/clients`` / ``GET /v1/mcp/tools`` /
``POST /v1/mcp/dispatch`` routes stay in ``server.py`` as thin wrappers calling
the ``*_logic`` functions here.

The shared MCP-tool registry + lock (``_MCP_CLIENT_TOOLS`` / ``_MCP_CLIENT_LOCK``)
remain server-resident (the worker / toolsearch / toolexec planes share them) and
are injected via :func:`configure`, together with the HTTP client factory, the
per-tool embedder (``_mcp_embed_new_tools``, from ``mios_toolsearch``), and the
worker-tool-surface cache invalidator. This module never imports ``server``
(one-way boundary); ``server.py`` re-imports every moved name under its original
alias so the importable surface is byte-identical.

The declared revision is the ``[mcp].protocol_version`` SSOT
(:data:`MCP_PROTOCOL_VERSION`, env ``MIOS_MCP_PROTOCOL_VERSION``). The newer MCP
feature set (durable Tasks, elicitation, OAuth resource-server auth, tool icons,
structured tool output) and the upcoming stateless-transport revision are scoped
follow-ups; this client implements the core initialize / tools-list / tools-call
consume path over Streamable-HTTP (current) + stdio.

<!-- mios-src:d7b2cccfa70c from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:4-28 -->

### Layered registry read

Layered registry read: vendor < /etc < user. Later overlays REPLACE
    earlier entries with the same id (not merge) so an operator can disable a
    vendor entry by re-declaring it with enabled:false.

<!-- mios-src:b81ca5cb9ce8 from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:107-109 -->

### Long-lived MCP server subprocess speaking newline-delimited...

Long-lived MCP server subprocess speaking newline-delimited JSON-RPC 2.0
 over stdin/stdout (MCP stdio transport). Mirrors _mcp_http_rpc's
    error-envelope shape so callers need NO special-casing. Self-heals: a dead
    process is respawned AND re-initialized on the next call (restart-on-crash).
    Non-blocking (asyncio subprocess + StreamReader.readline). stderr -> DEVNULL
    (spec: the server MAY log to stderr; the client MAY ignore it).

<!-- mios-src:e7659031ee24 from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:174-179 -->

### P4: surface a stdio MCP server's stderr (first chunk) in...

P4: surface a stdio MCP server's stderr (first chunk) in the journal instead of
        silently discarding it -- otherwise a spawn/crash is an opaque 'stdio init failed'.

<!-- mios-src:f2dca439aad7 from usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py:224-225 -->
