#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_registry (WS-A17 versioned package + registry projection). Pure stdlib, no server.py/DB/pytest. Verifies build_package produces a versioned self-describing descriptor, build_registry is deterministic (sorted by kind,name), the index path layout (ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml), the count, and verify_registry detects added/removed packages + a wrong schema for the drift gate.
# AI-related: ./mios_registry.py, ./mios_manifest.py
# AI-functions: check, main
"""Unit tests for mios_registry (WS-A17)."""

import json
import sys

import mios_registry as reg

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


ITEMS = [
    ("open_app", "verb", {"desc": "launch", "section": "Win", "permission": "write", "tier": "core"}),
    ("hermes", "agent", {"description": "gateway agent"}),
    ("disk_usage", "recipe", {"description": "df", "permission": "read"}),
]


def t_package():
    p = reg.build_package("open_app", "verb", ITEMS[0][2], author="mios", version="1.2.0")
    check("package: schema tag", p["schema"] == "mios-pkg/v1")
    check("package: author/name/version", p["author"] == "mios" and p["name"] == "open_app" and p["version"] == "1.2.0")
    check("package: kind", p["kind"] == "verb")
    check("package: self-describing manifest", p["manifest"]["description"] == "launch" and p["manifest"]["permission"] == "write")
    # recipe uses 'description' not 'desc' -> still captured.
    pr = reg.build_package("disk_usage", "recipe", ITEMS[2][2], author="mios", version="1.0.0")
    check("package: recipe description captured", pr["manifest"]["description"] == "df")


def t_registry():
    r = reg.build_registry(ITEMS, author="mios", version="2.0.0")
    idx = r["index"]
    check("registry: schema tag", idx["schema"] == "mios-registry/v1")
    check("registry: count matches", idx["count"] == 3 and len(r["packages"]) == 3)
    # Deterministic order: sorted by (kind, name) -> agent, recipe, verb.
    kinds = [e["kind"] for e in idx["packages"]]
    check("registry: deterministic kind order", kinds == ["agent", "recipe", "verb"], f"{kinds}")
    oa = next(e for e in idx["packages"] if e["name"] == "open_app")
    check("registry: path layout", oa["path"] == "ai/v1/packages/mios/open_app/2.0.0/mios-pkg.toml", oa["path"])


def t_deterministic():
    a = json.dumps(reg.build_registry(ITEMS, author="m", version="1")["index"], sort_keys=True)
    b = json.dumps(reg.build_registry(list(reversed(ITEMS)), author="m", version="1")["index"], sort_keys=True)
    check("registry: order-independent (deterministic)", a == b)


def t_verify():
    base = reg.build_registry(ITEMS, author="mios", version="1")["index"]
    check("verify: identical -> no diffs", reg.verify_registry(base, base) == [])
    more = reg.build_registry(ITEMS + [("web_search", "verb", {"desc": "s"})], author="mios", version="1")["index"]
    check("verify: detects ADDED", any(x.startswith("+") for x in reg.verify_registry(more, base)))
    check("verify: detects REMOVED", any(x.startswith("-") for x in reg.verify_registry(base, more)))
    bad = {**base, "schema": "wrong"}
    check("verify: flags wrong schema", any("schema" in x for x in reg.verify_registry(base, bad)))
    check("verify: missing committed -> flagged", reg.verify_registry(base, None) != [])


def main():
    t_package()
    t_registry()
    t_deterministic()
    t_verify()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
