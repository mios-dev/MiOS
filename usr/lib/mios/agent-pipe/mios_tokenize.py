# AI-hint: WS-A5 tokenizer seam for the agent-pipe. Centralizes the scattered "len // 4" token estimate behind ONE pluggable interface -- count_text / count_messages / truncate_to_tokens / backend_name -- so context-fit sizing, the OpenAI usage estimate, and history/block truncation all measure tokens THE SAME WAY and a real tokenizer can replace the heuristic later without touching call sites. The default backend is the established ~4-chars/token heuristic (so behaviour is byte-identical until a better backend is configured); an optional real backend can be registered. server.py owns the wiring; this module owns the measurement.
# AI-related: ./server.py, ./mios_ctxpack.py, ./mios_compact.py, ./test_mios_tokenize.py, /usr/share/mios/mios.toml
# AI-functions: count_text, count_messages, truncate_to_tokens, backend_name, set_backend, _usage_estimate, class HeuristicBackend
"""mios_tokenize -- the MiOS agent-pipe tokenizer seam (WS-A5, the AIOS
Context-Manager token-accounting layer).

Pure stdlib so it unit-tests in isolation. Before WS-A5 the pipe estimated
tokens with bare `len(x) // 4` expressions duplicated across _fit_context, the
usage estimate, and several `[:N]` char slices -- inconsistent, and impossible
to upgrade to a real tokenizer in one place. This module is that one place.

Default backend
===============
HeuristicBackend implements the SAME ~4-chars/token approximation the pipe
already used (CHARS_PER_TOKEN = 4), so swapping the inline `// 4` for
count_text()/count_messages() is byte-for-byte behaviour-preserving. A real
tokenizer (tiktoken / a vendored HF tokenizer) can be registered via
set_backend() without editing any call site; everything degrades to the
heuristic if the asset is absent (offline-safe).
"""

from __future__ import annotations

import json
from typing import List, Optional


class HeuristicBackend:
    """The default ~chars/token estimate -- exactly the pipe's prior `len // 4`."""

    chars_per_token = 4

    @property
    def name(self) -> str:
        return f"heuristic-chars{self.chars_per_token}"

    def count(self, text: str) -> int:
        return len(str(text)) // self.chars_per_token


_BACKEND = HeuristicBackend()


def set_backend(backend) -> None:
    """Install an alternate backend (must expose .name + .count(text)->int).
    Degrade-safe: a None/invalid backend is ignored (heuristic stays)."""
    global _BACKEND
    if backend is not None and hasattr(backend, "count") and hasattr(backend, "name"):
        _BACKEND = backend


def backend_name() -> str:
    return _BACKEND.name


def _cpt() -> int:
    return max(1, int(getattr(_BACKEND, "chars_per_token", 4) or 4))


def count_text(text: str) -> int:
    """Estimated token count of one string."""
    try:
        return max(0, int(_BACKEND.count(str(text or ""))))
    except Exception:  # noqa: BLE001 -- degrade to the heuristic
        return len(str(text or "")) // 4


def count_messages(messages: Optional[List[dict]],
                   tools: Optional[list] = None) -> int:
    """Estimated tokens of a chat prompt: every message's content + (optionally)
    the serialized tool surface. Matches the pre-WS-A5 _fit_context estimate
    `(sum(len(content)) + len(json.dumps(tools))) // 4` under the heuristic."""
    total = sum(len(str((m or {}).get("content") or ""))
                for m in (messages or []) if isinstance(m, dict))
    if tools:
        try:
            total += len(json.dumps(tools, default=str))
        except (TypeError, ValueError):
            total += len(str(tools))
    return total // _cpt()


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate `text` to at most ~max_tokens (rstripped). Token-budget-aware
    replacement for the bare `text[:N]` char slices; under the heuristic the
    char budget is max_tokens * chars_per_token, so a [:200] slice == 50 tokens."""
    s = str(text or "")
    n = max(0, int(max_tokens))
    if count_text(s) <= n:
        return s
    budget = n * _cpt()
    return s[:budget].rstrip()


def _usage_estimate(prompt: str, completion: str) -> dict:
    """OpenAI `usage` object (Tier-0 conformance; OWUI + clients read it). MiOS is
    a multi-call pipeline, so this reports a ~4-chars/token estimate of the
    CLIENT-VISIBLE exchange (user query + final answer) -- an honest per-turn
    approximation for the client's token display, NOT a faked single-model-call
    number. A future per-stage back-end usage aggregation can replace it."""
    pt = max(1, count_text(prompt))       # WS-A5 tokenizer seam (was //4)
    ct = max(1, count_text(completion))
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}
