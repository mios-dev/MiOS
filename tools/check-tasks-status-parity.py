#!/usr/bin/env python3
# AI-hint: Drift gate for a lying roadmap. TASKS.md carries every task twice, and references AGY-TASKS.md (AGY-1647).
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: TASKS.md summary table agrees with each task section and AGY-TASKS.md references resolve."""

import os
import re
import sys

TASKS = "TASKS.md"
AGY_TASKS = "AGY-TASKS.md"
PLACEHOLDER = "?"
KNOWN = {
    "done", "done-by-code", "completed", "retired",
    "planned", "planned/unverified", "in-progress", "pending",
    "partial", "open", "blocked", "built-gated-off",
}

_SECTION_RE = re.compile(r"^## (T-\d+)\s*(?:--|:)\s*(.*?)(?=^## |\Z)", re.M | re.S)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*(?:\||$)", re.M)
_ROW_RE = re.compile(r"^\|\s*(T-\d+)\s*\|\s*P\d\s*\|\s*([^|]+?)\s*\|")


def head_token(status: str) -> str:
    """The comparable head of a free-prose status: everything before the first
    ` -- ` continuation or ` (` qualifier."""
    return re.split(r"\s+--\s+|\s*\(", status, maxsplit=1)[0].strip().rstrip(".,;:").lower()


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
            out[m.group(1)] = m.group(2).strip()
    return out


def collect_agy_task_ids(root: str) -> set[int]:
    path = os.path.join(root, AGY_TASKS)
    if not os.path.isfile(path):
        return set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    header_pattern = re.compile(r"^(#+)\s*AGY-(\d+)(?:\.\.(?:AGY-)?(\d+))?(?:\s+.*)?$", re.MULTILINE)
    task_ids = set()
    for line in content.splitlines():
        m = header_pattern.match(line)
        if m:
            start_str, end_str = m.group(2), m.group(3)
            if end_str:
                for tid in range(int(start_str), int(end_str) + 1):
                    task_ids.add(tid)
            else:
                task_ids.add(int(start_str))
    return task_ids


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT", os.environ.get("MIOS_TOML_ROOT", "."))
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

    # Cross-file validation with AGY-TASKS.md
    agy_ids = collect_agy_task_ids(root)
    if agy_ids:
        # Find all AGY-xxx references in TASKS.md
        referenced_agy = re.findall(r"\bAGY-(\d+)\b", text)
        for ref in referenced_agy:
            ref_id = int(ref)
            if ref_id not in agy_ids:
                problems.append(f"VIOLATION: TASKS.md references AGY-{ref_id} which does not exist in AGY-TASKS.md")

    if problems:
        for p in problems:
            print(p)
        return 1

    closed = {"done", "done-by-code", "completed", "retired"}
    open_n = sum(1 for s in rows.values() if s not in closed)
    print(f"TASKS.md summary table matches every task section and AGY-TASKS.md references resolve "
          f"(tasks={len(rows)} sections={len(detail)} open={open_n} agy_validations={len(agy_ids)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
