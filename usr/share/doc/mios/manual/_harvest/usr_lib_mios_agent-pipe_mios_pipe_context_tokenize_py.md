<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_tokenize -- the MiOS agent-pipe tokenizer seam (WS-A5...

mios_tokenize -- the MiOS agent-pipe tokenizer seam (WS-A5, the AIOS
Context-Manager token-accounting layer).

Pure stdlib so it unit-tests in isolation. Before WS-A5 the pipe estimated
tokens with bare `len(x) // 4` expressions duplicated across _fit_context, the
usage estimate, and several `[:N]` char slices -- inconsistent, and impossible
to upgrade to a real tokenizer in one place. This module is that one place.

Default backend
===============
HeuristicBackend implements the SAME ~4-chars/token approximation the pipe
already used (CHARS_PER_TOKEN = 4), so swapping the inline `// 4` for
count_text()/count_messages() is byte-for-byte behaviour-preserving.

The heuristic is a DELIBERATE, offline-safe default -- NOT a placeholder pending
a fix. The agent-pipe carries no tokenizer dependency (it must import + run with
pure stdlib, in CI and on a bare host), so the ~chars/token estimate is the
shipped measure. It is intentionally APPROXIMATE: token counts here size context
budgets and the client-visible usage estimate, where a few-percent error is
immaterial; they never gate correctness. When a real tokenizer IS provisioned
(tiktoken / a vendored HF tokenizer / the model's own tokenizer), an accurate
backend is registered via set_backend() -- the provided wiring seam -- without
editing any call site, and everything degrades back to the heuristic if that
asset is absent. server.py selects the backend from the [ai].tokenizer_backend
SSOT (only "heuristic" ships today; an unknown name logs + falls back).

<!-- mios-src:0758ca1a1d24 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:3-28 -->

### Exact OpenAI-BPE token counts via tiktoken (optional...

Exact OpenAI-BPE token counts via tiktoken (optional dependency). This is the
    OpenAI-native counter -- it matches what an OpenAI client expects from the usage
    object the pipe reports. Offline-safe: the encoding blob loads from the baked
    TIKTOKEN_CACHE_DIR (set here from the SSOT cache_dir when the process has not
    already set it), so no network is touched at runtime; with neither a cached blob
    nor network the constructor raises and the caller degrades-open to the heuristic.

    The encoding name is SSOT ([ai].tokenizer_encoding) -- never defaulted in code --
    so there is no restated literal here.

<!-- mios-src:4162f1ffe678 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:51-59 -->

### Install an accurate-count backend (must expose .name +...

Install an accurate-count backend (must expose .name + .count(text)->int) --
    the provided wiring point for an exact tokenizer once one is provisioned, so the
    heuristic default is an intentional seam, not a forgotten wire. Degrade-safe: a
    None/invalid backend is ignored (the heuristic stays), so calling this can never
    make measurement worse than the offline default.

<!-- mios-src:e64dc75cf6ee from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:114-118 -->

### Construct the token-counting backend named ``kind``, or...

Construct the token-counting backend named ``kind``, or None if it cannot be
    built (optional dependency or asset absent) so the caller degrades-open to the
    heuristic. NEVER raises.

    ``kind`` selects the IMPLEMENTATION via a small backend registry (a dispatch to
    code, like a plugin name -- NOT a content/keyword gate); the actual parameters
    (encoding / path / cache_dir) are SSOT-supplied ([ai].tokenizer_*). server.py
    owns the wiring: it reads the SSOT selector + params and installs the result via
    set_backend().

<!-- mios-src:ab2ca8730788 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:125-133 -->

### Estimated tokens of a chat prompt

Estimated tokens of a chat prompt: every message's content + (optionally)
    the serialized tool surface, measured through the ACTIVE backend.

    The contents + the tool JSON are concatenated and counted ONCE so a real
    tokenizer sees the full text (not a per-message char//N that would bypass it).
    Under the heuristic this is byte-identical to the pre-WS-A5 _fit_context estimate
    `(sum(len(content)) + len(json.dumps(tools))) // 4` -- len(concat)//4 equals
    (sum(len(content)) + len(tools_json))//4 because the parts are joined verbatim.

<!-- mios-src:be235b09b59c from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:165-172 -->
