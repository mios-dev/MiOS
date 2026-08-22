#!/usr/bin/env python3
# AI-hint: Drift gate for a lying roadmap. TASKS.md carries every task twice -- once as a row in the summary table and once as a `**Status:**` line in the task's own section -- and the two silently diverged in 49 places, including seven rows the table called done-by-code while the detail still said open and three P0 rows the table called done while the detail said planned. Whoever reads only one surface gets a different answer about what is left. This gate requires the table cell to equal the head token of the detail status (the text before the first ` -- ` or ` (`), so the two can never disagree again, and rejects the `?` placeholder outright wherever a detail section exists to answer it.
# AI-related: TASKS.md, tools/test_check-tasks-status-parity.py, automation/98-drift-checks.sh
# AI-functions: detail_statuses, table_rows, head_token, main
"""Gate: TASKS.md summary table agrees with each task's own Status line."""

import os
import re
import sys

TASKS = "TASKS.md"
PLACEHOLDER = "?"
# The vocabulary both surfaces are allowed to use. A typo becomes a violation
# rather than a silently new status nothing else recognises.
KNOWN = {
    "done", "done-by-code", "completed", "retired",
    "planned", "planned/unverified", "in-progress", "pending",
    "partial", "open", "blocked", "built-gated-off",
}
# `## T-123 -- Title` and `## T-123: Title` both occur in the file.
_SECTION_RE = re.compile(r"^## (T-\d+)\s*(?:--|:)\s*(.*?)(?=^## |\Z)", re.M | re.S)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*(?:\||$)", re.M)
_ROW_RE = re.compile(r"^\|\s*(T-\d+)\s*\|\s*P\d\s*\|\s*([^|]+?)\s*\|")


def head_token(status: str) -> str:
    """The comparable head of a free-prose status: everything before the first
    ` -- ` continuation or ` (` qualifier."""
    return re.split(r"\s+--\s+|\s*\(", status, 1)[0].strip().rstrip(".,;:").lower()


def detail_statuses(text: str) -> dict:
    out = {}
    for m in _SECTION_RE.finditer(text):
        sm = _STATUS_RE.search(m.group(0))
        if sm:
            out[m.group(1)] = sm.group(1).strip()
    return out


def table_rows(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = _ROW_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    path = os.path.join(root, TASKS)
    if not os.path.isfile(path):
        print(f"{TASKS} not found under {root}")
        return 1
    text = open(path, encoding="utf-8", errors="replace").read()
    detail = detail_statuses(text)
    rows = table_rows(text)
    if not rows:
        print(f"{TASKS} summary table has no parseable rows")
        return 1

    problems = []
    for tid in sorted(rows):
        cell = rows[tid]
        if tid not in detail:
            # The table is the only record for this task; nothing to compare.
            if cell == PLACEHOLDER:
                problems.append(f"{tid}: status is '?' and the task has no section to resolve it")
            elif cell not in KNOWN:
                problems.append(f"{tid}: unknown status '{cell}' in the summary table")
            continue
        want = head_token(detail[tid])
        if cell == PLACEHOLDER:
            problems.append(
                f"{tid}: summary table says '?' while the task section says '{want}'")
        elif cell != want:
            problems.append(
                f"{tid}: summary table says '{cell}', the task section says '{want}'")
        if want not in KNOWN:
            problems.append(f"{tid}: unknown status '{want}' in the task section")

    for tid in sorted(set(detail) - set(rows)):
        problems.append(f"{tid}: has a task section but no row in the summary table")

    if problems:
        for p in problems:
            print(p)
        return 1

    closed = {"done", "done-by-code", "completed", "retired"}
    open_n = sum(1 for s in rows.values() if s not in closed)
    print(f"TASKS.md summary table matches every task section "
          f"(tasks={len(rows)} sections={len(detail)} open={open_n})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
