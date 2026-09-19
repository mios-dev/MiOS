#!/usr/bin/env python3
"""
Controls for the planted-violation naming convention (SKILL.md 6).

A negative control proves a gate can fail only if its `negative_expect` names what was actually
planted. Two ways that goes wrong, both found in this repo's own example plans:

  SHARED SENTINEL   `nope\\.md` was the expect for lane `docs` in one plan AND lane `cc-docs` in
                    another. A token that is not unique to a lane means either lane's output can
                    satisfy the other's gate.

  SELF-CERTIFYING   `planted-vacuous|VACUOUS` alternated the plant with `VACUOUS`, which is part
                    of the fixture's own filename `tests/checks/VACUOUS.md` -- printed by pytest
                    whether or not the plant landed. The control passed without the plant. That
                    is SKILL.md 7's Self-Certifying Predicate, shipped by the skill that defines
                    the taxonomy.

The convention: prefer the tool's OWN error for a real code mutation (organic). Where the
deliverable is a document with no natural mutation, plant `DEVLOOP-PLANTED-<LANE_ID>`.

Run: python3 tests/test_planted_naming.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "DEVLOOP-PLANTED-"
PLAN_GLOBS = ("skills/dev-loop/assets/lanes*.json", ".devloop/lanes*.json")

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def expected_sentinel(lane_id: str) -> str:
    return PREFIX + re.sub(r"[^A-Za-z0-9]+", "-", lane_id).strip("-").upper()


def plans() -> list[tuple[Path, dict]]:
    out = []
    for g in PLAN_GLOBS:
        for p in sorted(ROOT.glob(g)):
            if p.name == "lane-schema.json":
                continue
            try:
                out.append((p, json.loads(p.read_text())))
            except json.JSONDecodeError:
                check(f"{p.relative_to(ROOT)} parses", False)
    return out


def test_plans_found() -> None:
    """Empty-Set Pass guard: a suite that found no plans would pass every assertion below."""
    print("corpus:")
    found = plans()
    check("lane plans were found", len(found) >= 2, f"found {len(found)}")
    lanes = sum(len(d.get("lanes", [])) for _, d in found)
    check("lanes were found", lanes >= 4, f"found {lanes}")
    sents = [l for _, d in found for l in d.get("lanes", [])
             if PREFIX in str(l.get("negative_expect", ""))]
    check("at least one sentinel lane exists to judge", len(sents) >= 2, f"found {len(sents)}")


def test_sentinels_conform() -> None:
    print("sentinel form:")
    for p, doc in plans():
        rel = p.relative_to(ROOT)
        for lane in doc.get("lanes", []):
            ne = str(lane.get("negative_expect", ""))
            if PREFIX not in ne:
                continue  # organic expect — judged by test_organic_expects_are_left_alone
            lid = lane.get("id", "?")
            want = expected_sentinel(lid)
            check(f"{rel}:{lid} sentinel matches its lane id", ne == want,
                  f"expect={ne!r} want={want!r}")
            cmd = str(lane.get("negative_control_cmd", ""))
            check(f"{rel}:{lid} sentinel is actually planted by the command", want in cmd,
                  "an expect the command never plants can never match — the control is vacuous")
            check(f"{rel}:{lid} sentinel is the WHOLE expect (no alternation)",
                  "|" not in ne,
                  "alternating with text the tool prints anyway lets the control pass without the plant")


def test_sentinels_are_unique() -> None:
    print("sentinel uniqueness:")
    seen: dict[str, list[str]] = {}
    for p, doc in plans():
        for lane in doc.get("lanes", []):
            ne = str(lane.get("negative_expect", ""))
            if PREFIX in ne:
                seen.setdefault(ne, []).append(f"{p.relative_to(ROOT)}:{lane.get('id')}")
    for tok, owners in sorted(seen.items()):
        check(f"{tok} is unique", len(owners) == 1, f"shared by {owners}")


def test_sentinels_do_not_exist_in_tree() -> None:
    """A sentinel naming something real is self-certifying: the gate matches without the plant."""
    print("sentinels name nothing real:")
    toks = {str(l.get("negative_expect")) for _, d in plans() for l in d.get("lanes", [])
            if PREFIX in str(l.get("negative_expect", ""))}
    for tok in sorted(toks):
        # Search tracked files only; the plan that declares it is the sole legitimate mention.
        cp = subprocess.run(["git", "-C", str(ROOT), "grep", "-l", "--fixed-strings", tok],
                            capture_output=True, text=True)
        hits = [h for h in cp.stdout.split() if h]
        non_plan = [h for h in hits if not Path(h).name.startswith("lanes")
                    and Path(h).name not in ("SKILL.md", "lane-schema.json")
                    and not h.startswith("tests/")]
        check(f"{tok} does not name an existing tracked file/content", not non_plan,
              f"appears in {non_plan} — the control could match without the plant")


def test_organic_expects_are_left_alone() -> None:
    """The convention must not have bulldozed the BETTER kind of expect."""
    print("organic expects preserved:")
    organic = [str(l.get("negative_expect")) for _, d in plans() for l in d.get("lanes", [])
               if l.get("negative_expect") and PREFIX not in str(l.get("negative_expect"))]
    check("organic expects still present", len(organic) >= 3,
          f"found {len(organic)} — standardising must not replace real tool errors with sentinels")
    check("an organic expect names a real tool diagnostic",
          any("F401" in o or "FAILED" in o for o in organic), f"organic={organic}")


def test_convention_is_documented() -> None:
    print("documented where authors read it:")
    skill = (ROOT / "skills" / "dev-loop" / "SKILL.md").read_text()
    check("SKILL.md defines the sentinel", "DEVLOOP-PLANTED-<LANE_ID>" in skill)
    check("SKILL.md warns about the self-certifying alternation",
          "planted-vacuous|VACUOUS" in skill)
    schema = (ROOT / "skills" / "dev-loop" / "assets" / "lane-schema.json").read_text()
    check("lane-schema documents the sentinel", "DEVLOOP-PLANTED-<LANE_ID>" in schema)


def main() -> int:
    for t in (test_plans_found, test_sentinels_conform, test_sentinels_are_unique,
              test_sentinels_do_not_exist_in_tree, test_organic_expects_are_left_alone,
              test_convention_is_documented):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all planted-naming controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
