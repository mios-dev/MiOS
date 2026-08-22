<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### OpenAI-streaming SSE chunk + status-emit primitives...

OpenAI-streaming SSE chunk + status-emit primitives (extracted from server.py).

Every builder returns ``bytes`` ready to write to the SSE response stream, or (for
``_stream_answer``) async-yields them. Moved verbatim from ``server.py``; the
module is pure (stdlib + ``json`` only) and ``server.py`` re-imports every name so
its public surface is unchanged.

<!-- mios-src:34fb1217e136 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:3-9 -->

### Build an OpenAI-streaming SSE chunk. `reasoning` populates...

Build an OpenAI-streaming SSE chunk. `reasoning` populates the
    standard `delta.reasoning_content` field (OpenAI/OpenRouter/DeepSeek
    convention) -- OWUI renders it as a native Thinking dropdown and
    strict clients (Firefox Smart Window) ignore it, showing only the
    clean `content` answer. Optional `mios_status` carries pipe-internal
    phase emits (👂 prompt, 🧭 route, 🛠️ tool, ✅) that translator gateways
    lift into their native status surfaces; stock clients ignore it.

<!-- mios-src:f82f51405a58 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:33-39 -->

### Stream a reasoning/trace delta on the correct channel for...

Stream a reasoning/trace delta on the correct channel for the surface.

    ``reasoning_ok`` carries the consuming surface's capability (set per-request
    from the ``x-mios-reasoning-ok`` hint the OWUI pipe advertises; ``None`` when
    unknown):

    * ``True``  -- reasoning-aware surface (OWUI / Hermes desktop): pin the trace
      to ``delta.reasoning_content`` REGARDLESS of ``[observability].debug`` so it
      renders live in the native Thinking pane and never pollutes the answer
      ``content`` (final answer stays the only thing in ``content`` -- KV-safe,
      OWUI #21815). Full visibility, replay-safe.
    * ``False`` -- a surface that DECLARED itself content-only: fold the trace
      inline as ``content`` so strict clients (which ignore ``reasoning_content``)
      still render it. Visibility preserved; MiOS owns the replay-strip.
    * ``None``  -- unknown surface: legacy routing, ``[observability].debug``
      decides (byte-identical to before the hint existed -- degrade-open).

    The mandate is full visibility on EVERY surface; this only routes WHICH
    channel carries the trace, never suppresses it.

<!-- mios-src:2484901f8e75 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:66-84 -->

### Phase -> (emoji, label) for the SSE status strip....

Phase -> (emoji, label) for the SSE status strip. Personable
    defaults here; each phase is OVERRIDABLE from mios.toml
    [owui.status_phases.<phase>] = { emoji = "..", label = ".." } so the
    operator tunes MiOS-Agent's voice without touching code (SSOT; no
 hardcoded UI strings locked in the hot path).
    'better emitters / more detailed and personable'.

<!-- mios-src:deb4d8c6c02a from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:95-100 -->

### Humanistic-label variant of _sse_status. Looks up the phase...

Humanistic-label variant of _sse_status. Looks up the phase
    in _HUMAN_LABELS, emits the casual label + emoji. `detail` is
    optional and should ALSO be human-facing prose (e.g. "for 22
    seconds", "almost there") -- NOT a model id / args JSON /
    intent token. If you find yourself wanting to thread technical
    info through here, log it to the event table instead.

<!-- mios-src:f1b6e271b360 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:125-130 -->

### Emit a content-empty SSE chunk whose only purpose is the...

Emit a content-empty SSE chunk whose only purpose is the
    `mios_status` field. Standard OpenAI clients see a no-op delta
    + ignore the extra field. Translator gateways pull the phase
    info from `mios_status` and surface it natively (OWUI's
    event_emitter status, Hermes Discord's reactions, etc.).

    Prefer _sse_status_phase() for new emit sites -- it picks the
    canonical humanistic label from _HUMAN_LABELS. This raw form
    stays available for one-off cases where the phase mapping
    doesn't fit.

<!-- mios-src:2de1893c0a0b from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:138-147 -->

### Yield ONE _sse_status per recorded enrich STEP ("need...

Yield ONE _sse_status per recorded enrich STEP ("need
    emitters for every step end-to-end" -- not one whole-loop summary). Covers
    the web steps (search / each page read / each deep-crawl / each drill pass,
    recorded by _web_research_enrich) and the READ-only tool runs (recorded by
    _read_tool_enrich). Each emit also persists in the reasoning log via
    _sse_status. Yields nothing when no steps ran.

<!-- mios-src:a3f95f845ed3 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:172-177 -->

### SHORT, operator-facing description of what a DAG node is...

SHORT, operator-facing description of what a DAG node is DOING -- the
 active step's CONTEXT ("emits should show actual steps
    relevant to the current active step's context"). Derived from the node's
    OWN data -- an agent node's sub-task, or a verb node's key arg -- NOT the
    internal model/endpoint (which read as a leak). No LLM call, no hardcoded
    topic text: it's the step's literal intent.

<!-- mios-src:1ce609869330 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:193-198 -->

### Per-endpoint live emitter ("endpoint emitters for each ai...

Per-endpoint live emitter ("endpoint emitters for
    each ai endpoint/node"). One status event naming an AI node as the chain
 ENGAGES it / it RESPONDS / goes silent. `context` is
    a short description of the node's CURRENT STEP -- its sub-task or the verb
    arg -- so the emit reflects the active step's context, not just a glyph.
    The lane/model/endpoint internals stay OUT (they read as a leak); context
    is the WHAT (operator-facing), not the HOW (plumbing).

 the LABEL must be GENERATIVE -- indicative of the
    FUNCTION being performed, NOT the internal agent/function name (research-
    dgpu-1, hermes, opencode, ...). So the label = the node's actual sub-task
    (`context`), falling back to its semantic ROLE as a plain word (research /
    reasoning / coding -- a capability descriptor, not a node name) and never
    the registry key. The internal name is dropped entirely from the emit.

<!-- mios-src:544a9e760256 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:219-232 -->

### Yield the final answer in small character-exact chunks so...

Yield the final answer in small character-exact chunks so OWUI renders
    it progressively (live 'typing') instead of one end-of-turn burst -- the
    "thinking prints then switches to the refined copy" jolt (operator
). Pacing is bounded so long answers stream in ~1.2s, not slower.
    Char-slicing preserves the text byte-for-byte (markdown/code intact).

<!-- mios-src:5806fe0e99a1 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:243-247 -->

### Best-effort read of the war-room activity sink (F-011): a...

Best-effort read of the war-room activity sink (F-011): a JSONL sibling of
    the hermes-tail state file into which mios-a2o appends per-task start/finish
    transitions when `[frontier].stream_to_reasoning` is on. Returns event dicts
    newer than seen_ts (may be empty). Degrade-open: when the flag is off the file
    is never created, so this returns [] and `_tail_latest_status` is byte-
    identical to before. Path from MIOS_A2O_STREAM_PATH (SSOT), else derived as a
    sibling of the hermes-tail path so no transport constant is restated.

<!-- mios-src:2ce205584700 from usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py:278-284 -->
