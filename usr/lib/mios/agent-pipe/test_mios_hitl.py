"""Standalone unit test for mios_hitl (WS-6 HITL decision helpers).

Pure stdlib + the sibling module only -- no server.py / SurrealDB. The live
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


def main() -> int:
    for t in (t_parse_scope, t_requires_approval, t_gate_outcome, t_block_result):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
