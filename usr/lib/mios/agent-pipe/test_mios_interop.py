#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_interop (WS-11 3-projection: the A2A skill shape). Pure stdlib, no server.py/DB/pytest. Verifies to_a2a_skill renders the A2A AgentCard skill entry (id/name/description/tags), namespaces recipe/skill ids (mios_recipe__/mios_skill__) to match relay routing while verbs keep the bare id, derives tags from kind/section/permission/tier (deduped), uses model_name as the display name, and project_all aligns the function-name vs a2a-id vs description across the three projections.
# AI-related: ./mios_interop.py
# AI-functions: check, main
"""Unit tests for mios_interop (WS-11)."""

import sys

import mios_interop as io

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


VERB = {"section": "Window / app launch", "desc": "launch an app", "permission": "write",
        "tier": "core", "model_name": "launch_windows_app"}


def t_verb():
    s = io.to_a2a_skill("open_app", VERB, "verb")
    check("verb: bare id (no prefix)", s["id"] == "open_app")
    check("verb: display = model_name", s["name"] == "launch_windows_app")
    check("verb: description", s["description"] == "launch an app")
    check("verb: tags include kind + perm + tier", set(["verb", "perm:write", "tier:core"]) <= set(s["tags"]), s["tags"])
    check("verb: section tag normalized", "window___app_launch" in s["tags"], s["tags"])


def t_namespacing():
    check("recipe: prefixed id", io.to_a2a_skill("disk_usage", {"description": "df"}, "recipe")["id"] == "mios_recipe__disk_usage")
    check("skill: prefixed id", io.to_a2a_skill("summarize", {"description": "x"}, "skill")["id"] == "mios_skill__summarize")
    check("recipe: description from 'description' key", io.to_a2a_skill("r", {"description": "d"}, "recipe")["description"] == "d")


def t_tags_dedup_and_fallback():
    s = io.to_a2a_skill("v", {"permission": "read"}, "verb")
    check("tags: no dup verb tag", s["tags"].count("verb") == 1)
    check("name: falls back to id when no model_name", io.to_a2a_skill("bare", {}, "verb")["name"] == "bare")
    check("desc: empty when absent", io.to_a2a_skill("x", {}, "verb")["description"] == "")


def t_project_all():
    p = io.project_all("open_app", VERB, "verb")
    check("project_all: function_name bare", p["function_name"] == "open_app")
    check("project_all: a2a_id matches verb (bare)", p["a2a_id"] == "open_app")
    pr = io.project_all("disk_usage", {"description": "df"}, "recipe")
    check("project_all: recipe function vs a2a id differ by prefix",
          pr["function_name"] == "disk_usage" and pr["a2a_id"] == "mios_recipe__disk_usage")
    check("project_all: shared description", pr["description"] == "df")


def t_desc_cap():
    long = io.to_a2a_skill("x", {"desc": "z" * 999}, "verb")["description"]
    check("desc: capped to 500", len(long) == 500)


def main():
    t_verb()
    t_namespacing()
    t_tags_dedup_and_fallback()
    t_project_all()
    t_desc_cap()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
