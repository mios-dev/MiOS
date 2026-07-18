# AI-hint: WS-A5 tokenizer seam for the agent-pipe. Centralizes the scattered "len // 4" token estimate behind ONE pluggable interface -- count_text / count_messages / truncate_to_tokens / backend_name -- so context-fit sizing, the OpenAI usage estimate, and history/block truncation all measure tokens THE SAME WAY and an accurate tokenizer can replace the heuristic via set_backend (when one is provisioned) without touching call sites. The default backend is the established ~4-chars/token heuristic -- a DELIBERATE offline-safe default (the agent-pipe carries no tokenizer dependency), not a placeholder: behaviour is byte-identical until a better backend is configured. server.py selects the backend from the [ai].tokenizer_backend SSOT; this module owns the measurement.
# AI-related: ./server.py, ./mios_ctxpack.py, ./mios_compact.py, ./test_mios_tokenize.py, /usr/share/mios/mios.toml
# AI-functions: count_text, count_messages, truncate_to_tokens, backend_name, set_backend, make_backend, _usage_estimate, class HeuristicBackend, class TiktokenBackend, class HFTokenizerBackend
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
"""

from __future__ import annotations

import json
import os
from typing import List, Optional


class HeuristicBackend:
    """The default ~chars/token estimate -- exactly the pipe's prior `len // 4`."""

    chars_per_token = 4

    @property
    def name(self) -> str:
        return f"heuristic-chars{self.chars_per_token}"

    def count(self, text: str) -> int:
        return len(str(text)) // self.chars_per_token


class TiktokenBackend:
    """Exact OpenAI-BPE token counts via tiktoken (optional dependency). This is the
    OpenAI-native counter -- it matches what an OpenAI client expects from the usage
    object the pipe reports. Offline-safe: the encoding blob loads from the baked
    TIKTOKEN_CACHE_DIR (set here from the SSOT cache_dir when the process has not
    already set it), so no network is touched at runtime; with neither a cached blob
    nor network the constructor raises and the caller degrades-open to the heuristic.

    The encoding name is SSOT ([ai].tokenizer_encoding) -- never defaulted in code --
    so there is no restated literal here."""

    def __init__(self, *, encoding, cache_dir=None) -> None:
        if not encoding:
            raise ValueError("tiktoken backend needs an encoding (SSOT [ai].tokenizer_encoding)")
        if cache_dir and not os.environ.get("TIKTOKEN_CACHE_DIR"):
            os.environ["TIKTOKEN_CACHE_DIR"] = str(cache_dir)
        import tiktoken  # optional dep; ImportError -> caller degrades-open
        self._enc = tiktoken.get_encoding(str(encoding))
        self._encoding = str(encoding)

    @property
    def name(self) -> str:
        return f"tiktoken-{self._encoding}"

    def count(self, text: str) -> int:
        # disallowed_special=() so a literal special-token string in user text is
        # counted as ordinary bytes, never raising.
        return len(self._enc.encode(str(text), disallowed_special=()))

    def truncate(self, text: str, max_tokens: int) -> str:
        ids = self._enc.encode(str(text), disallowed_special=())
        n = max(0, int(max_tokens))
        return self._enc.decode(ids[:n]) if len(ids) > n else str(text)


class HFTokenizerBackend:
    """Exact token counts from a model's OWN HuggingFace tokenizer.json via the
    `tokenizers` package (optional dependency) -- the most accurate counter for a
    specific served model. `path` is the SSOT [ai].tokenizer_path to a vendored
    tokenizer.json; a missing dep/file raises and the caller degrades-open to the
    heuristic."""

    def __init__(self, *, path) -> None:
        if not path:
            raise ValueError("hf tokenizer backend needs a tokenizer.json path (SSOT [ai].tokenizer_path)")
        from tokenizers import Tokenizer  # optional dep
        self._tok = Tokenizer.from_file(str(path))
        self._path = str(path)

    @property
    def name(self) -> str:
        return f"hf-{os.path.basename(self._path) or self._path}"

    def count(self, text: str) -> int:
        return len(self._tok.encode(str(text)).ids)

    def truncate(self, text: str, max_tokens: int) -> str:
        ids = self._tok.encode(str(text)).ids
        n = max(0, int(max_tokens))
        return self._tok.decode(ids[:n]) if len(ids) > n else str(text)


_BACKEND = HeuristicBackend()


def set_backend(backend) -> None:
    """Install an accurate-count backend (must expose .name + .count(text)->int) --
    the provided wiring point for an exact tokenizer once one is provisioned, so the
    heuristic default is an intentional seam, not a forgotten wire. Degrade-safe: a
    None/invalid backend is ignored (the heuristic stays), so calling this can never
    make measurement worse than the offline default."""
    global _BACKEND
    if backend is not None and hasattr(backend, "count") and hasattr(backend, "name"):
        _BACKEND = backend


