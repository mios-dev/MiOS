<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_pdp -- the MiOS agent-pipe Policy Decision Point...

mios_pdp -- the MiOS agent-pipe Policy Decision Point (WS-A9, the AIOS
Access-Manager capability gate).

Pure stdlib so it unit-tests in isolation, in the sibling-module style of
mios_sched / mios_toolconflict / mios_trace. server.py owns the wiring (the
dispatching-agent + request-user contextvars, the audit-event emit, and the
SSOT [agents.<name>] / [users.<name>] policy keys); this module owns only the
DECISION: given a verb + a caller's policy, allow or deny.

The bypass it closes
====================
Before WS-A9 the per-agent and per-user RBAC ran ONLY at surface-build time
(pruning the model-facing tool list). The dispatch chokepoint did taint-firewall
+ HITL + enum validation but NO capability check -- so a verb absent from the
filtered surface (a stale tool_call, a direct/MCP/A2A caller, a model that
fabricated a name) would still dispatch. WS-A9 routes BOTH the surface filters
AND the dispatch gate through THIS one decide(), so surface and dispatch can
never diverge.

The fail-OPEN defect it fixes
=============================
The old filters computed `max_rank = rank(mp) if mp in TIERS else None`, i.e. a
max_permission naming an UNKNOWN tier (a config typo) collapsed to None == "no
ceiling" -> the caller silently kept the FULL surface. That is fail-OPEN on the
security axis. resolve_ceiling() now returns rank 0 (the safest tier only) for a
non-empty-but-unknown ceiling -> FAIL CLOSED. (An empty/absent max_permission is
still "no ceiling", the genuine no-op default.)

Decision semantics (decide)
===========================
  * `name` in denied_verbs            -> DENY  (applies to verbs AND non-verbs).
  * not a catalog verb (recipe/skill/MCP/client tool) -> ALLOW (only denied applies).
  * allowed_verbs set and `name` not in it            -> DENY.
  * max_permission ceiling set and the verb's tier outranks it -> DENY.
  * otherwise ALLOW.
An empty policy (no denied/allowed/ceiling) trivially allows everything -> the
ZERO-behaviour-change default for single-user MiOS.

<!-- mios-src:9ca01ba07d17 from usr/lib/mios/agent-pipe/mios_pipe/access/pdp.py:3-40 -->

### Ceiling rank for a configured max_permission. "" / absent...

Ceiling rank for a configured max_permission.

      ""  / absent      -> None  (no ceiling -- the genuine no-op default)
      a KNOWN tier       -> its rank
      a NON-EMPTY UNKNOWN tier -> 0  (FAIL CLOSED: only the safest tier passes)

    The last case is the WS-A9 fix for the old fail-OPEN behaviour (unknown ->
    None -> no ceiling -> full surface granted on a config typo).

<!-- mios-src:463678e6cce3 from usr/lib/mios/agent-pipe/mios_pipe/access/pdp.py:79-86 -->
