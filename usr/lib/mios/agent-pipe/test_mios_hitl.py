# AI-hint: Standalone unit test for mios_hitl to verify deterministic logic for Human-In-The-Loop (HITL) decision gating, scope parsing, and action blocking without requiring a live database or server.
# AI-related: mios_hitl
# AI-functions: _check, t_parse_scope, t_requires_approval, t_gate_outcome, t_block_result, main
"""Standalone unit test for mios_hitl (WS-6 HITL decision helpers).

Pure stdlib + the sibling module only -- no server.py / DB. The live
pending_action I/O + approval endpoints are verified by the operator on
MiOS-DEV; this covers the deterministic decision logic.

Run:  python test_mios_hitl.py
"""

import sys

import mios_hitl as H

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_parse_scope() -> None:
    default = {"powershell_run", "pc_click"}
    _check("scope: blank -> default", H.parse_scope("", default) == default)
    _check("scope: None -> default", H.parse_scope(None, default) == default)
    _check("scope: csv parsed",
           H.parse_scope("a, b ,c", set()) == {"a", "b", "c"},
           str(H.parse_scope("a, b ,c", set())))
    _check("scope: drops empties", H.parse_scope("a,,b,", set()) == {"a", "b"})


def t_requires_approval() -> None:
    scope = {"powershell_run"}
    _check("req: enabled+in-scope", H.requires_approval("powershell_run", True, scope))
    _check("req: disabled -> False",
           not H.requires_approval("powershell_run", False, scope))
    _check("req: out-of-scope -> False",
           not H.requires_approval("web_search", True, scope))
    _check("req: empty scope -> False",
           not H.requires_approval("anything", True, set()))


def t_gate_outcome() -> None:
    _check("gate: log always proceeds", H.gate_outcome("log", False) == "proceed")
    _check("gate: unknown mode proceeds", H.gate_outcome("weird", False) == "proceed")
    _check("gate: gate+approved proceeds", H.gate_outcome("gate", True) == "proceed")
    _check("gate: gate+unapproved blocks", H.gate_outcome("gate", False) == "block")
    _check("gate: case-insensitive", H.gate_outcome("GATE", False) == "block")


def t_block_result() -> None:
    r = H.block_result("powershell_run", {"script": "x"}, "powershell_run\x00{}")
    _check("block: not success", r["success"] is False)
    _check("block: flagged pending", r.get("hitl_pending") is True)
    _check("block: names the tool", "powershell_run" in r["stderr"])
    _check("block: has stable ref", isinstance(r.get("action_ref"), str)
           and len(r["action_ref"]) == 12, str(r.get("action_ref")))
    _check("block: exit_code -1", r["exit_code"] == -1)
    # same action -> same ref (deterministic), different action -> different
    r2 = H.block_result("pc_click", {"x": 1}, "pc_click\x00{}")
    _check("block: ref differs per action", r["action_ref"] != r2["action_ref"])


def t_decide() -> None:
    # The SINGLE reconciled HITL verdict that BOTH gates route through (mios_hitl.decide).
    # Inert: nothing in scope / [ai] off -> proceed (no behaviour when HITL is off).
    _check("decide: nothing in scope -> proceed", H.decide() == H.PROCEED)
    _check("decide: tier scope + ai off -> proceed",
           H.decide(in_tier_scope=True, ai_mode="off") == H.PROCEED)
    # [ai] risk-tier gate, alone.
    _check("decide: ai block + in tier scope -> block",
           H.decide(in_tier_scope=True, ai_mode="block") == H.BLOCK)
    _check("decide: ai block but OUT of tier scope -> proceed",
           H.decide(in_tier_scope=False, ai_mode="block") == H.PROCEED)
    _check("decide: ai audit + in tier scope -> observe",
           H.decide(in_tier_scope=True, ai_mode="audit") == H.OBSERVE)
    # [hitl] verb-scope gate, alone.
    _check("decide: hitl gate + in name scope -> block",
           H.decide(in_name_scope=True, hitl_enable=True, hitl_mode="gate") == H.BLOCK)
    _check("decide: hitl log + in name scope -> observe",
           H.decide(in_name_scope=True, hitl_enable=True, hitl_mode="log") == H.OBSERVE)
    _check("decide: hitl disabled -> proceed",
           H.decide(in_name_scope=True, hitl_enable=False, hitl_mode="gate") == H.PROCEED)
    # STRICTER WINS -- the former two gates can no longer disagree: if EITHER would
    # block, the unified verdict blocks (fail-safe / err toward blocking).
    _check("decide: stricter wins (ai audit + hitl gate) -> block",
           H.decide(in_tier_scope=True, ai_mode="audit",
                    in_name_scope=True, hitl_enable=True, hitl_mode="gate") == H.BLOCK)
    _check("decide: stricter wins (ai block + hitl log) -> block",
           H.decide(in_tier_scope=True, ai_mode="block",
                    in_name_scope=True, hitl_enable=True, hitl_mode="log") == H.BLOCK)
    # An explicit approval (ask-to-run / out-of-band) downgrades a block so the
    # approved action runs.
    _check("decide: approval downgrades block -> observe",
           H.decide(in_tier_scope=True, ai_mode="block", approved=True) == H.OBSERVE)
    # An unknown ai-mode token is treated as inert (off-like), matching the existing
    # `mode not in (audit, block)` convention -- it never fabricates a spurious block.
    _check("decide: unknown ai mode in scope -> proceed",
           H.decide(in_tier_scope=True, ai_mode="bogus") == H.PROCEED)
    # F2/T-033: the Rule-of-Two gate contributes a THIRD posture (a confirmed all-three
    # enforce chain) into the same resolver. Inert by default (byte-identical for the
    # two existing call-sites); BLOCK when set; stricter-wins; approval downgrades.
    _check("decide: ro2_block default inert -> proceed", H.decide() == H.PROCEED)
    _check("decide: ro2_block -> block", H.decide(ro2_block=True) == H.BLOCK)
    _check("decide: ro2_block + approval -> observe",
           H.decide(ro2_block=True, approved=True) == H.OBSERVE)
    _check("decide: ro2_block stricter-wins over ai audit -> block",
           H.decide(ro2_block=True, in_tier_scope=True, ai_mode="audit") == H.BLOCK)
    # F2: the CaMeL quarantine gate contributes a FOURTH posture (a confirmed
    # tainted+privileged enforce bite) into the same resolver. Inert by default
    # (byte-identical for the existing call-sites); BLOCK when set; stricter-wins;
    # approval downgrades -- same fail-safe rule as ro2_block.
    _check("decide: quarantine_block default inert -> proceed", H.decide() == H.PROCEED)
    _check("decide: quarantine_block -> block", H.decide(quarantine_block=True) == H.BLOCK)
    _check("decide: quarantine_block + approval -> observe",
           H.decide(quarantine_block=True, approved=True) == H.OBSERVE)
    _check("decide: quarantine_block stricter-wins over ai audit -> block",
           H.decide(quarantine_block=True, in_tier_scope=True, ai_mode="audit") == H.BLOCK)
    _check("decide: ro2 + quarantine together -> block (both architectural gates compose)",
           H.decide(ro2_block=True, quarantine_block=True) == H.BLOCK)


def main() -> int:
    for t in (t_parse_scope, t_requires_approval, t_gate_outcome, t_block_result,
              t_decide):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
