#!/usr/bin/env python3
"""Gate for a dev-loop research lane's findings file.

A research lane's deliverable is a measurement, so the gate must test that a
measurement actually happened -- not that a file exists. SKILL.md §7: asserting
"the file is there" is Measuring the Wrong Property, and a findings file with no
resolvable citation is an Empty-Set Pass.

Requires, all of them:
  * the file parses as the expected section layout (every REQUIRED heading present)
  * at least MIN_CITATIONS `path:line` citations
  * EVERY citation resolves: the path exists under the repo root AND the file has
    at least that many lines  (a citation to a file that is not there, or to line
    900 of a 40-line file, is a fabricated measurement and fails by name)
  * a VERDICT line drawn from the closed vocabulary

Usage:  check-finding.py <repo_root> <findings_file>
Exit 0 = the lane measured something real. Non-zero names what was wrong.
"""

import re
import sys
from pathlib import Path

REQUIRED = ("## VERDICT", "## WHAT IS ACTUALLY TRUE", "## NUMBERS", "## PROPOSED FIX",
            "## FILES TO CHANGE", "## NEGATIVE CONTROL", "## UNVERIFIED")
VERDICTS = ("CONFIRMED", "PARTLY_CONFIRMED", "REFUTED", "STALE")
MIN_CITATIONS = 3

# path:line -- the path may not contain spaces or a colon; the line is 1+ digits.
CITATION = re.compile(r"\b([A-Za-z0-9_./-]+\.[A-Za-z0-9_]+):(\d+)\b")


def fail(msg):
    print(f"check-finding: FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        fail("usage: check-finding.py <repo_root> <findings_file>")
    root, target = Path(sys.argv[1]).resolve(), Path(sys.argv[2])

    if not target.is_file():
        fail(f"{target} does not exist -- the lane produced no findings file")
    text = target.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        fail(f"{target} is empty")

    missing = [h for h in REQUIRED if h not in text]
    if missing:
        fail(f"{target} is missing required section(s): {', '.join(missing)}")

    verdict_line = next((l for l in text.splitlines()
                         if l.strip() and not l.startswith("#")
                         and any(v in l for v in VERDICTS)), None)
    if verdict_line is None:
        fail(f"{target} states no verdict from {'/'.join(VERDICTS)}")

    cites = CITATION.findall(text)
    if len(cites) < MIN_CITATIONS:
        fail(f"{target} carries {len(cites)} path:line citation(s), need >= {MIN_CITATIONS} "
             f"-- a finding with no citations measured nothing")

    bad = []
    for path, line in cites:
        p = (root / path)
        if not p.is_file():
            bad.append(f"{path}:{line} -- no such file under {root}")
            continue
        n = sum(1 for _ in p.open("rb"))
        if int(line) > n:
            bad.append(f"{path}:{line} -- file has only {n} lines")
    if bad:
        fail(f"{len(bad)} citation(s) in {target} do not resolve:\n  " + "\n  ".join(bad))

    print(f"check-finding: ok -- {target.name}: {len(cites)} citation(s), all resolve; "
          f"verdict present; {len(REQUIRED)} sections present")


if __name__ == "__main__":
    main()
