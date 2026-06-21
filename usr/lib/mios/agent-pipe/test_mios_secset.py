#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_secset (WS-A14 SSOT-derived security sets). Pure stdlib, no server.py/DB/pytest. Verifies high_privilege_set = curated base UNION SSOT additions (curated is the never-droppable floor; SSOT only adds), taint_verb_set merges built-in external-fetch verbs with SSOT taint_verbs, normalization (strip/drop-empty), and provenance() origin accounting (ssot_only / curated_only).
# AI-related: ./mios_secset.py
# AI-functions: check, main
"""Unit tests for mios_secset (WS-A14)."""

import sys

import mios_secset as ss

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_high_priv():
    curated = ["powershell_run", "pc_type", "pkg"]
    ssot = ["custom_verb", "pc_type"]   # adds custom_verb; pc_type overlaps
    s = ss.high_privilege_set(curated, ssot)
    check("highpriv: union of curated+ssot", s == {"powershell_run", "pc_type", "pkg", "custom_verb"}, f"{s}")
    check("highpriv: curated floor kept even if SSOT empty", ss.high_privilege_set(curated, []) == set(curated))
    check("highpriv: SSOT can ADD", "custom_verb" in s)
    check("highpriv: curated never dropped", {"powershell_run", "pkg"} <= s)
    check("highpriv: normalizes (strip + drop empty)",
          ss.high_privilege_set(["  a ", "", None], ["b"]) == {"a", "b"})


def t_taint():
    builtin = ("web_search", "web_extract")
    s = ss.taint_verb_set(builtin, ["my_scraper", "web_search"])
    check("taint: union builtin+ssot", s == {"web_search", "web_extract", "my_scraper"}, f"{s}")
    check("taint: empty ssot keeps builtin", ss.taint_verb_set(builtin, None) == set(builtin))


def t_provenance():
    p = ss.provenance(["a", "b", "c"], ["c", "d"])
    check("prov: total union", p["total"] == 4, f"{p}")
    check("prov: curated count", p["curated"] == 3)
    check("prov: ssot count", p["ssot"] == 2)
    check("prov: ssot_only", p["ssot_only"] == ["d"])
    check("prov: curated_only", p["curated_only"] == ["a", "b"])
    check("prov: has source label", "source" in p and "firewall_high_privilege_verbs" in p["source"])


def main():
    t_high_priv()
    t_taint()
    t_provenance()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
