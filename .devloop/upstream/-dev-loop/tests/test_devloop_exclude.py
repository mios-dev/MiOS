#!/usr/bin/env python3
"""
Controls for the .git/info/exclude worktree law (SKILL.md 11).

The defect these guard against, observed live 2026-09-19
--------------------------------------------------------
SKILL.md 11 used to instruct excluding `.worktrees/` and `.devloop/`. An AGY manager followed
it literally and excluded `.devloop/` wholesale. Consequences, in increasing order of harm:

  1. A lane's deliverable under `.devloop/findings/` becomes invisible to `git status`.
  2. It cannot be staged without `-f`, so it cannot be merged by the normal host path.
  3. WORST: the host decides vacuity from the lane's worktree diff, so a lane that produced a
     real, cited, gate-passing findings file looks EXACTLY like a lane that did nothing. The
     exclude silently converts delivered work into a `vacuous` verdict -- SKILL.md 7,
     Measuring the Wrong Property, committed by the loop against itself.

`scripts/devloop.sh` and `DevLoop.ps1` always wrote the narrow `.devloop/run-*/` form; only the
prose was wrong. A doc and a script that disagree is a defect even when the code is right,
because a model reads the doc. These tests therefore check BOTH the mechanical behaviour and
doc/code agreement.

Every mechanical case runs in a throwaway git repo under a temp dir -- the real repository is
never mutated, so there is no fixture to leak (SKILL.md 6).

Run: python3 tests/test_devloop_exclude.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARROW = [".worktrees/", ".devloop/run-*/", ".devloop/native/"]
BROAD = [".worktrees/", ".devloop/"]          # the form that caused the incident

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def make_repo(tmp: Path, exclude_lines: list[str]) -> Path:
    """A throwaway repo carrying the given .git/info/exclude."""
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    info = tmp / ".git" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "exclude").write_text("\n".join(exclude_lines) + "\n")
    for rel in (".devloop/findings/X.md", ".devloop/run-20260919/report.json",
                ".devloop/native/report-a.json", ".devloop/lanes.plan.json",
                ".devloop/LEDGER.md", ".worktrees/lane-a/file.txt"):
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    return tmp


def ignored(repo: Path, rel: str) -> bool:
    """True when git would ignore this path. check-ignore exits 0 on a match."""
    return subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", rel]).returncode == 0


def test_narrow_form_is_correct() -> None:
    print("narrow exclude (the fix):")
    with tempfile.TemporaryDirectory() as td:
        r = make_repo(Path(td) / "repo", NARROW)
        # The deliverables and tracked state MUST remain visible.
        check("findings/ is visible", not ignored(r, ".devloop/findings/X.md"),
              "a lane deliverable git cannot see cannot be merged, and reads as vacuous")
        check("lane plan is visible", not ignored(r, ".devloop/lanes.plan.json"))
        check("LEDGER is visible", not ignored(r, ".devloop/LEDGER.md"))
        # The transient run state MUST be hidden.
        check("run-*/ is ignored", ignored(r, ".devloop/run-20260919/report.json"))
        check("native/ is ignored", ignored(r, ".devloop/native/report-a.json"))
        check("worktrees/ is ignored", ignored(r, ".worktrees/lane-a/file.txt"))


def test_broad_form_is_detected() -> None:
    """NEGATIVE CONTROL. Plant the exact broken state and prove these checks catch it.

    Without this, every assertion above could be passing for some unrelated reason and we
    would not know -- a control that cannot fail proves nothing (SKILL.md 6)."""
    print("broad exclude (the incident, planted):")
    with tempfile.TemporaryDirectory() as td:
        r = make_repo(Path(td) / "repo", BROAD)
        check("planted '.devloop/' DOES hide the deliverable",
              ignored(r, ".devloop/findings/X.md"),
              "if this passes as visible, the test cannot detect the incident it exists for")
        check("planted '.devloop/' also hides the tracked lane plan",
              ignored(r, ".devloop/lanes.plan.json"))
        # And the positive assertion must genuinely invert under the planted state.
        check("the narrow-form assertion inverts under the broad form",
              ignored(r, ".devloop/findings/X.md") is not ignored(
                  make_repo(Path(td) / "repo2", NARROW), ".devloop/findings/X.md"),
              "the two forms must differ, or the test is measuring nothing")


def test_doc_and_code_agree() -> None:
    """The incident was a doc/code disagreement, not a code bug. Guard the doc."""
    print("doc / code agreement:")
    skill = (ROOT / "skills" / "dev-loop" / "SKILL.md").read_text()
    check("SKILL.md names the narrow form", ".devloop/run-*/" in skill)
    check("SKILL.md forbids the wholesale form explicitly",
          "Never exclude `.devloop/` wholesale" in skill,
          "a reader must be told not to do it, not merely shown the alternative")

    sh = (ROOT / "skills" / "dev-loop" / "scripts" / "devloop.sh").read_text()
    ps = (ROOT / "skills" / "dev-loop" / "scripts" / "DevLoop.ps1").read_text()
    check("devloop.sh writes the narrow form", '".devloop/run-*/"' in sh)
    check("DevLoop.ps1 writes the narrow form", "'.devloop/run-*/'" in ps)
    # Neither orchestrator may write the bare directory.
    check("devloop.sh never writes bare .devloop/", '".devloop/"' not in sh)
    check("DevLoop.ps1 never writes bare .devloop/", "'.devloop/'" not in ps)


def test_this_repo_is_not_currently_broken() -> None:
    """The live repo's own exclude, read-only. This is the state the incident left behind."""
    print("this repository's current exclude:")
    ex = ROOT / ".git" / "info" / "exclude"
    if not ex.is_file():
        check("exclude file present", False, "expected .git/info/exclude to exist")
        return
    lines = [l.strip() for l in ex.read_text().splitlines()]
    check("no bare '.devloop/' entry", ".devloop/" not in lines,
          "a bare entry here hides every lane deliverable in this checkout")
    check("a real findings file is visible to git",
          not ignored(ROOT, ".devloop/findings/ACP-P6.md")
          if (ROOT / ".devloop" / "findings" / "ACP-P6.md").exists() else True)


def main() -> int:
    for t in (test_narrow_form_is_correct, test_broad_form_is_detected,
              test_doc_and_code_agree, test_this_repo_is_not_currently_broken):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all .devloop exclude controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
