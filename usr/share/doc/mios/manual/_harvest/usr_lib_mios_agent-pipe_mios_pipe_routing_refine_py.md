<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### MiOS agent-pipe -- REFINE intent classifier (extracted from...

MiOS agent-pipe -- REFINE intent classifier (extracted from server.py).

Verbatim move: the refine pass is the primary classifier feeding routing.
The _REFINE_SYSTEM / _REFINE_SYSTEM_LITE prompts and the refine_intent /
_salvage_refine_dispatch bodies are byte-identical to their server.py origin
(prompt-sensitive -- do not edit). server.py injects every dep that stays
behind via :func:`configure` and re-imports the names verbatim.

<!-- mios-src:653b493e232d from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:3-10 -->

### Inject the server.py symbols the refine classifier reads....

Inject the server.py symbols the refine classifier reads. Each arg keeps
    its original server name as a module global; None means 'leave as-is' so a
    partial re-inject (e.g. the live agent-registry refresh) is safe. The routing
    cutoff args (promote_chars / dispatch_arg_max_words / chat_chars /
    dispatch_chars) carry the SSOT [refine] thresholds; injecting any of them
    re-renders _REFINE_SYSTEM so its length cues match the new gates.

<!-- mios-src:3d3c1734afcd from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:79-84 -->

### Render the full REFINE classifier prompt, interpolating the...

Render the full REFINE classifier prompt, interpolating the SSOT length
    cues (REFINE_CHAT_CHARS / REFINE_DISPATCH_CHARS / REFINE_PROMOTE_CHARS) into
    the 'Length cue' block so the prompt's char hints always match the runtime
    promotion guards (one constant feeds both). Byte-identical to the original
    apart from those three interpolated cue numbers; configure() re-renders it
    after the cutoffs are injected so an mios.toml override flows into the cue.

<!-- mios-src:ea7bbec00ecd from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:172-177 -->

### Recover a deterministic one-verb dispatch when refine emits...

Recover a deterministic one-verb dispatch when refine emits PROSE.

    A small refine model (qwen3.5:4b) occasionally NARRATES instead of emitting
    the JSON envelope -- even with format=json -- when the request invites
 reasoning ("Open discord on my desktop" -> the model
    replied 'To open Discord on your desktop, I will launch_app(Discord PTB)'
    as prose, json.loads failed at char 0, the turn DROPPED to the research
    swarm -> 477s, 8 agents, fabrication, NO launch). Rather than discard the
    obvious action, salvage it. Fully generative: it only matches verb NAMES
    from the live fast-path catalog (no hardcoded app/English list).

    Returns a {"intent":"dispatch","tool":...,"args":...} dict or None.

<!-- mios-src:e8ac3c23e59c from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:569-581 -->

### Quick-refine pass. Returns the parsed plan dict or None on...

Quick-refine pass. Returns the parsed plan dict or None on
    bypass / error (caller falls through to the legacy router path).

    Bypass: trivial inputs (greetings, single-word commands) skip
    refine entirely. The existing classify_intent router handles
    them with its own chat-reply path in one LLM call -- adding a
    refine pass on top would be wasted latency. Local-compute-aware
 per operator directive 'fast and efficient for pure
    local compute'.

<!-- mios-src:5583c82b606c from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:620-628 -->

### Critic->refiner for the HEAVY agent path (ref AIOS B.1 /...

Critic->refiner for the HEAVY agent path (ref AIOS B.1 / OS-Copilot
    executor-critic-refiner). Run the DCI critic on the buffered agent
    answer; if it raises a high-confidence challenge/ask (a genuinely
    contested/complex resolution), re-invoke the backend ONCE with the
    critic's concern so the answer is revised, then return the revision.

    Fires AS NEEDED: short/simple answers (< CRITIC_REFINE_MIN_CHARS) and
    the mios-os-control dispatch fast path never reach here, so CPU
    usecases stay fast; GPU/heavy answers earn the loop. Bounded by
    CRITIC_REFINE_MAX; returns the ORIGINAL answer on any error or when
    the critic is satisfied (the common case).

<!-- mios-src:741ccf697188 from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:1050-1060 -->
