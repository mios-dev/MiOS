# AI-hint: !/usr/bin/env python3 Standalone assert-script unit test for mios_manifest (WS-A1 verb-catalog manifest projection). Pure stdlib, no server.py/DB/pytest.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_ai_manifest_py.md
"""Unit tests for mios_manifest (WS-A1)."""

import json
import sys

import mios_manifest as man

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


CAT = {
    "open_app": {"section": "Win", "desc": "launch", "tier": "core",
                 "permission": "write", "model_name": "launch_windows_app",
                 "conflict_group": "desktop_ui"},
    "list_windows": {"section": "Win", "desc": "list", "permission": "read"},
    "web_search": {"section": "Web", "desc": "search", "permission": "read",
                   "parallel_limit": 3},
}


def t_project():
    mani = man.project_verb_catalog(CAT)
    check("project: registry_kind = verb-catalog", mani["registry_kind"] == "verb-catalog")
    check("project: NOT hermes-build-tools", mani["registry_kind"] != "hermes-build-tools")
    check("project: generated flag", mani["generated"] is True)
    check("project: count matches", mani["count"] == 3, f"{mani['count']}")
    names = [e["name"] for e in mani["data"]]
    check("project: sorted by name (deterministic order)", names == sorted(names), f"{names}")
    om = next(e for e in mani["data"] if e["name"] == "open_app")
    check("project: carries model_name", om["model_name"] == "launch_windows_app")
    check("project: carries WS-A7 conflict_group", om.get("conflict_group") == "desktop_ui")
    ws = next(e for e in mani["data"] if e["name"] == "web_search")
    check("project: carries WS-A7 parallel_limit", ws.get("parallel_limit") == 3)
    check("project: read-default permission", next(
        e for e in mani["data"] if e["name"] == "list_windows")["permission"] == "read")


def t_deterministic():
    a = json.dumps(man.project_verb_catalog(CAT), sort_keys=True)
    b = json.dumps(man.project_verb_catalog(dict(reversed(list(CAT.items())))), sort_keys=True)
    check("deterministic: insertion-order-independent", a == b)


def t_diff():
    base = man.project_verb_catalog(CAT)
    check("diff: identical -> no diffs", man.diff_manifest(base, base) == [])
    cat2 = dict(CAT); cat2["new_verb"] = {"section": "X", "desc": "n", "permission": "read"}
    d = man.diff_manifest(man.project_verb_catalog(cat2), base)
    check("diff: detects ADDED verb", any("new_verb" in x and x.startswith("+") for x in d), f"{d}")
    d2 = man.diff_manifest(base, man.project_verb_catalog(cat2))
    check("diff: detects REMOVED verb", any("new_verb" in x and x.startswith("-") for x in d2))
    cat3 = dict(CAT); cat3["open_app"] = {**CAT["open_app"], "permission": "interactive"}
    d3 = man.diff_manifest(man.project_verb_catalog(cat3), base)
    check("diff: detects CHANGED verb", any("open_app" in x and x.startswith("~") for x in d3), f"{d3}")
    bad = {**base, "registry_kind": "hermes-build-tools"}
    check("diff: flags wrong registry_kind",
          any("registry_kind" in x for x in man.diff_manifest(base, bad)))
    check("diff: missing committed -> flagged", man.diff_manifest(base, None) != [])


def main():
    t_project()
    t_deterministic()
    t_diff()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
