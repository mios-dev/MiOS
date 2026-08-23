# AI-hint: Provides deterministic logic for the WS-6 HITL approval gate, determining if actions should proceed or be blocked/logged based on verb scope and mode.
# AI-functions: parse_scope, requires_approval, gate_outcome, block_result

from __future__ import annotations

import hashlib


def parse_scope(csv, default_set):
    """Resolve the set of verb names that require approval. A blank csv falls
    back to `default_set` (typically the high-privilege verb set); otherwise the
    comma-separated, whitespace-trimmed names."""
    s = (csv or "").strip()
    if not s:
        return set(default_set or ())
    return {p.strip() for p in s.split(",") if p.strip()}


def requires_approval(tool, enabled, scope):
    """True when the HITL gate applies to this verb dispatch."""
    return bool(enabled) and (tool in (scope or set()))


def gate_outcome(mode, approved):
    """'proceed' or 'block'. 'gate' mode blocks unless the action was approved
    out-of-band; every other mode (incl. 'log' and any unknown value) is
    non-blocking and proceeds (after the caller records/emits)."""
    if str(mode).lower() == "gate":
        return "proceed" if approved else "block"
    return "proceed"


def block_result(tool, args, action_hash):
    """The structured dispatch-refusal returned when a gated action is not yet
    approved. Shape matches the broker's dispatch result so the agent tool-loop
    handles it uniformly (it sees a failure + a human-readable next step)."""
    short = hashlib.sha256(str(action_hash).encode("utf-8", "replace")
                           ).hexdigest()[:12]
    return {
        "success": False, "tool": tool, "args": args, "output": "",
        "stderr": (f"hitl_pending: '{tool}' awaiting human approval "
                   f"(ref {short}); approve via POST /v1/hitl/approve"),
        "exit_code": -1, "latency_ms": 0,
        "hitl_pending": True, "action_ref": short,
    }


PROCEED, OBSERVE, BLOCK = "proceed", "observe", "block"
_VERDICT_RANK = {PROCEED: 0, OBSERVE: 1, BLOCK: 2}


def tier_gate_posture(ai_mode):
    """Posture contributed by the [ai] risk-tier gate for an in-tier-scope verb:
    'block' -> BLOCK, 'audit' -> OBSERVE, anything else (off/empty/unknown) ->
    PROCEED. Pure enum dispatch over the SSOT mode value (not a content heuristic)."""
    m = str(ai_mode or "").strip().lower()
    if m == "block":
        return BLOCK
    if m == "audit":
        return OBSERVE
    return PROCEED


def scope_gate_posture(enable, mode):
    """Posture contributed by the [hitl] verb-scope gate for an in-scope verb:
    disabled -> PROCEED, mode 'gate' -> BLOCK, else (log/unknown) -> OBSERVE."""
    if not enable:
        return PROCEED
    return BLOCK if str(mode or "").strip().lower() == "gate" else OBSERVE


def decide(*, in_tier_scope=False, ai_mode="off",
           in_name_scope=False, hitl_enable=False, hitl_mode="log",
           ro2_block=False, quarantine_block=False, approved=False):
    rank = _VERDICT_RANK[PROCEED]
    if in_tier_scope:
        rank = max(rank, _VERDICT_RANK[tier_gate_posture(ai_mode)])
    if in_name_scope:
        rank = max(rank, _VERDICT_RANK[scope_gate_posture(hitl_enable, hitl_mode)])
    if ro2_block:
        rank = max(rank, _VERDICT_RANK[BLOCK])
    if quarantine_block:
        rank = max(rank, _VERDICT_RANK[BLOCK])
    if rank == _VERDICT_RANK[BLOCK]:
        return OBSERVE if approved else BLOCK
    return OBSERVE if rank == _VERDICT_RANK[OBSERVE] else PROCEED
