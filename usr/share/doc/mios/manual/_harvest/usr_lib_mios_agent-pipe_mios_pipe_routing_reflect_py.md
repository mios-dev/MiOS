<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Reflection / self-assessment cluster (per-turn DoD verdict...

Reflection / self-assessment cluster (per-turn DoD verdict + failed-step reflection).

Extracted verbatim from ``server.py``. ``_inline_satisfaction_check`` runs the
synchronous Definition-of-Done check on the CURRENT turn and emits a
``user_query_(un)satisfied`` event; ``reflect_on_step_failure`` is the ReWOO
single-step reflection that turns a failed DAG node into one corrected step.
``server.py`` re-imports both names under their original aliases so the public
surface is byte-identical.

The DB writers, the verb catalog, the REFINE_* model-call constants and the
``_REFLECT_SYSTEM`` prompt are injected via :func:`configure` (one-way module
boundary -- this module never imports ``server``); ``_recent_reflections`` and
``loads_lenient`` come from sibling modules directly.

<!-- mios-src:222c023806a2 from usr/lib/mios/agent-pipe/mios_pipe/routing/reflect.py:3-16 -->

### CONFIRMATION ENGINE. Run a synchronous Definition-of-Done...

CONFIRMATION ENGINE. Run a synchronous
    Definition-of-Done check on THIS turn and emit a
    user_query_(un)satisfied event for the current session. mios-daemon's
    async loop ticks every 30s and only sees PRIOR turns; without this
    inline check, polish never knows whether the current turn actually
    succeeded and can't ground-truth the wrapped reply against it.

    Two signal sources, in priority order:
      1. tool_call rows agent-pipe recorded this turn (dispatch / DAG
         fast-paths write these) -> AND-fold their success fields.
      2. The agent-path signals `agent_tools_called` (verb names the
         sub-agent invoked inside its OWN tool-loop, captured from the
         stream) + `agent_answered` (the sub-agent produced a non-empty
         final answer). Under unify-on a verb like mios-os-control runs
         INSIDE Hermes, so agent-pipe records NO tool_call row for it --
         "no rows" then means the agent handled the turn, NOT that it
         failed. Treating that as `no_tools_seen -> unsatisfied` was the
         false-negative that made polish report failure on a succeeded
         verb and made the critic re-litigate a done answer (the
         "succeeds early then reports failed" bug). A delivered answer
         is DoD-met: the turn is DONE. Whether the ACTION inside it
         succeeded is then carried by the agent's own answer + any
         recorded rows -- polish relays a failure the agent states, but
         is no longer told the whole turn failed.

    Returns the emitted verdict dict {kind, payload} or None when
    there is nothing to judge. The agent-path caller uses the returned
    kind to HALT the chain (skip the critic re-pass) on a confirmed
    success. Best-effort: any DB hiccup returns None instead of
    failing the turn.

<!-- mios-src:ea24cac422b4 from usr/lib/mios/agent-pipe/mios_pipe/routing/reflect.py:114-143 -->

### ReWOO-style reflection

ReWOO-style reflection: route a failed DAG step back to the
    SAME small refine model with the failure context and ask for a
    single corrected step. Returns {tool, args, rationale} dict
    or None on timeout/empty.

    Distinct from the retry-same-args loop (PLANNER_REFLEXION_CAP):
    that retries transient errors; this REPLACES the args/tool when
    the failure is structural (wrong verb, missing arg, wrong path).
    Three-stage Reflect/Call/Final pipeline -- caller bounds the
    number of reflection turns to 1, so a stubborn failure surfaces
    as a real error instead of looping (per the published
    Structured Reflection termination contract).

<!-- mios-src:53cf4589cdee from usr/lib/mios/agent-pipe/mios_pipe/routing/reflect.py:253-264 -->

### Pull recent mios-daemon satisfaction verdicts (Phase E.1)....

Pull recent mios-daemon satisfaction verdicts (Phase E.1).
    These are post-hoc audit rows the daemon emits every ~30s based
    on AND-folding tool_call outcomes against refine intent. Polish
    uses them to ground the response in CROSS-TURN truth -- if the
    operator's previous query was flagged unsatisfied, the next
    response shouldn't paraphrase it as having worked.

<!-- mios-src:490cafed2754 from usr/lib/mios/agent-pipe/mios_pipe/routing/reflect.py:378-383 -->