def make_backend(kind, *, encoding=None, path=None, cache_dir=None):
    """Construct the token-counting backend named ``kind``, or None if it cannot be
    built (optional dependency or asset absent) so the caller degrades-open to the
    heuristic. NEVER raises.

    ``kind`` selects the IMPLEMENTATION via a small backend registry (a dispatch to
    code, like a plugin name -- NOT a content/keyword gate); the actual parameters
    (encoding / path / cache_dir) are SSOT-supplied ([ai].tokenizer_*). server.py
    owns the wiring: it reads the SSOT selector + params and installs the result via
    set_backend()."""
    k = str(kind or "").strip().lower()
    try:
        if k in ("", "heuristic"):
            return HeuristicBackend()
        if k in ("tiktoken", "openai", "bpe"):
            return TiktokenBackend(encoding=encoding, cache_dir=cache_dir)
        if k in ("hf", "huggingface", "tokenizers"):
            return HFTokenizerBackend(path=path)
    except BaseException:  # noqa: BLE001 -- dep/asset missing -> degrade-open (no real tokenizer)
        return None
    return None


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
    the serialized tool surface, measured through the ACTIVE backend.

    The contents + the tool JSON are concatenated and counted ONCE so a real
    tokenizer sees the full text (not a per-message char//N that would bypass it).
    Under the heuristic this is byte-identical to the pre-WS-A5 _fit_context estimate
    `(sum(len(content)) + len(json.dumps(tools))) // 4` -- len(concat)//4 equals
    (sum(len(content)) + len(tools_json))//4 because the parts are joined verbatim."""
    parts = [str((m or {}).get("content") or "")
             for m in (messages or []) if isinstance(m, dict)]
    if tools:
        try:
            parts.append(json.dumps(tools, default=str))
        except (TypeError, ValueError):
            parts.append(str(tools))
    return count_text("".join(parts))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate `text` to at most ~max_tokens (rstripped). Token-budget-aware
    replacement for the bare `text[:N]` char slices; under the heuristic the
    char budget is max_tokens * chars_per_token, so a [:200] slice == 50 tokens."""
    s = str(text or "")
    n = max(0, int(max_tokens))
    if count_text(s) <= n:
        return s
    # A real backend can truncate token-EXACTLY (encode -> slice ids -> decode); the
    # heuristic has no such method, so it falls through to the char-budget slice
    # (n * chars_per_token) -- byte-identical to the prior `[:N]` behaviour.
    tr = getattr(_BACKEND, "truncate", None)
    if callable(tr):
        try:
            out = tr(s, n)
            if isinstance(out, str):
                return out.rstrip()
        except Exception:  # noqa: BLE001 -- degrade to the char-budget slice
            pass
    budget = n * _cpt()
    return s[:budget].rstrip()


def _normalize_usage(usage: Optional[dict]) -> dict:
    if not usage or not isinstance(usage, dict):
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "prompt_tokens_details": {"cached_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 0}
        }
    pt = usage.get("prompt_tokens") or 0
    ct = usage.get("completion_tokens") or 0
    tt = usage.get("total_tokens") or (pt + ct)
    pt_details = usage.get("prompt_tokens_details")
    if not isinstance(pt_details, dict):
        pt_details = {"cached_tokens": 0}
    elif "cached_tokens" not in pt_details:
        pt_details = {**pt_details, "cached_tokens": 0}
    ct_details = usage.get("completion_tokens_details")
    if not isinstance(ct_details, dict):
        ct_details = {"reasoning_tokens": 0}
    elif "reasoning_tokens" not in ct_details:
        ct_details = {**ct_details, "reasoning_tokens": 0}
    return {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": tt,
        "prompt_tokens_details": pt_details,
        "completion_tokens_details": ct_details
    }


def _usage_estimate(prompt: str, completion: str) -> dict:
    """OpenAI `usage` object (Tier-0 conformance; OWUI + clients read it). MiOS is
    a multi-call pipeline, so this reports a ~4-chars/token estimate of the
    CLIENT-VISIBLE exchange (user query + final answer) -- an honest per-turn
    approximation for the client's token display, NOT a faked single-model-call
    number. A future per-stage back-end usage aggregation can replace it."""
    pt = max(1, count_text(prompt))       # WS-A5 tokenizer seam (was //4)
    ct = max(1, count_text(completion))
    return _normalize_usage({"prompt_tokens": pt, "completion_tokens": ct})
