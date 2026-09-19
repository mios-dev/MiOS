#!/usr/bin/env python3
"""
Control for the host-side sentinel guard in adapters.py's merge gate.

The hole this closes, found by a live run
-----------------------------------------
A sentinel negative control works by citing a path that does NOT exist, so the checker fails and
names it. But the lane can SEE its own negative_control_cmd -- adapters.py puts it in the lane
prompt -- which means the lane knows the exact path the control expects to be missing. A lane
that creates that path makes the citation resolve, the control PASS, and the gate vacuous.

This is not hypothetical. On 2026-09-19 a MiOS lane, told to construct a violation for the gate
it was measuring, created `automation/DEVLOOP-PLANTED-T1000-GATE04.sh` -- byte for byte the path
its own negative control expected to be absent. Intent does not matter: the effect is a control
that cannot fail, and nothing downstream could have told.

The fix is host-side and runs BEFORE the control: if any DEVLOOP-PLANTED-* sentinel named in the
command already exists in the worktree, refuse to gate (exit 2). Your control must be valid too
(SKILL.md 6) -- and validity is checked before the control runs, not inferred from its result.

Run: python3 tests/test_sentinel_guard.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = ROOT / "skills" / "dev-loop" / "scripts" / "adapters.py"

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def gate(create_sentinel: bool) -> tuple[int, str]:
    """Run one merge gate over a throwaway worktree.

    The run directory lives OUTSIDE the worktree on purpose: the gate writes neg-<id>.log into
    it, and a run dir inside the tree would appear between the two tree snapshots and be
    misreported as the control failing to restore. (Cost me two false negatives before I saw it.)
    """
    base = Path(tempfile.mkdtemp())
    wt = base / "wt"; wt.mkdir()
    run = base / "run"; run.mkdir()
    subprocess.run(["git", "init", "-q", str(wt)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(wt), "config", k, v], check=True)
    (wt / "f.md").write_text("ok\n")
    subprocess.run(["git", "-C", str(wt), "add", "f.md"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "init"], check=True)

    if create_sentinel:                      # the lane creates the path its control expects gone
        (wt / "DEVLOOP-PLANTED-X.sh").write_text("# planted by the lane\n")

    # A realistic sentinel control: plants a citation, fails non-zero, NAMES the plant, restores.
    neg = ("cp f.md .bak; trap 'mv .bak f.md' EXIT INT TERM; "
           "printf 'DEVLOOP-PLANTED-X.sh:1\\n' >> f.md; "
           "if grep -q 'DEVLOOP-PLANTED-X' f.md; then "
           "echo 'citation does not resolve: DEVLOOP-PLANTED-X.sh'; exit 1; fi")
    lane = {"id": "x", "objective": "o", "owned_paths": ["f.md"],
            "positive_cmd": "true", "negative_control_cmd": neg,
            "negative_expect": "DEVLOOP-PLANTED-X"}
    lf = base / "lane.json"; lf.write_text(json.dumps(lane))

    cp = subprocess.run([sys.executable, str(ADAPTERS), "gate", "--lane", str(lf),
                         "--wt", str(wt), "--run", str(run)], capture_output=True, text=True)
    return cp.returncode, (cp.stdout + cp.stderr)


def test_clean_worktree_gates_normally() -> None:
    """POSITIVE CONTROL — and the baseline for everything below. A guard that fires on every
    lane would satisfy the negative case while blocking all real work, so this must pass
    cleanly before the refusal below means anything (SKILL.md 6)."""
    print("sentinel absent (normal lane):")
    rc, out = gate(False)
    check("gate passes", rc == 0, f"rc={rc}: {out.strip().splitlines()[-1] if out.strip() else ''}")
    check("the negative control was actually run and failed for its reason",
          "FAILED for the expected reason" in out)
    check("the guard stayed silent", "VACUOUS BEFORE IT RAN" not in out,
          "a guard that fires on a clean tree blocks every lane")


def test_preexisting_sentinel_is_refused() -> None:
    """NEGATIVE CONTROL — the live failure, reproduced."""
    print("sentinel already present (the MiOS case):")
    rc, out = gate(True)
    check("gate refuses with exit 2", rc == 2, f"rc={rc}")
    check("it says the control was vacuous BEFORE running", "VACUOUS BEFORE IT RAN" in out)
    check("it names the sentinel", "DEVLOOP-PLANTED-X" in out)
    check("it names the offending file", "DEVLOOP-PLANTED-X.sh" in out)
    check("it did NOT report the control as having failed for its reason",
          "FAILED for the expected reason" not in out,
          "refusing after the fact would already have accepted a vacuous result")


def main() -> int:
    for t in (test_clean_worktree_gates_normally, test_preexisting_sentinel_is_refused):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all sentinel-guard controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
