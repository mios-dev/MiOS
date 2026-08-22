<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Sub-agent /v1 tool-loop + its anti-disclaimer / closed-loop...

Sub-agent /v1 tool-loop + its anti-disclaimer / closed-loop guards.

Extracted verbatim from ``server.py``. Holds ``_v1_secondary_tool_loop`` (the
universal pipe-side OpenAI tool-loop every /v1 sub-agent runs through -- MiOS is
/v1-only, so this is the single tool-loop mechanism), plus the load-bearing loop
guards it relies on: the anti-disclaimer ``_TOOL_NUDGE`` +
``_looks_like_disclaimer``, the no-progress signature ``_tool_call_sig``, the
failure verdict ``_tmsgs_indicate_failure``, the closed-loop ``_REPLAN_NUDGE``
and the ``_daemon_diagnose`` monitor pass. ``server.py`` re-imports every name
under its original alias so the module's public surface is byte-identical.

The moved bodies are unchanged. ``_exec_tool_calls`` / ``_rescue_tool_calls``
(mios_toolexec) and ``loads_lenient`` (mios_jsonsalvage) are imported directly
from those siblings; the remaining server-side symbols the loops touch (the
config scalars, the ``_DAEMON_DIAGNOSE_*`` constants and the helpers
``_apply_outbound_auth`` / ``_endpoint_supports_parallel_tools``) are injected
via :func:`configure` (one-way module boundary -- this module never imports
``server``).

<!-- mios-src:d764a4a8ab48 from usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py:3-21 -->

### Stable (name + sorted-args) signature of a tool_call, for...

Stable (name + sorted-args) signature of a tool_call, for the loop's
    no-progress / runaway guard: if a round re-emits ONLY calls already made,
    the loop breaks instead of repeating forever (universal-loop slice 3).

<!-- mios-src:03dd8b4132ca from usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py:37-39 -->

### True if any call in the batch targets a state-changing...

True if any call in the batch targets a state-changing verb, judged by
    the SSOT verb-catalog permission tier (write/interactive) -- NOT a hardcoded
    lexical read-only allowlist (Law 7). Unknown/read-tier verbs are read-only.
    Same permission classification reflect.py and the risk-tier sandbox use, so
    the write/failure gate generalises across every verb and stays SSOT-driven.

<!-- mios-src:644a494943c3 from usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py:148-152 -->

### DAEMON-DIAGNOSE ("the daemon monitors the pipeline and...

DAEMON-DIAGNOSE ("the daemon monitors the pipeline and reports
    back"): a FRESH monitor-LLM pass over a FAILED step -- WHY it likely failed + a
    DIFFERENT concrete action to try -- so the closed-loop retry is GUIDED, not a blind
    re-run. A SECOND perspective (not the model that just gave up). Short + bounded +
    degrade-open: any error/empty/disabled -> '' (caller falls back to the generic nudge).

<!-- mios-src:6b1e7b3d9c13 from usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py:180-184 -->

### Pipe-side READ-ONLY OpenAI tool-loop for a /v1 sub-agent...

Pipe-side READ-ONLY OpenAI tool-loop for a /v1 sub-agent (opencode :8633,
    hermes, daemon-agent, any node bound to a /v1 endpoint -- MiOS is /v1-only, so
    this is the single tool-loop mechanism for the /chat/completions shape): POST
    (non-streaming) -> read message.tool_calls (RESCUING a narrated call from
    content when the field is empty -- the opencode ```json webfetch``` lie) ->
    execute the read verbs via the broker -> append role:tool -> re-call, up to
    SECONDARY_TOOL_MAX_ITERS or until the agent stops calling tools (SATISFIED).
    A self-looping agent returns no tool_calls -> ONE pass, no-op. Returns the
    augmented messages ready for the final (streamed or complete) answer.
    Endpoint-agnostic: `ep` comes from the agent's binding map, no port literals
 here ('any agent/model on any node/endpoint, no
    hardcodes').

<!-- mios-src:598439faa436 from usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py:216-227 -->
