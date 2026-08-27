# AI-hint: WS-A5 tokenizer seam for the agent-pipe. Centralizes the scattered "len // 4" token estimate behind ONE pluggable interface -- count_text...
# AI-doc: usr/share/doc/mios/manual/context.md

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
