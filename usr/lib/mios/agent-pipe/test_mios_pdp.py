#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_pdp (WS-A9 PDP capability gate).
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_pdp (WS-A9)."""

import sys

import mios_pdp as pdp

TIERS = ["read", "write", "interactive"]
_fails = 0

def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))

def t_rank():
    check("rank: read=0", pdp.permission_rank("read", TIERS) == 0)
    check("rank: write=1", pdp.permission_rank("write", TIERS) == 1)
    check("rank: interactive=2", pdp.permission_rank("interactive", TIERS) == 2)
    check("rank: unknown tier ranks ABOVE top (fail-closed)",
          pdp.permission_rank("nuke", TIERS) == 3)
    check("rank: case/space-insensitive", pdp.permission_rank("  WRITE ", TIERS) == 1)

def t_ceiling():
    check("ceiling: empty -> None (no ceiling)", pdp.resolve_ceiling("", TIERS) is None)
    check("ceiling: absent -> None", pdp.resolve_ceiling(None, TIERS) is None)
    check("ceiling: known tier -> its rank", pdp.resolve_ceiling("write", TIERS) == 1)
    check("ceiling: UNKNOWN tier -> 0 (FAIL CLOSED, not None)",
          pdp.resolve_ceiling("supervisor", TIERS) == 0)
    check("ceiling: typo'd tier -> 0 (fail closed)", pdp.resolve_ceiling("writ", TIERS) == 0)

def _d(name, *, in_catalog=True, verb_perm="read", denied=(), allowed=(), ceiling=None):
    return pdp.decide(name, in_catalog=in_catalog, verb_perm=verb_perm,
                      denied=denied, allowed=allowed,
                      ceiling_rank=ceiling, tiers=TIERS)

def t_decide():
    check("decide: empty policy allows", _d("open_app").allow)
    check("decide: denied verb -> deny", not _d("open_app", denied=["open_app"]).allow)
    check("decide: denied rule named", _d("x", denied=["x"]).rule == "denied_verbs")
    check("decide: allowed-list excludes others",
          not _d("open_app", allowed=["web_search"]).allow)
    check("decide: allowed-list includes self",
          _d("web_search", allowed=["web_search"]).allow)
    ceil_read = pdp.resolve_ceiling("read", TIERS)
    check("decide: ceiling read drops write verb",
          not _d("pc_type", verb_perm="write", ceiling=ceil_read).allow)
    check("decide: ceiling read keeps read verb",
          _d("list_windows", verb_perm="read", ceiling=ceil_read).allow)
    check("decide: ceiling rule named",
          _d("pc_type", verb_perm="write", ceiling=ceil_read).rule == "max_permission")
    bad_ceil = pdp.resolve_ceiling("typo", TIERS)
    check("decide: fail-closed ceiling drops write verb",
          not _d("pc_type", verb_perm="write", ceiling=bad_ceil).allow)
    check("decide: fail-closed ceiling keeps read verb",
          _d("list_windows", verb_perm="read", ceiling=bad_ceil).allow)

def t_non_verb():
    check("non-verb: passes allowed-list (not a verb)",
          _d("some_mcp_tool", in_catalog=False, allowed=["web_search"]).allow)
    check("non-verb: passes ceiling (not a verb)",
          _d("some_skill", in_catalog=False, verb_perm="write",
             ceiling=pdp.resolve_ceiling("read", TIERS)).allow)
    check("non-verb: denied STILL applies",
          not _d("evil_tool", in_catalog=False, denied=["evil_tool"]).allow)
    check("non-verb: rule = non_verb when allowed",
          _d("t", in_catalog=False).rule == "non_verb")

def main() -> int:
    t_rank()
    t_ceiling()
    t_decide()
    t_non_verb()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0

if __name__ == "__main__":
    sys.exit(main())
