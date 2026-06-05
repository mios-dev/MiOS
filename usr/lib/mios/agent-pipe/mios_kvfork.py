"""mios_kvfork -- KV-cache FORK primitives for the MiOS agent-pipe (WS-8, the
AIOS context-manager "fork" capability that extends the existing demand-paging
KV layer, server.py `_kv_paging` / `_kv_slot_action`).

Purpose
=======
The llama.cpp /slots layer already lets us SAVE a conversation's KV to disk and
RESTORE it (`_kv_slot_action`). A SWARM that wants to branch several parallel
cognitive paths from a SHARED PREFIX (e.g. "from this researched context, spawn
3 sub-agents that each take a different angle") needs a FORK: copy a parent
conversation's saved KV file to a NEW child-conversation filename so each branch
pages in the same prefix independently and diverges without clobbering the
parent. That is the RadixAttention prefix-sharing workload, done on the cheap
disk-file prototype (no vLLM/LMCache yet).

Why this lives here (pure, DB-free, sibling module)
---------------------------------------------------
Pure stdlib (re / typing) so it unit-tests in isolation, in the
mios_sched / mios_evict / mios_hitl style. This module owns ONLY the reusable
mechanism: the filesystem-safe filename derivation (kept byte-identical to
server.py `_kv_filename` so a forked child's file is the one `_kv_paging` later
restores), the fork-request validation, and the SLOT-ACTION PLAN. server.py owns
the wiring (the SSOT flag, the async `kv_fork()` that drives `_kv_slot_action`
against a live llama.cpp endpoint, the contextvar, the /v1 observability).

llama.cpp has NO native "copy slot file" verb. A fork is therefore expressed as
a two-step plan over the EXISTING save/restore primitive:

    1. restore  <- parent file   (page the shared prefix INTO the slot)
    2. save     -> child file     (write the slot back out under the new name)

After step 2 the child conversation owns an independent KV file seeded with the
parent's prefix; subsequent turns on the child page IN that file and diverge.
The plan is data only -- the caller (server.py) runs it under the per-slot lock
so a concurrent conversation can't swap the slot between the two steps.

Everything degrades open: a malformed request returns a non-fatal reason and the
caller proceeds without forking (the child simply starts from a cold/empty KV,
exactly as it would today).
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

# Kept byte-identical to server.py `_kv_filename` so a child file produced here
# is the SAME path `_kv_paging` restores when the child conversation next runs.
# (If server.py's scheme ever changes, change it in BOTH places.)
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
    """Validate a fork request. Returns (ok, reason). DEGRADE-OPEN contract: the
    caller treats ok=False as 'skip the fork, proceed cold' -- never an error.

    Rejects:
      * an empty/None source or destination (nothing to fork / nowhere to put it)
      * a source and destination that sanitise to the SAME KV file (a self-fork
        is a no-op that would needlessly rewrite the parent's own file).
    """
    s_raw = "" if src_conv is None else str(src_conv).strip()
    d_raw = "" if dst_conv is None else str(dst_conv).strip()
    if not s_raw:
        return False, "empty source conversation"
    if not d_raw:
        return False, "empty destination conversation"
    if conv_token(s_raw) == conv_token(d_raw):
        return False, "source and destination resolve to the same KV file"
    return True, "ok"


# One step of a fork plan: (action, conversation, filename). `action` is the
# llama.cpp /slots verb the caller passes straight to `_kv_slot_action`.
ForkStep = Tuple[str, str, str]


def plan_fork(src_conv: object, dst_conv: object) -> List[ForkStep]:
    """Build the ordered slot-action plan that forks `src_conv`'s saved KV into a
    new file for `dst_conv`. Two steps over the existing save/restore primitive:

        ("restore", <src token>, <src file>)   # page the shared prefix IN
        ("save",    <dst token>, <dst file>)    # write the slot OUT under dst

    PURE: returns data only; the caller runs the steps (under the per-slot lock)
    via `_kv_slot_action`. Order matters and must be preserved. Call only after
    validate_fork() returns ok -- this does not re-validate (it sanitises, so a
    bad input yields a 'default'/'default' no-op plan rather than raising)."""
    s_tok = conv_token(src_conv)
    d_tok = conv_token(dst_conv)
    return [
        ("restore", s_tok, kv_filename(src_conv)),
        ("save", d_tok, kv_filename(dst_conv)),
    ]


def fork_outcome(restore_ok: bool, save_ok: bool) -> Tuple[bool, str]:
    """Collapse the two step results into one fork verdict. A fork SUCCEEDS only
    if the SAVE landed (the child file now exists). A failed RESTORE is tolerated
    but noted: the child is then seeded from whatever was already resident in the
    slot rather than the intended parent prefix -- degraded, not fatal.

    Returns (forked, reason). `forked=False` => the caller should let the child
    start cold (its next turn pages in nothing, as today)."""
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
