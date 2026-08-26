<!-- AI-hint: Manual pages distilled from the source comments of agent-pipe, sanitized, each passage anchored to the comment it came from. -->

# agent-pipe

### Tool-Manager parameter validation (ref AIOS kernel C 3.7...

Tool-Manager parameter validation (ref AIOS kernel C 3.7: "validate
    parameters before execution to prevent tool crashes"). Reject a verb
    arg whose value falls outside the enum DECLARED for it in mios.toml
    [verbs.<tool>.params.<arg>.enum], BEFORE the command reaches the
    broker -- previously such values passed through as a stray env var and
    silently misbehaved.

<!-- mios-src:eb46518aa256 from usr/lib/mios/agent-pipe/mios_argval.py:40-45 -->

### mios_codemode -- pure helpers for WS-2 Code Mode (the AIOS...

mios_codemode -- pure helpers for WS-2 Code Mode (the AIOS Tool-Manager
"Code Mode" layer: instead of loading ~71 OpenAI function schemas into the
model's context every turn, the agent WRITES CODE that calls a small local tool
API; the code runs inside the EXISTING rootless podman coderun-sandbox and only
the FILTERED result returns -- the big token win).

Pure stdlib (no httpx / fastapi / podman / DB), in the sibling-module style of
mios_sched / mios_evict / mios_aci / mios_hitl, so it unit-tests in isolation
(test_mios_codemode.py). server.py owns the wiring (the SSOT flag, the
_exec_tool_calls branch, the broker proxy); the CLI (usr/libexec/mios/
mios-coderun-codemode) owns the actual podman exec. This module owns only the
reusable, side-effect-free decisions both of them need to agree on:

  * session id derivation (stable per conversation so a chat reuses one warm
    sandbox instead of churning a container per call),
  * the `podman exec` argv that dispatches a snippet into a running sandbox,
  * normalising the agent's tool-call arguments into a snippet request,
  * parsing / capping the sandbox's JSON result envelope,
  * the gating decision (Code Mode is DEFAULT-OFF + degrade-open).

Nothing here launches, writes, or touches the network -- that keeps the security-
sensitive surface (which the agent can drive) small and fully testable.

<!-- mios-src:394b3c922176 from usr/lib/mios/agent-pipe/mios_codemode.py:4-26 -->

### Validate + normalise an agent Code Mode tool-call into a...

Validate + normalise an agent Code Mode tool-call into a request dict.

    Returns (ok, payload). On success payload = {code, lang, timeout, net}. On
    failure payload = {"error": "<reason>"} so the caller returns a structured
    tool result the model can react to (no exceptions across the tool boundary).
    DEFAULT net=False (offline jail) -- the sandbox denies the network unless the
    agent opts in AND the deploy allows it.

<!-- mios-src:186c293eec36 from usr/lib/mios/agent-pipe/mios_codemode.py:95-101 -->

### Code Mode gating (DEFAULT-OFF): only on when...

Code Mode gating (DEFAULT-OFF): only on when [code_mode].enable is an
    explicit truthy value. Any missing/empty/garbage config -> off (degrade
    closed for a code-EXECUTION feature -- the one place we don't degrade open).

<!-- mios-src:80302a148fc9 from usr/lib/mios/agent-pipe/mios_codemode.py:125-127 -->

### The argv that dispatches a prepared snippet file into a...

The argv that dispatches a prepared snippet file into a RUNNING sandbox
    container via `podman exec -i`. The snippet is written to the bind-mounted
    workspace first (the caller does that I/O); here we only build the command
    that runs the right interpreter on it inside the jail.

    `init` (optional) is the in-container Landlock PID-1 wrapper
    (/usr/local/bin/exec-init per concepts/coderun-sandbox.md) -- when given, the
    interpreter is run THROUGH it for the per-process kernel boundary. Pure: this
    only assembles the list; it never runs anything.

<!-- mios-src:35e58aef566d from usr/lib/mios/agent-pipe/mios_codemode.py:143-151 -->

### Verb->bash dispatch chokepoint -- the...

Verb->bash dispatch chokepoint -- the taint->firewall->HITL->broker launcher.

Extracted verbatim from ``server.py`` (refactor R7). Holds the SSOT command-
template renderer (``_template_to_cmd``), the per-verb dispatch-command builder
(``_build_dispatch_cmd`` -- the launch_app / window_op / os_recipe / pkg / pc_* /
text_* / powershell_run guard registry) and the launcher proper
(``dispatch_mios_verb`` / ``_dispatch_bounded`` / ``_dispatch_mios_verb_inner``).
``server.py`` re-imports every name under its original alias so the module's
public surface is byte-identical.

The moved bodies are UNCHANGED. ``_classify_verb_taint`` / ``_session_is_tainted``
(mios_firewall), ``_hitl_block_reason`` / ``_HITL_ARBITER_URL`` /
``_hitl_arbiter_verdict`` / ``_match_user_cfg`` / ``_dispatch_quota_reason`` /
``_dispatch_pdp_reason`` (mios_policy), ``_action_hash`` / ``_pending_hash`` /
``_hitl_record_pending`` / ``_hitl_gate`` (mios_hitlflow) and ``_loads_lenient``
(mios_jsonsalvage) are imported directly from their sibling modules; ``mios_sandbox``
is imported as a module. Every other server-side symbol they touch (the verb
catalog, the broker socket path, the DB-event helpers, the dispatch ContextVars,
the sandbox-profile resolver and the dedup state) is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).

SECURITY-CRITICAL: every gate here is NAME-KEYED (verb keys, the permission tier
in mios_policy, the ``_HIGH_PRIVILEGE_VERBS`` / ``_LAUNCH_VERBS`` set membership).
Nothing is renamed.

<!-- mios-src:a4ea47df6ca6 from usr/lib/mios/agent-pipe/mios_dispatch.py:4-28 -->

### Persist a /v1/dispatch verb execution as a session-linked...

Persist a /v1/dispatch verb execution as a session-linked ``tool_call`` row
    -- the SAME shape the chat dispatch fast-path and the DAG executor write -- so a
    verb run through the dispatch HTTP front (mios-mcp-server's ``tools/call`` lands
    here) is VISIBLE to same-session provenance-taint propagation.

    ``_session_is_tainted`` decides the Semantic Firewall block by reading prior
    ``tool_call`` rows with ``tainted = true``; the chat + DAG paths each record their
    executions, but the dispatch path did not -- so a tainting verb dispatched here
    left no row, the taint was never seen, and a downstream high-privilege verb in the
    SAME session went un-gated. The taint markers come straight off the verb result
    (``_classify_verb_taint`` set them inside the dispatch chokepoint): no new schema,
    no new taint logic, just the missing persistence.

    Best-effort / degrade-open: the verb has ALREADY executed by the time this runs,
    so an absent DB writer or a write failure is swallowed (the audit row is not
    load-bearing for the verb's own result).

<!-- mios-src:547636815095 from usr/lib/mios/agent-pipe/mios_dispatch.py:128-143 -->

### Return (cmd, workspace_or_None). When SANDBOX_ENFORCE is on...

Return (cmd, workspace_or_None). When SANDBOX_ENFORCE is on AND `tool` OPTS
    IN to confinement (an explicit [verbs.*].sandbox_profile) AND the resolved
    profile is confined AND the cmd does not already self-confine, prefix it with
    mios-sandbox-exec (--level enforce, +--net iff the tier allows egress) bound to
    a fresh per-dispatch workspace. Otherwise the cmd is returned unchanged. The
    OPT-IN gate (explicit override, not tier alone) is what keeps OS-control/launch
    verbs -- which bwrap would break -- from ever being wrapped here.

<!-- mios-src:e1a811185cb1 from usr/lib/mios/agent-pipe/mios_dispatch.py:274-280 -->

### Bulkhead layer. web_search dispatches share a global...

Bulkhead layer. web_search dispatches share a global concurrency
    semaphore so a council/DAG fan-out -- each call itself expanding into
    MIOS_WEB_FANOUT concurrent sub-queries -- can't stampede the local
    SearXNG; excess calls QUEUE here, with a small pre-acquire jitter to
    stagger simultaneous starts. All other verbs pass straight through.

    WS-A7: additionally, every dispatch is wrapped in the Tool-Manager conflict
    gate, which serializes verbs that declare a parallel_limit (per-verb
    concurrency cap) or a conflict_group (named mutual-exclusion set, e.g. the
    single-foreground-window UI verbs). The gate is a no-op for verbs that
    declare neither (the overwhelming majority), so this adds ~zero overhead to
    the common path while making stateful verbs fan-out-safe.

<!-- mios-src:96b0f8602785 from usr/lib/mios/agent-pipe/mios_dispatch.py:515-526 -->

### Public dispatch entry point, wrapping the bulkhead with a...

Public dispatch entry point, wrapping the bulkhead with a conversation-
    scoped concurrent SINGLE-FLIGHT guard (anti-swarm-duplication; see
    _dispatch_inflight). Concurrent identical (verb, resolved-args) dispatches
    in the same conversation collapse to ONE broker execution + share the
    result, so a side effect never fires N times across a fan-out. In-flight
    only -> sequential repeats re-run fresh.

<!-- mios-src:44e1dd194cfd from usr/lib/mios/agent-pipe/mios_dispatch.py:600-605 -->

### Audit a Rule-of-Two all-three decision -- one structured...

Audit a Rule-of-Two all-three decision -- one structured observability shape for
    both the audit-mode log line and the enforce-mode block. Carries the property
    breakdown (which of A/B/C, the count, the mode) so the decision is reconstructable.
    Best-effort / degrade-open: an absent DB writer or a write failure is swallowed.

<!-- mios-src:5c222419f898 from usr/lib/mios/agent-pipe/mios_dispatch.py:739-742 -->

### The Rule-of-Two architectural gate (F2/T-033, CaMeL-class)...

The Rule-of-Two architectural gate (F2/T-033, CaMeL-class), composed at the
    dispatch chokepoint. Returns a block_result dict to REFUSE the dispatch (enforce
    mode, a confirmed all-three kill-chain not yet human-approved) or None to PROCEED.

    Composes EXISTING signals -- it re-derives nothing: A (untrusted-input) is the
    provenance-taint chain (``_session_is_tainted``); B (sensitive-access) + C
    (state-change) are derived from the SSOT verb metadata INSIDE the pure
    ``mios_ruleof2.evaluate`` (the [verbs.*].sensitive flag + the permission tier).
    Placed AFTER the existing taint/HITL gates -- each of those returns early on its
    own block -- so Rule-of-Two only ADDS a refusal (the stricter gate wins).

      off     -> not consulted (the call-site guards on the mode -> byte-identical).
      audit   -> structured non-blocking audit line, then proceed (observe before enforce).
      enforce -> route the all-three posture through the SINGLE ``mios_hitl.decide``
                 resolver; an explicit same-turn ask-to-run approval downgrades the
                 block so the human who approved THIS exact action can run it.

    Degrade-open: ANY error -> None (fall back to the existing firewall/HITL behaviour;
    never crash, never newly block-everything). A CONFIRMED all-three under enforce
    gates (fail toward safety).

<!-- mios-src:cf3199a1a661 from usr/lib/mios/agent-pipe/mios_dispatch.py:762-781 -->

### Audit a CaMeL quarantine decision (the boundary BIT...

Audit a CaMeL quarantine decision (the boundary BIT: tainted AND privileged) --
    one structured observability shape for both the audit-mode log line and the
    enforce-mode block. Carries the axis breakdown (A + whether B / C, the mode) so the
    decision is reconstructable. Best-effort / degrade-open: an absent DB writer or a
    write failure is swallowed.

<!-- mios-src:e4670aec2bef from usr/lib/mios/agent-pipe/mios_dispatch.py:825-829 -->

### The CaMeL dual-context QUARANTINE gate (F2, the deeper half...

The CaMeL dual-context QUARANTINE gate (F2, the deeper half of T-033), composed
    at the dispatch chokepoint AFTER the Rule-of-Two gate so it only ADDS a refusal
    (stricter-wins). Returns a block_result dict to REFUSE the dispatch (enforce mode, a
    confirmed tainted+privileged action not yet human-approved) or None to PROCEED.

    Composes EXISTING signals -- it re-derives nothing: A (untrusted-input) is the
    provenance-taint chain (``_session_is_tainted``); B (sensitive-access) + C
    (state-change) come from the SSOT verb metadata INSIDE the pure
    ``mios_quarantine.evaluate`` (the [verbs.*].sensitive flag + the permission tier).
    The boundary BITES on tainted AND (sensitive OR state-change) -- the STRICTER
    superset of Rule-of-Two's all-three, for when you want full CaMeL isolation.

      off     -> not consulted (the call-site guards on the mode -> byte-identical).
      audit   -> structured non-blocking audit line, then proceed (observe before enforce).
      enforce -> route the bite posture through the SINGLE ``mios_hitl.decide`` resolver
                 (quarantine_block=True); an explicit same-turn ask-to-run approval
                 downgrades the block so the human who approved THIS exact action runs it.

    SOUNDNESS: this sits at the SAME single chokepoint as the firewall / HITL /
    Rule-of-Two gates and only ADDS a refusal -- there is no second action path that
    bypasses it, and stricter-wins composition means enabling it can only make the
    posture stricter, never weaker.

    Degrade-open: ANY error -> None (fall back to the existing firewall/HITL/Rule-of-Two
    behaviour; never crash, never newly block-everything). A CONFIRMED bite under enforce
    gates (fail toward safety).

<!-- mios-src:c06984198e32 from usr/lib/mios/agent-pipe/mios_dispatch.py:850-875 -->

### Run a single MiOS verb via the launcher broker (unix socket...

Run a single MiOS verb via the launcher broker (unix socket
    /run/mios-launcher/launcher.sock). Returns a structured dict:
    {success, tool, args, output, stderr, exit_code, latency_ms,
     tainted, taint_reason}. Uses the broker's CAPTURE_JSON: protocol
    so stdout/stderr split cleanly.

    Phase A.3: Semantic Firewall stub -- when a high-privilege verb
    is dispatched and the session has ANY upstream tainted tool_call,
    the dispatch is REFUSED (not even sent to the broker) and an
    event row is emitted (kind=firewall_block, severity=high).
    Taint of the dispatched verb itself is computed from
    _classify_verb_taint AND inherited from session state.

<!-- mios-src:376a282b6752 from usr/lib/mios/agent-pipe/mios_dispatch.py:962-973 -->

### Endpoint capability detection (pure leaf extracted from...

Endpoint capability detection (pure leaf extracted from server.py).

MiOS is OpenAI-/v1-only -- every lane exposes ``/v1/chat/completions``, so there
is no wire-dialect to detect. This module probes what FEATURE-SET a given /v1
endpoint supports: a llama.cpp ``llama-server`` that can do ``/slots`` KV paging,
whether it accepts ``tool_choice='required'``, and whether its model reliably
emits well-formed PARALLEL tool calls. Every probe is CONFIG-FIRST (a
per-binding/agent ``api`` field wins) and falls back to an env-SSOT host:port
hint tuple, so no bare port literal lives in the routing code. All functions are
pure (endpoint string + cfg dict + optional engine); the only dependency is
``mios_config._DISPATCH_TOML`` for the hint defaults. ``server.py`` re-imports
every name under its original ``_``-prefixed alias so the module's importable
surface is byte-identical (surface-parity gate).

<!-- mios-src:6cefc369b17a from usr/lib/mios/agent-pipe/mios_endpoints.py:4-17 -->

### mios_registry -- versioned package + local registry...

mios_registry -- versioned package + local registry projection (WS-A17, the
AIOS agent/tool packaging layer).

Pure stdlib. A "package" is a versioned, self-describing wrapper around ONE
capability the live SSOT already defines -- a verb/tool, an agent, or a recipe.
The registry INDEX is a flat catalogue of those packages keyed by
author/name/version. Both are deterministic projections of the live catalogs
(the same ones WS-A1 projects), so the whole thing is a materialized SSOT
mirror, gated behind [ai].package_registry (ships inert -> nothing emitted, the
drift gate is a trivial pass).

Path layout (when materialized):
    ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml   (per-package manifest)
    ai/v1/packages/registry.json                              (the index)

<!-- mios-src:8b04ab691e00 from usr/lib/mios/agent-pipe/mios_registry.py:4-18 -->

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

<!-- mios-src:56ca917a715c from usr/lib/mios/agent-pipe/mios_skills.py:4-21 -->

### Inject the server.py runtime helpers the skills engine...

Inject the server.py runtime helpers the skills engine calls back into.

    The invocation/attribution lifecycle, the arg renderer and the $-token regex
    now LIVE in this module (no longer injected); only the DB-event helpers, the
    verb dispatcher, the pg outcome mirror and the SKILLS_ENABLED flag are
    server-owned. _passport_sign is imported directly from mios_a2a_principal.
    The episodic SKILL.md mirror's target dir + enable flag are server-owned SSOT
    (env-read) and injected here; _a2a_now is imported directly from mios_a2a.

<!-- mios-src:015d29414f58 from usr/lib/mios/agent-pipe/mios_skills.py:54-61 -->

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

<!-- mios-src:05440901c177 from usr/lib/mios/agent-pipe/mios_skills.py:135-145 -->

### Render one skill row as an OpenAI function-tool schema....

Render one skill row as an OpenAI function-tool schema.
    Hermes + OpenCode consume this dump verbatim so their tool
    surface auto-extends every time the operator promotes a skill --
    no code changes per skill on either client.

<!-- mios-src:818ce79aafbf from usr/lib/mios/agent-pipe/mios_skills.py:312-315 -->

### Substitute $-tokens in skill step args using the params...

Substitute $-tokens in skill step args using the params map.
    Pure helper -- the skill body holds the template, the params
    dict holds the concrete operator-supplied values.

    Operator-supplied params override mined defaults. Missing
    params leave the $-token literal (so the dispatch errors
    visibly instead of silently swallowing the gap).

<!-- mios-src:fbaad9c6a4f1 from usr/lib/mios/agent-pipe/mios_skills.py:430-436 -->

### Open a skill_invocation row; returns the new row id (or...

Open a skill_invocation row; returns the new row id (or
    None if the DB write failed). The caller closes the row via
    _skill_invocation_close with ended_at + success.

    Hand-built CREATE -- _db_create json.dumps-quotes every value,
    but the legacy backend requires record<...> references UNQUOTED
    (`skill = skill:abc123`, not `skill = "skill:abc123"`). The
    quoted form produces a coerce error response that the caller
    can't interpret as success.

<!-- mios-src:df1527cc3747 from usr/lib/mios/agent-pipe/mios_skills.py:457-465 -->

### Render a self-contained SKILL.md (operator brief L6...

Render a self-contained SKILL.md (operator brief L6 'closed-loop self-
    learning'): YAML frontmatter (re-usable by OpenViking-style L0/L1/L2 +
    Obsidian) + Goal + Workflow (per-tool-call line) + Outcome. Kept compact
    so the file fits a single tokenizer window when the next similar query
    recalls it as exemplar context.

<!-- mios-src:1a8135098bf2 from usr/lib/mios/agent-pipe/mios_skills.py:546-550 -->

### Static public-surface projection + diff for the agent-pipe...

Static public-surface projection + diff for the agent-pipe server monolith.

The refactor (R0..R12) MOVES blocks of ``server.py`` into sibling modules
behavior-identically, re-importing the moved names so the module's importable
surface is unchanged, and finally collapses ``server.py`` to a re-export shim.
The silent regressions that move can cause are:

  1. an ``@app`` route is dropped / its path or handler renamed, and
  2. a name that external code relies on (a sibling ``mios_*.py``, a ``test_*.py``,
     or a libexec tool that does ``from server import X`` / accesses ``server.X``)
     vanishes from the module entirely.

Both are invisible to a syntax check and to the per-module unit tests. This
projector captures the surface as a committed golden
(``usr/share/mios/ai/v1/surface.generated.json``); the ``check_surface_parity``
gate in ``98-drift-checks.sh`` regenerates it from the live ``server.py`` and
fails on any diff.

KEY INVARIANT -- ``provided`` counts a re-imported name the SAME as a defined one
(it is the set of all module-level *bound* names), so a legitimate
"move definition into a sibling + ``from sibling import name``" extraction is
**zero-diff**, while deleting the name with no re-export is a REMOVED violation.
Pure stdlib + ``ast`` only (no execution of server code) -- the offline half of
"make the refactor regression-proof".

``project_surface`` projects ONE file. ``project_package`` projects a whole
package (the entry module plus the sibling router modules it mounts), resolving
``app.include_router`` mounts that cross file boundaries so the gate stays honest
once routes migrate off ``@app`` onto APIRouter instances in sibling modules. It
is a strict superset of ``project_surface``: on a single-file layout (the current
``server.py``) the two produce the IDENTICAL projection.

<!-- mios-src:24613613b335 from usr/lib/mios/agent-pipe/mios_surface.py:4-35 -->

### Map ``<targets> = APIRouter(...)`` to ``(prefix, [bound...

Map ``<targets> = APIRouter(...)`` to ``(prefix, [bound names])``.

    The router constructor is recognised by its terminal callee name, so both a
    bare ``APIRouter(...)`` and an attribute ``<pkg>.APIRouter(...)`` form match --
    the same structural-API basis on which the ``app`` route object is recognised.
    ``prefix`` is the literal ``prefix=`` kwarg, the empty string when the kwarg is
    omitted (the constructor's own default), or ``_DYNAMIC`` when the kwarg is
    present but not a string literal. ``None`` for any other assignment.

<!-- mios-src:90ecd78ea9ee from usr/lib/mios/agent-pipe/mios_surface.py:93-101 -->

### Map an ``app.include_router(<router>, prefix=...)``...

Map an ``app.include_router(<router>, prefix=...)`` statement to
    ``(router name, mount prefix)``; ``None`` otherwise.

    Mounting a router prepends this prefix to every one of the router's paths.
    ``prefix`` is the literal kwarg, the empty string when omitted, or ``_DYNAMIC``
    when non-literal. Only ``app``-mounted routers are composed here (the in-file
    scope documented on ``project_surface``); a router mounted onto another router
    is not transitively chained.

<!-- mios-src:c3cb972858c7 from usr/lib/mios/agent-pipe/mios_surface.py:121-129 -->

### Map a ``@<obj>.<method>("/path", ...)`` decorator on a...

Map a ``@<obj>.<method>("/path", ...)`` decorator on a NON-``app`` object to
    ``(obj name, METHOD, path)``; ``None`` otherwise.

    Structurally identical to ``_route_from_decorator`` but for an object other
    than ``app`` -- a candidate router variable. The caller keeps only candidates
    whose object was bound to an ``APIRouter`` instance; ``app`` is excluded here
    because ``_route_from_decorator`` already projects it, so it is never counted
    twice.

<!-- mios-src:604f93c8d3d3 from usr/lib/mios/agent-pipe/mios_surface.py:147-155 -->

### Concatenate route path segments (mount prefix + router...

Concatenate route path segments (mount prefix + router prefix + decorator
    path) exactly as FastAPI mounts a router -- plain left-to-right concatenation.

    If ANY segment is the ``_DYNAMIC`` sentinel the whole path is ``_DYNAMIC``,
    mirroring how a single non-literal path is recorded: a path that is not fully
    statically known is reported as dynamic rather than half-resolved.

<!-- mios-src:3b14c68eb246 from usr/lib/mios/agent-pipe/mios_surface.py:172-178 -->

### Module-level bound names introduced by an import statement....

Module-level bound names introduced by an import statement.

    ``import a.b as c`` -> ``c``; ``import a.b`` -> ``a`` (the top package binds);
    ``from m import x, y as z`` -> ``x``, ``z``. ``from m import *`` binds an
    unknowable set -> recorded as the sentinel ``"*"`` so its presence is tracked.

<!-- mios-src:56eb903cd2d2 from usr/lib/mios/agent-pipe/mios_surface.py:185-190 -->

### Project the public surface of the Python module at...

Project the public surface of the Python module at ``path``.

    Deterministic (all lists sorted) so a byte-stable golden can be committed and
    diffed. Returns:

      * ``routes``   -- sorted ``"METHOD path -> handler"`` for every ``@app`` route
                        AND every route declared on an ``APIRouter`` instance. A
                        router route's path is composed as ``<mount prefix><router
                        prefix><decorator path>`` -- FastAPI's mount order -- so a
                        route MOVED from ``@app.get("/a/b")`` onto a prefixed router
                        yields the IDENTICAL record and the migration is zero-diff.
      * ``provided`` -- sorted union of EVERY module-level bound name: top-level
                        ``def``/``async def``, ``class``, assigned global (incl.
                        tuple/annotated targets), and imported name. This is the
                        runtime importable surface; a move+reimport keeps a name in
                        it, a true deletion removes it.
      * ``counts``   -- size summary for quick human scanning

    CROSS-FILE NOTE: router-route composition HERE is resolved from the AST of the
    SINGLE file scanned. When a router and its ``app.include_router(...)`` mount live
    in the same file the full path is recovered. When the package layout splits them
    across files (the ``mios_pipe/`` shape) this single-file scan sees the router's
    own prefix but NOT a mount prefix applied in another file -- it does the best
    in-file resolution (router prefix + decorator path) rather than fabricate the
    missing segment. ``project_package`` lifts this limitation: it parses the
    mounting (entry) file together with the imported router modules and composes the
    cross-file mount prefix. This single-file projector is deliberately unchanged so
    the in-file gate stays byte-stable.

<!-- mios-src:6ce650d4a6a3 from usr/lib/mios/agent-pipe/mios_surface.py:202-230 -->

### Per-file structural facts ``project_package`` composes...

Per-file structural facts ``project_package`` composes across files.

    Collected from a single module's top level (the same scope ``project_surface``
    scans): the APIRouter assignments and their prefixes, the routes decorated on
    those routers, every ``include_router`` mount (split into ``app``-targeted and
    router-nested), and the import bindings that resolve an included router name to
    its defining sibling module.

<!-- mios-src:a03486d151d9 from usr/lib/mios/agent-pipe/mios_surface.py:298-305 -->

### Classify an ``include_router`` first argument into a...

Classify an ``include_router`` first argument into a resolvable reference.

    ``("name", id)`` for a bare ``r``; ``("attr", obj, attr)`` for ``mod.r``;
    ``("other",)`` for any other (dynamic) shape -- which resolves to nothing rather
    than to a fabricated target.

<!-- mios-src:fc5cebd4bdcd from usr/lib/mios/agent-pipe/mios_surface.py:315-320 -->

### Map a ``<obj>.include_router(<arg>, prefix=...)`` statement...

Map a ``<obj>.include_router(<arg>, prefix=...)`` statement to
    ``(obj name, include ref, mount prefix)``; ``None`` otherwise.

    Generalises ``_include_router_call`` (which recognises only the ``app`` object,
    keeping ``project_surface``'s in-file scope) to ANY mounting object, so a router
    nested onto another router (``parent.include_router(child, ...)``) is captured
    for whole-package composition. ``prefix`` defaults to the empty string when
    omitted and is ``_DYNAMIC`` when present but non-literal.

<!-- mios-src:9b5bcf213530 from usr/lib/mios/agent-pipe/mios_surface.py:329-337 -->

### The module-binding maps an import introduces...

The module-binding maps an import introduces: ``(from_imports, plain_imports)``.

    ``from <mod> import <name> [as <b>]`` -> ``from_imports[b] = (<mod>, <name>)``;
    ``import <mod> [as <b>]`` -> ``plain_imports[b] = <mod>`` (a bare ``import a.b``
    binds the top package ``a``). A ``*`` import binds an unknowable set and is
    skipped (no router can be resolved through it).

<!-- mios-src:3f541a65d758 from usr/lib/mios/agent-pipe/mios_surface.py:353-359 -->

### Resolve a dotted module to a sibling ``<final...

Resolve a dotted module to a sibling ``<final component>.py`` in ``search_dir``.

    The static, no-import resolution the refactor's flat ``mios_*.py`` layout uses:
    the module's terminal name IS the filename. ``None`` when no such file exists (an
    external / unresolved module -- never guessed).

<!-- mios-src:5b2b9b3b29e9 from usr/lib/mios/agent-pipe/mios_surface.py:421-426 -->

### Resolve an include reference to ``(defining file, router...

Resolve an include reference to ``(defining file, router var)`` or ``(None, None)``.

    A bare name is a router defined in THIS file or one imported from a sibling
    (``from <mod> import <r>``); an attribute ``<mod>.<r>`` resolves ``<mod>`` through
    the import bindings to a sibling file. Anything that does not resolve to a local
    sibling file yields ``(None, None)`` -- unresolved, never fabricated.

<!-- mios-src:abbc1a97563e from usr/lib/mios/agent-pipe/mios_surface.py:474-480 -->

### Project the public surface of a multi-file package rooted...

Project the public surface of a multi-file package rooted at ``entry_path``.

    Identical to ``project_surface`` for the entry module's in-file surface (``@app``
    routes, any in-file routers, and the entry's ``provided`` names), then ADDS the
    routes contributed by sibling router modules the entry mounts via
    ``app.include_router(<imported router>, prefix=...)`` -- composing the mount
    prefix (entry file) with the router prefix + ``@router`` decorator paths (sibling
    file) into the SAME record. ``provided`` stays the ENTRY module's bound-name
    surface (see the section comment for why it is not aggregated).

    On a layout with no cross-file includes (e.g. the current single-file
    ``server.py``) this returns EXACTLY what ``project_surface`` does. ``search_dir``
    overrides where sibling ``<module>.py`` files are looked up (default: the entry
    file's own directory).

<!-- mios-src:30d811ac91af from usr/lib/mios/agent-pipe/mios_surface.py:535-549 -->

### Human-readable diffs between a fresh projection and the...

Human-readable diffs between a fresh projection and the committed golden.

    REMOVED (in golden, gone now) is the dangerous case -- a route/symbol the
    surface promised disappeared. ADDED (new now, not in golden) is reported too:
    a deliberate surface growth should regenerate the golden, an accidental one is
    worth seeing. Compares ``routes`` and ``provided``.

<!-- mios-src:e6243060d128 from usr/lib/mios/agent-pipe/mios_surface.py:576-582 -->

### CLI

CLI: ``mios_surface <server.py>`` prints the projection JSON;
    ``mios_surface <server.py> --check <golden.json>`` diffs and exits non-zero on drift.

    ``--package`` switches to whole-package projection (``project_package``),
    optionally with ``--search-dir <dir>`` for the sibling module lookup. Without
    it, the single-file ``project_surface`` path is used -- so the drift-gate's
    ``<server.py> --check <golden.json>`` invocation behaves exactly as before.

<!-- mios-src:60fe525377c2 from usr/lib/mios/agent-pipe/mios_surface.py:595-602 -->

### 'MiOS' Agent Pipe -- standalone FastAPI service. Step 2 of...

'MiOS' Agent Pipe -- standalone FastAPI service.

Step 2 of the migration: ports the router + dispatch + agent-plane DB
writes from the OWUI Pipe class into this gateway-agnostic service.

Operator directive "mios discord chats not going through
MiOS-Agent(OWUI) paths when contacting through discord (uses only
MiOS-Hermes and doesn't have the same tool understanding and
environments details now!!!!)"

Architecture:

  OWUI                     ──┐
  Hermes Discord gateway   ──┼──> :8640 (this service)
  future Slack/Telegram    ──┘        │
                                       ▼
                              :8642 (hermes-agent)
                                       │
                                       ▼
                       mios-llm-light :8450 (raw /v1 inference)

Endpoints:
  GET  /health                  -> {status, version, backend, port}
  POST /v1/chat/completions     -> Router-classified chain:
                                     action=dispatch -> verb via broker
                                                       -> tool_call envelope
                                     action=chat    -> short-reply
                                     action=agent   -> proxy to backend
                                     (no verdict)   -> proxy to backend
  GET  /v1/models               -> proxy to MIOS_AGENT_PIPE_BACKEND
  POST /v1/embeddings           -> proxy to MIOS_AGENT_PIPE_BACKEND

Per the SSOT chain: every operator-tunable constant sources from
mios.toml -> userenv.sh -> MIOS_* env -> os.environ.get() with
sensible fallbacks. No hardcoded literals.

Skipped vs. the OWUI Pipe (deliberate for this commit; can be Step
2b if Discord needs them):
  * REFINE pass (CPU-LLM rewrite of the user message before forward)
  * CRITIC pass (post-backend verification + re-compose loop)
  * POLISH pass (final-answer cleanup)
  * NARRATION COLLAPSE (OWUI <think> wrapping)
These are quality-bonus features that add latency without changing
the tool-understanding parity Discord needs. They can be ported in
follow-up commits guided by operator feedback.

<!-- mios-src:8e220b2bb79a from usr/lib/mios/agent-pipe/server.py:4-49 -->

### Open a span under the current trace/parent (contextvars)...

Open a span under the current trace/parent (contextvars), record it on
    exit with duration + ok/error status. Near-no-op when tracing is disabled or
    no trace is active (degrade-open).

<!-- mios-src:b3c10a99920b from usr/lib/mios/agent-pipe/server.py:343-345 -->

### Liveness-probe + circuit-break an agent/node when it...

Liveness-probe + circuit-break an agent/node when it declares health_gate
 OR lives on a REMOTE endpoint (dead-node circuit-breaker:
    ai-local the phone had no explicit health_gate -> was dispatched while off ->
    'All connection attempts failed' retry storm that helped wedge the box). LOCAL
    lanes are never probed -- their failure is a separate, louder problem and
    probing only adds latency.

<!-- mios-src:855a2a330f4a from usr/lib/mios/agent-pipe/server.py:429-434 -->

### At chat_completions entry

At chat_completions entry: seed the dispatch depth FROM the incoming X-MiOS-Hop
    (so the bound crosses the HTTP hop) and record the Via chain. If our OWN id is
    already in the chain, force degrade-closed (no further fan-out) -> a re-entrant
    loop answers single-agent instead of recursing. Degrade-open on any error.

<!-- mios-src:fc796ad8d3ed from usr/lib/mios/agent-pipe/server.py:619-622 -->

### Force the micro model on a LOCAL light-lane (CPU/iGPU)...

Force the micro model on a LOCAL light-lane (CPU/iGPU) endpoint -- a big
    model can never cold-load multi-GB weights on a CPU-only daemon MiOS itself
 controls (runaway fix). No-op for non-light endpoints AND for
    REMOTE nodes: a remote node serves its OWN model catalog (a tailnet node
    whose port happens to be 11435/11436 need not serve the LOCAL micro tag), so
    it KEEPS its declared model -- exactly this function's long-standing intent
    ('remote keep their model'), which the bare port-substring match wrongly
    violated for any remote node on a CPU-hint port (the remote-cpu node, the
    iGPU/potato examples). LOCAL == localhost/127.0.0.1 (mirrors _load_node_pool's
    _is_local). The slow-lane num_predict cap (_is_slow_lane_ep) stays port-based
    and DOES still apply to a remote CPU -- a remote CPU is genuinely slow, so its
    output is still capped; only the wrong-model substitution is local-scoped.

<!-- mios-src:74a6abf4465c from usr/lib/mios/agent-pipe/server.py:1264-1275 -->

### [dispatch] -- multi-agent concurrent fan-out config (SSOT...

[dispatch] -- multi-agent concurrent fan-out config (SSOT in
    mios.toml; env override).

 mode (supersedes the earlier 'a couple, not all'):
      * 'council'   -- EQUAL WEIGHTING: every chat-eligible agent (every
                       [agents.*] without fanout=false, minus the primary)
                       is dispatched CONCURRENTLY each turn, up to
                       fanout_max, regardless of tag relevance. Lane-diverse
                       ordering runs CPU + GPU agents in parallel. This is
                       what stops the Hermes monopoly.
      * 'relevance' -- legacy: score the OTHER agents by skill-tag overlap
                       with the refined plan, engage only the top matches.
    fanout_max<=1 restores exact single-agent behaviour (zero fan-out).

<!-- mios-src:ff8dc1247235 from usr/lib/mios/agent-pipe/server.py:1466-1478 -->

### Canonical skill tags for an agent

Canonical skill tags for an agent: role + inference lane + declared
    strengths. SINGLE SSOT shared by the A2A AgentCard (publish side ->
    skill.tags) and _pick_fanout_agents (consume side -> routing key) so an
    agent's advertised capabilities and the key the orchestrator routes on
    can never drift. Clean human/agent-facing labels (NOT snake_case-split);
    the router expands sub-tokens for matching internally.

<!-- mios-src:3db845183ebd from usr/lib/mios/agent-pipe/server.py:1530-1535 -->

### The verified owner/tenant for THIS turn's dispatch, or...

The verified owner/tenant for THIS turn's dispatch, or None. Reuses the V2
    principal-binding owner: under [security].principal_bind_mode=enforce the
    _client_env owner is already RECONCILED to the token-bound account (the spoofable
    claim overridden), so this returns the verified tenant; otherwise the forwarded
    owner. None (a system/daemon/seeding dispatch with no forwarded principal) -> the
    per-tenant gate never caps it. Consulted ONLY when TENANT_QUOTA_ENABLE; degrade-
    open: any error -> None (no per-tenant cap). Mirrors mios_knowledge._request_
    principal so the tenant key agrees with owner_user row-scoping.

<!-- mios-src:dd28ae032739 from usr/lib/mios/agent-pipe/server.py:1965-1972 -->

### Pipeline-side READ-ONLY capability runner ("all... skills...

Pipeline-side READ-ONLY capability runner ("all...
    skills and recipes fire on ALL endpoints"). For the refine-hinted verbs that
    are permission=read AND take NO required args (live system state), the
    PIPELINE runs them itself + injects the real output for EVERY agent -- so a
    system-state turn is grounded on the iGPU/phone too, not only the
    tool-looping primary. SAFETY: write/launch verbs + recipes are NEVER
    auto-fired here (binding no-live-launch rule); web verbs go to
    _web_research_enrich, KB search to _rag_enrich. Best-effort + bounded.

<!-- mios-src:9b2aa36feb47 from usr/lib/mios/agent-pipe/server.py:2130-2137 -->

### Data-driven action-vs-research split

Data-driven action-vs-research split: a routed [routing.domains] domain is
    an ACTION domain (decompose into EXECUTABLE tool steps, not research facets)
    iff ANY of its SSOT verbs is permission=='write'. No keyword/app/English
    literals -- the distinction is verb PERMISSION metadata from mios.toml, so a
 new write-verb in any domain becomes 'action' automatically.
    (swarm researched 'send a discord message' instead of performing it).

<!-- mios-src:e22ba496b5a5 from usr/lib/mios/agent-pipe/server.py:2630-2635 -->

### Generative compute-need judge ("MATH(AND OTHER PYTHON...

Generative compute-need judge ("MATH(AND OTHER PYTHON
    CAPABILITIES) ... natural language!!! not verbs/keywords"). Decide, BY MEANING not
    keywords, whether fully + CORRECTLY answering needs a calculation a language model
    cannot do reliably in its head -- multi-digit/exact arithmetic, statistics, unit/
    currency conversion, counting, or a date/time difference. A small model both
    mis-computes in-head AND won't reliably call the (now ambient) sandbox tool, so the
    PIPE runs the math itself (mirrors the web prefetch). True only on a confident yes;
    degrade-CLOSED (error/None -> False = no compute prefetch, unchanged behaviour).

<!-- mios-src:fa6a8d52a398 from usr/lib/mios/agent-pipe/server.py:2651-2658 -->

### A2A-discoverable agent directory (roadmap DATA-01 / T-059)....

A2A-discoverable agent directory (roadmap DATA-01 / T-059).

    Returns the roster of every registered ``[agents.*]`` entry as an
    ``(author, name, version)`` tuple plus its A2A card link, so a discovering
    peer QUERIES this endpoint instead of reading a static file. Reuses the
    A2A AgentCard as the SSOT: ``author`` = the card provider organization,
    node ``version`` = the card version, and each entry links back to the
    node's well-known AgentCard -- a REMOTE peer (kind in
    remote-http/a2a/edge/node/mobile) advertises its OWN card + a2a base,
    while a local sub-agent is a skill of THIS node's single card. Open
    discovery surface (see _AUTH_OPEN_PATHS). Degrade-open: an unreadable
    registry or card yields an empty roster, never a 500.

<!-- mios-src:b9fb8897a488 from usr/lib/mios/agent-pipe/server.py:3179-3191 -->

### True if `url`'s host is LOCAL to the operator (loopback /...

True if `url`'s host is LOCAL to the operator (loopback / tailnet /
    private LAN / container DNS), False for a public/cloud host. Conservative:
    an unparseable or empty url is treated as local (it's not a cloud egress).

<!-- mios-src:34ce81a9651d from usr/lib/mios/agent-pipe/server.py:3340-3342 -->

### Re-read the agent/node registry + A2A peer registry from...

Re-read the agent/node registry + A2A peer registry from disk and refresh the
    LIVE module caches WITHOUT a restart (FED-G3). Removes 'restart to add an agent'.
    Degrade-open: a partial failure logs + still refreshes what it can.

<!-- mios-src:a73868ba8924 from usr/lib/mios/agent-pipe/server.py:3521-3523 -->

### U3: the AgentCard `signatures[]` is a real A2A v1.0 JWS...

U3: the AgentCard `signatures[]` is a real A2A v1.0 JWS (RFC-7515 over RFC-8785
    JCS), proven with a real Ed25519 key -- the spec mandates JWS, so the proof is a
    cryptographic sign->verify round-trip, not just a shape check. A tampered card or
    tampered signature FAILS verification; a non-EdDSA alg is rejected; the protected
    header decodes to the JOSE-standard {alg: EdDSA, kid}. Skipped cleanly where
    python3-cryptography is absent (the build host), exactly like the passport
    real-key round-trip in test_mios_a2a_principal.

<!-- mios-src:606e0131d1ae from usr/lib/mios/agent-pipe/test_mios_a2a.py:147-153 -->

### Offline tests for T-066 (A2A federation loopback smoke...

Offline tests for T-066 (A2A federation loopback smoke test).

The network/CLI half of mios-a2a-test needs a live agent-pipe; the pure
protocol helpers (build_message / extract_artifact_text / classify_task) are
exercised here with stub Task payloads so the round-trip's shape logic is
guarded without any live service.

<!-- mios-src:69d603946b75 from usr/lib/mios/agent-pipe/test_mios_a2a_loopback.py:5-11 -->

### Standalone unit test for mios_a2a_principal (WS-6 signed...

Standalone unit test for mios_a2a_principal (WS-6 signed delegation principal).

Pure stdlib + the sibling module only -- no server.py / Ed25519 keys. The real
crypto is the agent passport's _passport_sign/_passport_verify (covered by the
passport tests + operator on MiOS-DEV); here we inject fakes to prove the
deterministic glue: claim shape, text-binding, and the absent/unsigned/tamper/ok
branches the receive path relies on.

Run:  python test_mios_a2a_passport.py

<!-- mios-src:4f4d61c2c0e4 from usr/lib/mios/agent-pipe/test_mios_a2a_passport.py:4-13 -->

### Insert a no-op stand-in for the ONE heavy dependency this...

Insert a no-op stand-in for the ONE heavy dependency this gate does not require
    installed (``websockets``), leaving every OTHER runtime dep
    (fastapi/starlette/pydantic/uvicorn/httpx) as the REAL package so ``server.app`` is
    a genuine FastAPI instance. server.py imports a handful of websockets submodules at
    module load for its portal terminal proxy; an empty module satisfies the import
    without a live client (no route is exercised at import time -- daemons start in the
    FastAPI lifespan, not at import). ``setdefault`` leaves a real websockets in place
    when one IS installed.

<!-- mios-src:fd58fad5ea1e from usr/lib/mios/agent-pipe/test_mios_approutes.py:25-32 -->

### Point MIOS_TOML at the real vendor mios.toml before...

Point MIOS_TOML at the real vendor mios.toml before importing server, reusing
    test_server_import._resolve_toml when that sibling import gate is present so the
    resolution stays single-sourced; degrade to the same relative resolution when it is
    not. server.py turns into a crashing None-logger if the toml is unresolved, so this
    must run before ``import server``.

<!-- mios-src:20338cfdaa48 from usr/lib/mios/agent-pipe/test_mios_approutes.py:61-65 -->

### NG-3

NG-3: a payload handed in as a pre-serialised JSON STRING and the SAME payload
        as a parsed dict must canonicalize identically. payload is a jsonb column;
        psycopg reads it back as the parsed object at verify time, so write-time (which
        may see either form) must not diverge from verify-time (which always sees the
        parsed object) -- else the chain reports a spurious "broken" link.

<!-- mios-src:7d84c8799dae from usr/lib/mios/agent-pipe/test_mios_audit.py:106-110 -->

### The micro-LLM early-reply helpers (intent=chat reply...

The micro-LLM early-reply helpers (intent=chat reply, memory-hit judge,
    location-ask), now owned by mios_chat (the injection was reversed). Asserts
    (1) the no-network GUARDS short-circuit and (2) the degrade-open except path.
    Inputs are SYNTHETIC opaque tokens (no English example words); the REFINE lane
    is never actually called -- httpx is swapped for a client that raises and
    _env_grounding is stubbed so the system-prompt assembly stays local.

<!-- mios-src:c27eef8e3ea2 from usr/lib/mios/agent-pipe/test_mios_chat.py:386-391 -->

### The refine-driven orchestration helpers, now owned by...

The refine-driven orchestration helpers, now owned by mios_chat (the
    injection was reversed): the action-hint gate (_hints_write_action), the
    micro-LLM knowledge-gap judge (_needs_external_knowledge) and the multi-task
    queue writer (_shadow_queue_tasks). SYNTHETIC opaque verb tokens + permissions
    (no English example words); no network (the judge degrades open via the
    raising httpx stub) and no DB (the queue writer's guard paths return early).

<!-- mios-src:183e1948a3f8 from usr/lib/mios/agent-pipe/test_mios_chat.py:417-422 -->

### Standalone unit test for mios_codemode (WS-2 Code Mode pure...

Standalone unit test for mios_codemode (WS-2 Code Mode pure helpers).

Pure stdlib + the sibling module only -- no server.py / podman / DB import, so it
runs on any Python 3.10+ without the agent-pipe runtime deps. Mirrors the
test_mios_sched / test_mios_evict pattern: explicit asserts + a PASS/FAIL summary;
exit code != 0 on any failure.

Run:  python test_mios_codemode.py

<!-- mios-src:fe6a7cb70ecf from usr/lib/mios/agent-pipe/test_mios_codemode.py:4-12 -->

### Standalone unit test for the #49 enrich domain-filter...

Standalone unit test for the #49 enrich domain-filter contract.

server.py `_read_tool_enrich` restricts AUTO-added enrich verbs to the routed
domain, but must NOT drop (a) verbs refine explicitly hinted -- a compound can
span domains -- nor (b) the deterministic local_state core verbs when the turn is
a state query mis-routed to e.g. apps_windows. This pins that set-logic with a
reference impl (pure stdlib; mirrors the server.py keep computation), the same
pattern as test_mios_launch. Live behaviour is verified on MiOS-DEV.

Run:  python test_mios_compound.py

<!-- mios-src:a4070d756c4b from usr/lib/mios/agent-pipe/test_mios_compound.py:4-14 -->

### Hermetic tests for validate_config (WS-CONFIG safety net)....

Hermetic tests for validate_config (WS-CONFIG safety net).

Run standalone:  python test_mios_config_validate.py
Or via pytest:   pytest test_mios_config_validate.py

<!-- mios-src:28ff8b560b07 from usr/lib/mios/agent-pipe/test_mios_config_validate.py:3-7 -->

### A8: _deepen_until_barrier early-exits on a SATISFIED node...

A8: _deepen_until_barrier early-exits on a SATISFIED node only when the SSOT
    flag is on; degrade-open -> a judge error/timeout falls through to the
    deadline-bound loop (never under-computes). Four scenarios, observed via the
    number of (stubbed) agent coverage passes.

<!-- mios-src:336583d016da from usr/lib/mios/agent-pipe/test_mios_dag_exec.py:188-191 -->

### The dissent-extraction cutoff must read from the SSOT knob...

The dissent-extraction cutoff must read from the SSOT knob
    (DCI_FLOW_TRIGGER_CONF), not a baked literal. Drive the same flow
    with the knob raised ABOVE the challenger's 0.9 confidence and
    assert the challenge is NO LONGER extracted as dissent -- proving
    the cutoff is config-driven, then restore the knob.

<!-- mios-src:ae2e74d3a2df from usr/lib/mios/agent-pipe/test_mios_dci.py:134-138 -->

### Standalone unit test for the #54 egress-firewall generator....

Standalone unit test for the #54 egress-firewall generator.

Pure: asserts the structure of build_ruleset's output (uid scoping, always-allowed
nets, per-mode final rule, allowlist) without invoking nft, so it runs anywhere in
the drift-gate. nft *syntax* is validated separately with `nft -c` where the
binary exists. Loads the generator from tools/ via SourceFileLoader.

Run:  python test_mios_egress.py

<!-- mios-src:99b212f0c3bb from usr/lib/mios/agent-pipe/test_mios_egress.py:4-12 -->

### Standalone unit test for mios_hitl (WS-6 HITL decision...

Standalone unit test for mios_hitl (WS-6 HITL decision helpers).

Pure stdlib + the sibling module only -- no server.py / DB. The live
pending_action I/O + approval endpoints are verified by the operator on
MiOS-DEV; this covers the deterministic decision logic.

Run:  python test_mios_hitl.py

<!-- mios-src:b23ebc543e08 from usr/lib/mios/agent-pipe/test_mios_hitl.py:4-11 -->

### Stdlib assert-script for mios_hitlflow (R7 security wave)....

Stdlib assert-script for mios_hitlflow (R7 security wave).

Covers the security-critical decisions of the HITL ask-to-run + runtime
approval-gate flow:
  * _action_hash determinism + structural (key-order invariant) identity.
  * _pending_hash NULL-free, deterministic, per-action bypass key behavior
    (same action -> same key so an approval bypasses a later identical
    dispatch; a DIFFERENT action -> a DIFFERENT key so the approval never
    crosses over).
  * _hitl_gate NAME-KEYED gating using the REAL mios_secset high-privilege
    builder + the REAL mios_hitl decision helpers: a scoped high-privilege
    verb BLOCKS (gate mode, unapproved); a safe verb PROCEEDS.
  * _classify_approval_reply with a stubbed model returns approve / reject
    correctly (and degrades to 'unrelated' on error).

Run: python test_mios_hitlflow.py

<!-- mios-src:6f5103cf0f7c from usr/lib/mios/agent-pipe/test_mios_hitlflow.py:3-19 -->

### Standalone unit test for the #61 pods->k3s generated...

Standalone unit test for the #61 pods->k3s generated manifests.

Validates the COMMITTED artifacts (not the generator, which needs live pods +
podman): each manifest must parse as YAML, declare an apiVersion, carry the
deterministic AI-hint header, and contain none of the volatile fields the
generator strips -- so a malformed or un-stripped manifest can never land. Skips
cleanly if pyyaml is unavailable.

Run:  python test_mios_k3s.py

<!-- mios-src:6a5839b5edb4 from usr/lib/mios/agent-pipe/test_mios_k3s.py:4-13 -->

### A7: agent_memory recall applies the SHARED blended rerank...

A7: agent_memory recall applies the SHARED blended rerank (not flat cosine).
    With rank_age>0 a recently-saved fact OUTRANKS a stale one at EQUAL cosine
    (recency breaks the tie); at rank_age==0 the blend is inert (pure cosine), so the
    contrast proves the recency weighting drove the order. DEGRADE-OPEN: agent_memory
    has no access/tier/outcome columns -> those blend terms read neutral, only cosine
    + ts contribute, and nothing crashes.

<!-- mios-src:6d1217ae691e from usr/lib/mios/agent-pipe/test_mios_knowledge.py:198-203 -->

### Standalone unit test for mios_kvfork (WS-8 KV-cache fork...

Standalone unit test for mios_kvfork (WS-8 KV-cache fork primitives).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps. Mirrors the mios_sched /
mios_evict standalone-test pattern: explicit asserts, PASS/FAIL summary, exit
code != 0 on any failure.

Run:  python test_mios_kvfork.py

<!-- mios-src:195641361b15 from usr/lib/mios/agent-pipe/test_mios_kvfork.py:4-12 -->

### Standalone unit test for mios_lanes (WS-1). Pure stdlib +...

Standalone unit test for mios_lanes (WS-1).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps (httpx/fastapi/...). Mirrors the
mios_sched test pattern: a mock-free asyncio harness with explicit asserts and a
PASS/FAIL summary; exit code != 0 on any failure.

Run:  python test_mios_lanes.py

<!-- mios-src:2da9cf12d2ec from usr/lib/mios/agent-pipe/test_mios_lanes.py:4-12 -->

### Stdlib unit tests for mios_lanes_resolver (strangler-fig...

Stdlib unit tests for mios_lanes_resolver (strangler-fig extraction).

Drives the moved lane-resolver cluster with a fake httpx client + stubbed
config -- NO network, NO DB. Asserts: lane selection prefers the heavy lane when
its probe is up, falls back to the always-on light lane when the heavy lanes are
down, the legacy heavy/light probe is used when the resolver path raises, and the
_heavy_lane_up probe caches + degrades closed. Run: ``python test_mios_lanes_resolver.py``.

<!-- mios-src:74d2d1438d2c from usr/lib/mios/agent-pipe/test_mios_lanes_resolver.py:3-10 -->

### Standalone unit test for the deterministic launch-target...

Standalone unit test for the deterministic launch-target extraction
(server.py `_deterministic_action_route`: SSOT trailing-filler strip + word-count
+ compound-connective guard that binds an unambiguous 'open/launch <app>' to
open_app(name=<app>)).

Pure stdlib -- no server.py import, so it runs on any Python 3.11+ without the
agent-pipe runtime deps. Mirrors the test_mios_kvfork standalone pattern: a
reference impl PINS the contract, and the REAL mios.toml
[routing].launch_filler_phrases SSOT is loaded so a drift in either the list or the
logic is caught. Regression guard for the operator e2e bug where
'open notepad for me' bound name='notepad for me' and 'open spotify on my desktop'
fell through to the LLM path and mis-routed to discovery.

Run:  python test_mios_launch.py

<!-- mios-src:61ce4340e077 from usr/lib/mios/agent-pipe/test_mios_launch.py:4-18 -->

### Standalone unit test for the #54 mTLS provisioning tool....

Standalone unit test for the #54 mTLS provisioning tool.

Provisions into a temp dir and verifies the PKI is correct: the agent leaf is
signed by the CA, it is valid for BOTH client + server auth, and re-running keeps
the existing CA (so exchanged peer trust is not invalidated). Needs cryptography;
SKIPS (exit 0) if it is unavailable so the drift-gate stays portable.

Run:  python test_mios_mtls.py

<!-- mios-src:bde353015183 from usr/lib/mios/agent-pipe/test_mios_mtls.py:4-12 -->

### status_code + .json() in the OpenAI (`choices`) shape --...

status_code + .json() in the OpenAI (`choices`) shape -- MiOS is /v1-only --
    for the moved formulator/local-state tests. (`native` kept for signature
    compatibility; the retired `message` shape is no longer emitted.)

<!-- mios-src:50b1225a45a2 from usr/lib/mios/agent-pipe/test_mios_native_loop.py:157-159 -->

### Standalone unit test for mios_pg pure helpers (WS-9...

Standalone unit test for mios_pg pure helpers (WS-9 Postgres client).

Pure stdlib + the sibling module only -- no psycopg, no live Postgres (the I/O is
verified by the operator on MiOS-DEV). Run:  python test_mios_pg.py

<!-- mios-src:d94fe0196aea from usr/lib/mios/agent-pipe/test_mios_pg.py:4-8 -->

### Regression guard

Regression guard: with queue_enable OFF, _higher_priority_waiting is byte-
    identical to the T-019 probe-only path even if the queue holds a higher-priority
    turn -- so the queue can never silently change default-off preemption.

<!-- mios-src:8d8418cfe25d from usr/lib/mios/agent-pipe/test_mios_preempt.py:648-650 -->

### Standalone unit test for mios_reputation (WS / #54...

Standalone unit test for mios_reputation (WS / #54 zero-trust federation).

Pure stdlib + the sibling module only -- no server.py. Proves the deterministic
properties the peer selector relies on, especially that an all-neutral list is
returned unchanged (so reputation never alters behaviour until peers have a
track record).

Run:  python test_mios_reputation.py

<!-- mios-src:8abb2ac12c2a from usr/lib/mios/agent-pipe/test_mios_reputation.py:4-12 -->

### Standalone unit test for mios_sched.PriorityGate (WS-1)....

Standalone unit test for mios_sched.PriorityGate (WS-1).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps (httpx/fastapi/...). Mirrors the
_execute_dag_saturated standalone-test pattern: a mock-free asyncio harness with
explicit asserts and a PASS/FAIL summary; exit code != 0 on any failure.

Run:  python test_mios_sched.py

<!-- mios-src:2bdaac1e6456 from usr/lib/mios/agent-pipe/test_mios_sched.py:4-12 -->

### Under contention, a freed slot goes to a tenant UNDER its...

Under contention, a freed slot goes to a tenant UNDER its cap even over a
    HIGHER-priority waiter whose tenant is AT its cap -- one tenant can't starve another.
    Tenant A holds a slot for the whole test (A pinned AT cap); B1 holds its slot so the
    fairness moment (B1 served, A2 still queued) is observable, then A2 is served
    (degrade-open: it becomes the sole waiter).

<!-- mios-src:2372a57da968 from usr/lib/mios/agent-pipe/test_mios_sched.py:233-237 -->

### Standalone unit test for mios_selfimprove (#64...

Standalone unit test for mios_selfimprove (#64 self-improvement analyzer).

Pure stdlib + the sibling module only -- no server.py / DB. Proves the analyzer
surfaces the right findings from outcome records and does not over-react to thin
samples.

Run:  python test_mios_selfimprove.py

<!-- mios-src:585ec8342721 from usr/lib/mios/agent-pipe/test_mios_selfimprove.py:4-11 -->

### Standalone unit test for mios_selfimprove_act (T-062/T-064...

Standalone unit test for mios_selfimprove_act (T-062/T-064 ACT decision core).

Pure stdlib + the sibling modules only -- no server.py / DB / live models. Proves
the ACT half (a) STRUCTURALLY isolates the evaluator/eval/lane-config from a
proposal (anti-reward-hacking), (b) curates eval tasks by the solver-gap, and
(c) accepts a proposal ONLY when it does not regress the baseline (pass^k), with
isolation enforced before any score is consulted.

Synthetic, non-dictionary surface/id tokens throughout: the improvable/protected
sets are made-up kinds the test supplies, so a PASS proves structural set
membership rather than any baked-in English vocabulary.

Run:  python test_mios_selfimprove_act.py

<!-- mios-src:08af0d0c0828 from usr/lib/mios/agent-pipe/test_mios_selfimprove_act.py:4-17 -->

### Standalone unit test for mios_stress pure helpers (T20)....

Standalone unit test for mios_stress pure helpers (T20).

Pure stdlib + the sibling module only -- no httpx, no live agent-pipe (the live
run is exercised by the operator / the authorized direct-chat). Run:
  python test_mios_stress.py

<!-- mios-src:346d0853150b from usr/lib/mios/agent-pipe/test_mios_stress.py:4-9 -->

### Stdlib assert-script for mios_vision (refactor R9). Covers...

Stdlib assert-script for mios_vision (refactor R9).

Covers the two load-bearing branches of the extracted module with stubs (no
network / no DB):

  1. the VISION honest-error gate -- with NO vision model provisioned,
     ``_vision_complete`` returns an HONEST "vision unavailable" assistant turn
     (never a raw 5xx, never a fabricated description); ``_vision_backend_failed``
     classifies a degraded backend correctly.
  2. the CLIENT-TOOLS tool_call handback -- when the model emits a CLIENT
     (non-MiOS) tool_call, ``_client_tools_loop`` hands the whole assistant
     message back UNCHANGED for the caller to execute, and ``_client_tools_wrap``
     shapes it with finish_reason=tool_calls.

<!-- mios-src:a17a05418629 from usr/lib/mios/agent-pipe/test_mios_vision.py:3-16 -->

### Point MIOS_TOML at the repo's vendor mios.toml if present...

Point MIOS_TOML at the repo's vendor mios.toml if present (repo root = 4
    levels up from this file: usr/lib/mios/agent-pipe/), so the import exercises
    the REAL config parse on any host. Harmless if absent (readers degrade).

<!-- mios-src:1cb3f968e343 from usr/lib/mios/agent-pipe/test_server_import.py:23-25 -->
### Regression

Regression: the podman-exec stripper must not backtrack exponentially.

The flag-repetition group allowed a flag's ARGUMENT to start with '-', so
"-a -b" had two legal parses and the group backtracked exponentially (~1.64^n
measured) on model-controlled script text. The bound pinned here is wall-clock
on a pathological input rather than an assertion about the pattern string,
because the defect is behavioural; flags-with-arguments are pinned too, since
that is what the narrowed character class could plausibly break.

<!-- mios-src:7b5bbd956f27 from usr/lib/mios/agent-pipe/test_mios_dispatch_redos.py:4-12 -->
### Bounded Reflection Loop Convergence (T-385 / AGY-1983)...

Bounded Reflection Loop Convergence (T-385 / AGY-1983)

Implements bounded deliberation and reflection loops with semantic delta scoring,
enforcing deterministic termination when refinement reaches diminishing returns (delta < 0.05)
or encounters the maximum iteration ceiling (default: 3) to prevent token waste and circular debate.

<!-- mios-src:10cd7e103e6b from usr/lib/mios/agent-pipe/mios_deliberate.py:4-10 -->

### Dynamic Agent Persona Synthesis (T-384 / AGY-1982)...

Dynamic Agent Persona Synthesis (T-384 / AGY-1982)

Classifies user query intent across 6 specialized technical domains (Kernel/Systems,
Database/Storage, Security/Crypto, Networking/Mesh, AI/Inference, DevOps/CI) and
synthesizes enriched system prompts with domain-specific technical rigor and guidelines
while strictly preserving canonical project laws and OpenAI endpoint contracts.

<!-- mios-src:d583386802a0 from usr/lib/mios/agent-pipe/mios_persona.py:4-11 -->
