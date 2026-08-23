# AI-hint: Provides filesystem-safe KV-cache fork primitives for the agent-pipe, enabling branching of shared conversation prefixes into independent c...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_context_kvfork_py.md

from __future__ import annotations

import re
from typing import List, Optional, Tuple

_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]")
_NAME_CAP = 120
_FILE_PREFIX = "mios-kv-"
_FILE_SUFFIX = ".bin"


def kv_filename(conv: object) -> str:
    """A filesystem-safe slot-save filename for one conversation's KV. Mirrors
    server.py `_kv_filename` exactly: sanitise to [A-Za-z0-9_.-], cap at 120
    chars, fall back to 'default' when empty. The file lands under the
    llama.cpp host's --slot-save-path."""
    safe = _SAFE_RE.sub("_", str(conv if conv is not None else "default"))[:_NAME_CAP]
    return f"{_FILE_PREFIX}{safe or 'default'}{_FILE_SUFFIX}"


def conv_token(conv: object) -> str:
    """The sanitised, length-capped conversation token (the variable part of the
    filename). Two conversations collide as a fork source/target iff this token
    matches -- so validate_fork compares on THIS, not on the raw input (e.g.
    'a/b' and 'a_b' both sanitise to 'a_b' and would share one KV file)."""
    return _SAFE_RE.sub("_", str(conv if conv is not None else "default"))[:_NAME_CAP] or "default"


def validate_fork(src_conv: object, dst_conv: object) -> Tuple[bool, str]:
    s_raw = "" if src_conv is None else str(src_conv).strip()
    d_raw = "" if dst_conv is None else str(dst_conv).strip()
    if not s_raw:
        return False, "empty source conversation"
    if not d_raw:
        return False, "empty destination conversation"
    if conv_token(s_raw) == conv_token(d_raw):
        return False, "source and destination resolve to the same KV file"
    return True, "ok"


ForkStep = Tuple[str, str, str]


def plan_fork(src_conv: object, dst_conv: object) -> List[ForkStep]:
    s_tok = conv_token(src_conv)
    d_tok = conv_token(dst_conv)
    return [
        ("restore", s_tok, kv_filename(src_conv)),
        ("save", d_tok, kv_filename(dst_conv)),
    ]


def fork_outcome(restore_ok: bool, save_ok: bool) -> Tuple[bool, str]:
    if not save_ok:
        return False, ("fork failed: could not save child KV file"
                       + ("" if restore_ok else " (parent restore also failed)"))
    if not restore_ok:
        return True, "forked with WARNING: parent restore failed; child seeded from resident slot"
    return True, "forked: child KV seeded from parent prefix"


def parse_bool(val: object, default: bool = False) -> bool:
    """Tolerant truthiness for an SSOT/env flag string (mirrors the agent-pipe's
    own off-set convention). DEFAULT-OFF callers pass default=False."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in {"true", "1", "yes", "on"}:
        return True
    if s in {"false", "0", "no", "off", ""}:
        return False
    return default


def clamp_branches(n: object, hard_cap: int, default: int = 1) -> int:
    """Bound the number of fork children a single request may spawn so a runaway
    swarm can't flood the slot-save-path with files. Returns an int in
    [0, hard_cap]; a non-numeric/None input falls to `default` (then clamped)."""
    try:
        v = int(n)
    except (TypeError, ValueError):
        v = int(default)
    cap = max(0, int(hard_cap))
    if v < 0:
        v = 0
    return min(v, cap)
