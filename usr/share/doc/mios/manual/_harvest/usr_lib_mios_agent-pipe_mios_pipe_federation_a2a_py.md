<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

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

<!-- mios-src:fae559cdf10a from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:3-22 -->

### The chat's shared-context checkpoints rendered as A2A v1.0...

The chat's shared-context checkpoints rendered as A2A v1.0 Message objects:
    role=ROLE_AGENT, one text Part per checkpoint, grouped by contextId=key. This is
    the SAME blackboard _scratchpad_note writes + _scratchpad_render injects --
    exposed in the open A2A/ACP shape so context is SHARED between agents over the
    standard, not only via the bespoke prose injection ('context should be shared
    inter agents -- A2A/ACP'). v1.0 Message{role,parts[],contextId} (no `kind` tag).

<!-- mios-src:bc71d7a62799 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:542-547 -->

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

<!-- mios-src:9fa99e9f93ac from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:583-596 -->

### FED-G6 verify-tier audit

FED-G6 verify-tier audit: emit ONE structured (JSON) record for a principal
    check that verify-mode lets pass but enforce-mode would reject -- so an operator
    can watch what enforcing WOULD block before flipping the gate. Best-effort: an
    audit failure must never block the request it is only observing.

<!-- mios-src:3136a8fafd09 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:613-616 -->

### WS-A10 principal/cert revocation list, loaded from...

WS-A10 principal/cert revocation list, loaded from MIOS_CRL_PATH (a JSON
    list or {"revoked":[...]}) + cached by mtime. INERT BY DEFAULT: no CRL file
    -> an empty CRL (nothing revoked), so the revocation check is a no-op until an
    operator publishes a CRL. Degrade-open.

<!-- mios-src:e0b55c90dc58 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:647-650 -->

### True if this caller key is on the CRL -- matched by the...

True if this caller key is on the CRL -- matched by the bearer token's
    FINGERPRINT or by the entry's stored id/kid/fingerprint/principal. server.py's
    _check_inbound_principal consults this so POST /v1/admin/keys/revoke takes effect at
    the inbound gate immediately (the CRL is hot-reloaded on revoke). Degrade-open: any
    CRL fault -> not revoked, so a revocation error never locks out a valid caller.

<!-- mios-src:aaa9caa545f7 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:710-714 -->

### FED-G8 logic for POST /v1/admin/keys/revoke (server.py...

FED-G8 logic for POST /v1/admin/keys/revoke (server.py keeps the thin route on
    a2a_router). Appends the named caller key to the CRL + hot-reloads it so the
    credential is refused on the very next check, no restart. ADMIN: credential-gated
    by the inbound-principal resolver -- a control-plane mutation, always-on
    independent of the global api_require_auth flag, matching the peers/reload route.
    Body names the key by token | id | fingerprint | kid | principal.

<!-- mios-src:e90ec7eb4efd from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:752-757 -->

### Receive-side check (thin wrapper over...

Receive-side check (thin wrapper over mios_a2a_principal.verify): binds the
    delivered text + routes to the passport verifier. (verdict, reason, claims);
    verdict None = no principal block (legacy / non-MiOS peer).

    WS-A10: a validly-SIGNED principal is still REJECTED if its principal/agent id
    is on the CRL (mios_crl) -- revocation overrides a good signature. Inert when
    no CRL file exists (empty CRL); degrade-open.

<!-- mios-src:f931f6f8c0df from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:782-788 -->

### Synchronously run a freshly-created Task through the...

Synchronously run a freshly-created Task through the agent-pipe's own
    /v1/chat/completions, marshal the answer back as an Artifact + an
    agent-role Message in history, and advance state to completed/failed.
    Internal localhost POST: zero new code paths -- the task gets the same
    refine/swarm/council/polish treatment as any OWUI chat, and threads on the
    same scratchpad via metadata.chat_id=contextId.

<!-- mios-src:057501f97288 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:930-935 -->

### P2: bridge an A2A SendStreamingMessage onto SSE -- emit a...

P2: bridge an A2A SendStreamingMessage onto SSE -- emit a `working` Task
    frame, run the same dispatch path SendMessage uses, then the final
    `completed`/`failed` Task frame. Honest, non-incremental streaming (no live
    token bus). Each SSE result is a v1.0 StreamResponse payload (a Task wrapped
    under "task"); v1.0 dropped the `final` flag -- the stream simply closes after
    the terminal frame. Fields captured into locals BEFORE the generator (the
    request body is consumed once). MIOS_A2A_STREAM=0 reverts.

<!-- mios-src:694c7ac11cca from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:1202-1208 -->

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

<!-- mios-src:2d1eee7d4df7 from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:1377-1386 -->

### A2A/ACP shared inter-agent context

A2A/ACP shared inter-agent context: the conversation's blackboard
 rendered as A2A Message history grouped by contextId (
    "context should be shared inter agents -- A2A/ACP"). Any A2A/ACP-aware
    agent or client reads the shared context by contextId here, in the open
    standard shape, instead of relying only on the bespoke prose injection.
    LOCAL-ONLY, like the rest of the A2A surface.

<!-- mios-src:7203f8552f2d from usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py:1392-1397 -->
