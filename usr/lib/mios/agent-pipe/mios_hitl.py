# AI-hint: Provides deterministic logic for the WS-6 HITL approval gate, determining if actions should proceed or be blocked/logged based on verb scope and mode.
# AI-functions: parse_scope, requires_approval, gate_outcome, block_result
"""mios_hitl -- pure decision helpers for the WS-6 runtime HITL approval gate.

DB-free + stdlib-only so the scope-resolution and gate-decision logic unit-tests
in isolation (sibling-module pattern, like mios_sched / mios_evict). server.py
owns the pgvector pending_action I/O, the event emission, and the approval
endpoints; this module owns only the deterministic, testable decisions.

Modes:
  "log"  (default) -- NON-BLOCKING: record + emit an observability event, then
                      proceed. The autonomous swarm is never deadlocked.
  "gate"           -- BLOCKING: a scoped verb is refused (block_result) and a
                      pending_action row is written until approved out-of-band;
                      the agent's later retry of the same action then passes.
"""

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


# ── Unified HITL verdict -- the SINGLE reconciliation of BOTH configured gates ──
# MiOS exposes two HITL controls that historically decided INDEPENDENTLY and could
# disagree: the [ai] RISK-TIER gate (mode off|audit|block, applied to verbs whose
# permission tier is at/above [ai].hitl_threshold) and the [hitl] VERB-SCOPE gate
# (enable + mode log|gate, applied to the gated verb set). They are complementary
# COVERAGE LAYERS, not duplicates -- but a single dispatch must resolve them to ONE
# coherent outcome, or a turn can be "HITL-enabled but not blocked". `decide` is that
# single resolver, which BOTH gate call-sites route their decision through (so the two
# can no longer diverge): each gate contributes a posture ONLY within its own scope,
# the verdict is the STRICTER of the two (a safety gate errs toward blocking), and an
# approval (ask-to-run this turn, or an out-of-band /v1/hitl/approve) downgrades a
# block so the approved action runs.
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
           ro2_block=False, approved=False):
    """THE single HITL verdict, reconciling the [ai] risk-tier gate, the [hitl]
    verb-scope gate AND the Rule-of-Two architectural gate. Each gate is evaluated
    ONLY within its own scope; the result is the STRICTER of their postures
    (proceed < observe < block) so that if ANY gate would block this verb, it blocks
    (fail-safe -- the gates can never disagree on the blocking outcome). The
    Rule-of-Two gate contributes a BLOCK posture (`ro2_block=True`) when a dispatch
    holds all three dangerous properties under enforce mode -- the deterministic
    kill-chain refusal (mios_ruleof2). `approved` downgrades a BLOCK to OBSERVE so an
    explicitly-approved action runs. Returns PROCEED / OBSERVE / BLOCK. Pure + total:
    it never raises (call-sites stay degrade-open on their own I/O, but the DECISION
    itself errs toward blocking, never toward a silent execution). `ro2_block` defaults
    False -> inert for the two existing call-sites (byte-identical verdict)."""
    rank = _VERDICT_RANK[PROCEED]
    if in_tier_scope:
        rank = max(rank, _VERDICT_RANK[tier_gate_posture(ai_mode)])
    if in_name_scope:
        rank = max(rank, _VERDICT_RANK[scope_gate_posture(hitl_enable, hitl_mode)])
    if ro2_block:
        # A confirmed all-three Rule-of-Two chain (enforce mode) errs toward blocking.
        rank = max(rank, _VERDICT_RANK[BLOCK])
    if rank == _VERDICT_RANK[BLOCK]:
        return OBSERVE if approved else BLOCK
    return OBSERVE if rank == _VERDICT_RANK[OBSERVE] else PROCEED
