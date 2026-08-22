<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### RBAC / PDP / quota + human-in-the-loop policy decision...

RBAC / PDP / quota + human-in-the-loop policy decision plane.

Extracted verbatim from ``server.py``. Holds the least-privilege capability
gate (the #55 risk lattice + per-agent/per-user surface filters routed through
the shared :mod:`mios_pdp` core), the #62 human-in-the-loop block-reason + the
out-of-process policy arbiter, the WS-6 per-user quota gate, and the WS-A9
dispatch-time Policy Decision Point.

SECURITY-CRITICAL: the gates are NAME-KEYED on verb keys and permission tiers.
The moved bodies are byte-identical to the originals -- no verb key, gate name,
permission tier, or set-membership test was renamed or rewritten. ``mios_pdp``
(aliased ``_pdp``) and ``mios_quota`` are imported directly; ``_toml_section``
comes from :mod:`mios_config`; every other server-side symbol these helpers
touch (the verb / recipe catalogs, the agent registry, the HITL / client /
dispatch ContextVars, ``_pending_hash``, ``_get_client`` and the DB-event
helpers) is injected via :func:`configure` (one-way module boundary -- this
module never imports ``server``). ``server.py`` re-imports every name under its
original alias so the module's public surface is byte-identical.

<!-- mios-src:d0f2431b5d62 from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:3-21 -->

### The permission tier that actually governs THIS call....

The permission tier that actually governs THIS call. Umbrella verbs that
    dispatch to a NAMED sub-action with its own permission (os_recipe -> a named
    [recipes.*]) must be gated by the RECIPE's tier, not the umbrella verb's
    worst-case 'interactive' -- otherwise HITL block-mode neutralizes even the
    read-only recipes (service-status / show-network / disk-usage / os-control-
    health) the agent needs for routine OS introspection. Falls back to the
    verb's own permission. Degrade-open: any lookup miss -> the verb tier.

<!-- mios-src:9316435d079d from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:119-125 -->

### 62: the [ai] RISK-TIER half of the HITL decision. In BLOCK...

#62: the [ai] RISK-TIER half of the HITL decision. In BLOCK mode return a
    human-readable refusal reason if `tool`'s effective tier is at/above
    [ai].hitl_threshold; AUDIT logs + proceeds (None); OFF is inert (None). The
    block/observe verdict is computed by the SINGLE shared resolver
    (``mios_hitl.decide``) that the [hitl] verb-scope gate also routes through, so the
    two HITL gates can no longer disagree (the stricter-wins / fail-safe combine lives
    in the resolver). Degrade-open: never raises, never gates on error. For os_recipe
    the effective tier is the NAMED recipe's, not the umbrella verb's.

<!-- mios-src:2767dbc352c3 from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:139-146 -->

### Consult the external policy arbiter for a high-risk action...

Consult the external policy arbiter for a high-risk action; return a refusal
    reason on DENY, else None (allow/not-applicable). No-op when no arbiter URL is
    configured. Degrade-open per _HITL_ARBITER_FAIL.

<!-- mios-src:58c6ac6a1c98 from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:185-187 -->

### WS-2 per-agent RBAC + #55 capability/risk gate: restrict a...

WS-2 per-agent RBAC + #55 capability/risk gate: restrict a dispatched
    agent's tool surface to what its role is permitted. SSOT:
    [agents.<name>].denied_verbs / .allowed_verbs / .max_permission in mios.toml
    (layered vendor<etc<user, surfaced via _AGENT_REGISTRY). No-op when none is
    set -> ZERO behaviour change. Only gates BARE VERBS (names in _VERB_CATALOG):
    names in denied_verbs are dropped; if allowed_verbs is set, any verb NOT in it
    is dropped; if max_permission is set, any verb whose permission tier outranks
    it is dropped. Non-verb tools (recipes/skills/MCP/client tools) pass through
    untouched unless explicitly named in denied_verbs.

<!-- mios-src:b8a1aaa7cac3 from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:218-226 -->

### 60 WS-6 per-USER authz: restrict the dispatched tool...

#60 WS-6 per-USER authz: restrict the dispatched tool surface by WHO the
    request is from -- the per-USER axis, complementing _agent_rbac_filter's
    per-AGENT axis. SSOT: [users.<name>].denied_verbs / .allowed_verbs /
    .max_permission in mios.toml, matched to the principal the chat surface
    forwarded (_client_env user_name / user_email). No-op when no [users.*] entry
    matches the current user -> ZERO behaviour change (default; single-user MiOS is
    unaffected). Same verb-gating semantics + risk lattice as #55.

    SCOPE NOTE: this keys on the surface-CLAIMED identity. Cryptographic
    SIGNED-principal verification (the 'signed principal' half of #60) is a further
    step -- until then this is policy over a TRUSTED-surface identity, not an auth
    boundary against a forged caller.

<!-- mios-src:950e87369b91 from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:276-287 -->

### WS-6 per-user rate/budget gate at the dispatch chokepoint....

WS-6 per-user rate/budget gate at the dispatch chokepoint. Counts one
    request per verb dispatch for the matched [users.*] principal; DENY when over
    the user's rpm_limit / daily_budget. Returns a refusal reason on deny, else
    None. INERT when the principal has no quota config (the default), and
    degrade-open (a quota bug must never block real work).

<!-- mios-src:940d7287c531 from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:407-411 -->

### WS-A9 dispatch-time Policy Decision Point. Re-checks the...

WS-A9 dispatch-time Policy Decision Point. Re-checks the per-AGENT
    (_dispatch_agent_var) and per-USER (_match_user_cfg) capability policy for
    `verb` at the SINGLE dispatch chokepoint, through the SAME mios_pdp core the
    surface filters use -- so a verb pruned from the model surface (or named by a
    stale/MCP/A2A/fabricated call) can NOT still dispatch (the RBAC bypass WS-A9
    closes). Returns a refusal reason on DENY, else None. Degrade-open: an
    unexpected error proceeds (a PDP bug must never block real work); an EXPLICIT
    policy deny always blocks.

<!-- mios-src:5d1bfd67a70c from usr/lib/mios/agent-pipe/mios_pipe/access/policy.py:432-439 -->
