# AI-hint: Provides deterministic logic for the WS-6 HITL approval gate, determining if actions should proceed or be blocked/logged based on verb scope and mode.
# AI-functions: parse_scope, requires_approval, gate_outcome, block_result
"""mios_hitl -- pure decision helpers for the WS-6 runtime HITL approval gate.

DB-free + stdlib-only so the scope-resolution and gate-decision logic unit-tests
in isolation (sibling-module pattern, like mios_sched / mios_evict). server.py
owns the SurrealDB pending_action I/O, the event emission, and the approval
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
