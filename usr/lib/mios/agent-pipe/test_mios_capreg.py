#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_capreg (WS-2 unified RBAC-filtered capability manifest). Pure stdlib, no server.py/DB/pytest. Verifies tier_rank ordering + fail-closed (unknown tier ranks beyond highest), allowed() admission (cap<=ceiling; unknown cap excluded; unknown ceiling admits nothing), recipe platform detection, the unified verb+recipe projection (RBAC filter by ceiling, platform filter, kind/tier tagging, deterministic sort), and the summary counts.
# AI-related: ./mios_capreg.py
# AI-functions: check, main
"""Unit tests for mios_capreg (WS-2 capability registry projection)."""

import sys

import mios_capreg as cr

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# Verbs carry their RBAC tier in `permission` (read|write|interactive); the `tier`
# key on a real verb is COMMONNESS (common/rare/core) and must be IGNORED here.
VERBS = {
    "list_windows": {"permission": "read", "tier": "common", "description": "list windows"},
    "open_app": {"permission": "write", "tier": "common", "description": "launch an app"},
    "run_powershell": {"permission": "interactive", "tier": "rare", "description": "run pwsh"},
    "weird": {"permission": "superuser", "description": "unknown tier verb"},
}
RECIPES = {
    "open-folder": {"permission": "read", "linux": "xdg-open {path}", "windows": "explorer {path}"},
    "reboot": {"permission": "interactive", "windows": "shutdown /r"},
    "run-bash": {"permission": "read", "linux": "bash -lc {cmd}"},
}


def t_tier_rank():
    check("rank: read<write<interactive", cr.tier_rank("read") < cr.tier_rank("write") < cr.tier_rank("interactive"))
    check("rank: unknown beyond highest", cr.tier_rank("superuser") == 3 and cr.tier_rank("") == 3)
    check("rank: case-insensitive", cr.tier_rank("READ") == cr.tier_rank("read"))


def t_allowed():
    check("allowed: read under interactive", cr.allowed("read", "interactive"))
    check("allowed: write under write", cr.allowed("write", "write"))
    check("allowed: write NOT under read", cr.allowed("write", "read") is False)
    check("allowed: unknown cap excluded even at top", cr.allowed("superuser", "interactive") is False)
    check("allowed: unknown ceiling admits nothing", cr.allowed("read", "bogus") is False)


def t_platforms():
    check("platforms: both", cr.recipe_platforms(RECIPES["open-folder"]) == ["linux", "windows"])
    check("platforms: windows-only", cr.recipe_platforms(RECIPES["reboot"]) == ["windows"])
    check("platforms: none", cr.recipe_platforms({"permission": "read"}) == [])


def t_build():
    # ceiling = write: read+write verbs, NOT interactive, NOT unknown-tier; read recipes
    m = cr.build_capability_manifest(VERBS, RECIPES, ceiling="write")
    names = {(c["name"], c["kind"]) for c in m}
    check("build: includes read+write verbs", ("list_windows", "verb") in names and ("open_app", "verb") in names)
    check("build: uses `permission` not commonness `tier`",
          next(c["tier"] for c in m if c["name"] == "list_windows") == "read")
    check("build: excludes interactive verb under write", ("run_powershell", "verb") not in names)
    check("build: excludes unknown-tier verb (fail-closed)", ("weird", "verb") not in names)
    check("build: includes read recipes", ("open-folder", "recipe") in names and ("run-bash", "recipe") in names)
    check("build: excludes interactive recipe under write", ("reboot", "recipe") not in names)
    check("build: deterministic sort (kind then name)",
          [ (c["kind"], c["name"]) for c in m ] == sorted((c["kind"], c["name"]) for c in m))
    # ceiling = interactive: everything known-tier; platform=linux drops windows-only reboot
    mi = cr.build_capability_manifest(VERBS, RECIPES, ceiling="interactive", platform="linux")
    inames = {(c["name"], c["kind"]) for c in mi}
    check("build: interactive admits run_powershell", ("run_powershell", "verb") in inames)
    check("build: still excludes unknown-tier verb", ("weird", "verb") not in inames)
    check("build: platform=linux drops windows-only reboot", ("reboot", "recipe") not in inames)
    check("build: platform=linux keeps cross-platform open-folder", ("open-folder", "recipe") in inames)
    # ceiling = read: only read caps
    mr = cr.build_capability_manifest(VERBS, RECIPES, ceiling="read")
    check("build: read ceiling -> only read tier", all(c["tier"] == "read" for c in mr))
    # unknown ceiling -> empty
    check("build: unknown ceiling -> empty", cr.build_capability_manifest(VERBS, RECIPES, ceiling="root") == [])


def t_summary():
    m = cr.build_capability_manifest(VERBS, RECIPES, ceiling="interactive")
    s = cr.manifest_summary(m)
    check("summary: total matches", s["total"] == len(m))
    check("summary: by_kind has verb+recipe", "verb" in s["by_kind"] and "recipe" in s["by_kind"])
    check("summary: empty safe", cr.manifest_summary([]) == {"total": 0, "by_kind": {}, "by_tier": {}})


def t_load_and_diff():
    import os
    import tempfile
    toml_text = (
        '[recipes.open-folder]\n'
        'description = "open"\n'
        'permission = "read"\n'
        'linux = "xdg-open {path}"\n'
        'windows = "explorer {path}"\n\n'
        '[recipes.reboot]\n'
        'permission = "interactive"\n'
        'windows = "shutdown /r"\n'
    )
    fd, p = tempfile.mkstemp(suffix=".toml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(toml_text)
        recs = cr.load_recipes_from_toml(p)
        check("load: parses recipes", set(recs) == {"open-folder", "reboot"})
        check("load: missing file -> {}", cr.load_recipes_from_toml("/no/such.toml") == {})
        man = cr.project_from_toml(p, ceiling="interactive", verbs={"v1": {"tier": "read", "description": "x"}})
        names = {(c["name"], c["kind"]) for c in man}
        check("project: merges verbs + recipes", ("v1", "verb") in names and ("open-folder", "recipe") in names)
    finally:
        os.unlink(p)
    # diff
    base = [{"kind": "verb", "name": "a", "tier": "read"},
            {"kind": "recipe", "name": "r", "tier": "read", "platforms": ["linux"]}]
    check("diff: identical -> []", cr.diff_capabilities(base, base) == [])
    added = base + [{"kind": "verb", "name": "b", "tier": "write"}]
    check("diff: added detected", any("+ verb:b" in d for d in cr.diff_capabilities(added, base)))
    check("diff: removed detected", any("- verb:b" in d for d in cr.diff_capabilities(base, added)))
    changed = [{"kind": "verb", "name": "a", "tier": "write"},
               {"kind": "recipe", "name": "r", "tier": "read", "platforms": ["linux"]}]
    check("diff: tier change detected", any("~ verb:a tier" in d for d in cr.diff_capabilities(changed, base)))


def main():
    t_tier_rank()
    t_allowed()
    t_platforms()
    t_build()
    t_summary()
    t_load_and_diff()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
