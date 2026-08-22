<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### VISION + CLIENT-TOOLS responders (refactor R9). Extracted...

VISION + CLIENT-TOOLS responders (refactor R9).

Extracted VERBATIM from ``server.py`` -- the two image-/tool-bearing fast-path
branches of ``/v1/chat/completions`` that bypass refine/council/polish. The
VISION branch (``_vision_complete`` + the inline-remote-image pre-step + the
honest-error gate) proxies an image turn to the local VLM and never fabricates a
description. The CLIENT-TOOLS hybrid loop (``_client_tools_complete`` and its
cluster) runs an OpenAI client-tools turn where MiOS asserts its identity, merges
its verb surface server-side, executes MiOS verbs via the broker, and rides only
the caller's own tool_calls back. Both clusters moved byte-identically.

Sibling helpers are imported directly; every server-side symbol is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).
``server.py`` re-imports every moved name under its original alias so the
importable surface is byte-identical.

<!-- mios-src:54abcbacdadb from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:3-18 -->

### True if any message carries OpenAI vision content (a...

True if any message carries OpenAI vision content (a content list with
    an image_url / input_image part) -- the signal to route this turn to the
    local VLM instead of the text executor (which cannot see images).

<!-- mios-src:2935f6240fc4 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:97-99 -->

### Resolve a media-asset URL from a page's HTML metadata --...

Resolve a media-asset URL from a page's HTML metadata -- GENERIC (JSON-LD
    contentUrl, og:image, og:video, twitter:image), no site-specific keyword, so it
    works for Tenor/Imgur/etc. First hit wins (operator rule: no hardcoded domains).

<!-- mios-src:cca5b62281b8 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:160-162 -->

### Rewrite remote image_url URLs in `messages` to INLINED...

Rewrite remote image_url URLs in `messages` to INLINED base64 data URLs the
    local llama.cpp VLM can actually see (it doesn't fetch URLs + rejects page URLs).
    Per image: fetch the URL; if it's a PAGE (text/html, e.g. a Tenor GIF page),
    resolve to its real media via HTML metadata then fetch that; for an animated
    GIF/WEBP extract a middle frame (Pillow); re-encode to PNG; inline. Mutates
    `messages` in place. Returns False if a REMOTE image could NOT be inlined, so the
    caller returns an honest 'couldn't fetch' turn instead of letting the VLM guess.
    Already-inlined data: URLs (OWUI) and non-image parts are untouched (no regress).

<!-- mios-src:403353c36f89 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:179-186 -->

### Proxy an image-bearing turn to the local VLM...

Proxy an image-bearing turn to the local VLM (OpenAI-compatible, on the
    dGPU lane). Streams the VLM SSE verbatim; non-stream returns its JSON. When
    the vision model is unprovisioned / fails to load, returns an HONEST 'vision
 unavailable' assistant turn instead of relaying a raw 5xx (
    'FIX ALL VISION' -- the confusing leaf error was the reported failure).

<!-- mios-src:e3b078589475 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:245-249 -->

### True when the CALLER supplied its own OpenAI tools[] -- the...

True when the CALLER supplied its own OpenAI tools[] -- the signal that this
    is client-side tool-calling (the client executes the functions and wants
    tool_calls back), NOT a MiOS-orchestrated turn. OWUI strips tools before
    calling the pipe and the mios CLI is Hermes-direct, so this is False for them
    (zero regression). Empty/missing tools -> False (normal orchestration).

<!-- mios-src:4e8dd585c337 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:311-315 -->

### A returned tool_call is MiOS-executable SERVER-SIDE when it...

A returned tool_call is MiOS-executable SERVER-SIDE when it resolves to a real
    MiOS verb -- EVEN IF the client also shipped it. The Hermes desktop app ships the
    WHOLE MiOS MCP surface (launch_windows_app, windows_desktop_type_text, ...) as its
    own tools; relaying those back for it to self-execute via MCP was the failure path
    ('open notepad and type hello' mis-fired -- malformed/parallel calls, nothing ran,
). Running MiOS verbs HERE via the proven broker (dispatch_mios_
    verb) is reliable, ORDER-preserving, and does NOT double-execute (the loop appends
    the RESULT, not the tool_call, so nothing rides back for the client to re-run).
    Only genuinely non-MiOS client tools (browser_*, terminal, IDE ops) -- which the
    server CANNOT run -- ride back to the caller.

<!-- mios-src:875be6931f08 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:360-369 -->

### Prepend the FULL MiOS root contract (/MiOS.md via...

Prepend the FULL MiOS root contract (/MiOS.md via _agent_contract) PLUS the
    client-tools addendum to the caller's leading system message (or add one).
    WS-B: the Zen path now gets the SAME root-MD grounding every other MiOS agent
    gets, instead of drifting on a bespoke identity string. Server-side only -- the
    client never sees it, so it can't accumulate across the multi-request loop.

<!-- mios-src:b89537e47c56 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:379-383 -->

### One non-stream POST to the tool backend, with heavy->light...

One non-stream POST to the tool backend, with heavy->light FALLBACK on any
    non-200 + diagnostic logging. The heavy lane (SGLang) can 400 a tool surface it
 rejects (the Hermes REPL got 'No reply' because the loop
    treated a heavy-lane 400 as an empty completion). On a non-200 we LOG the body +
    a request summary (so the cause is finally visible) and retry the always-on light
    lane (a different engine often accepts what the heavy lane rejected). Returns {}
    (never raises) when neither lane yields a 200, so the loop's synthesis / never-
    empty fallback engages instead of the whole turn erroring out.

<!-- mios-src:b702f79c4173 from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:395-402 -->

### STREAM the backend response verbatim for a full-agent...

STREAM the backend response verbatim for a full-agent client that carries its
    OWN MiOS tools (Hermes desktop app): inject MiOS identity, enable thinking, forward
    the client's tools, and relay the SSE byte-for-byte so content / reasoning /
    tool_calls stream LIVE -- no compute-then-burst dead wait. The client executes its
    own tool_calls in its own loop (it has the tools), so no server-side merge is
    needed; that merge is only for tool-less clients (Zen) via the hybrid loop.

<!-- mios-src:19d09ac17f1e from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:620-625 -->

### OpenAI client-tool turn (Zen smart-window et al.) as a...

OpenAI client-tool turn (Zen smart-window et al.) as a HYBRID loop: MiOS
    asserts its own identity, the MiOS verb surface is merged alongside the
    caller's browser tools, MiOS verbs execute server-side (so 'open notepad'
    actually launches), and only the caller's own tool_calls ride back to it.
    Falls back to a verbatim relay if the loop errors so browsing never regresses.
    NEVER runs refine/council/polish. Twin of _vision_complete.

<!-- mios-src:2428458e8e4b from usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py:662-667 -->
