#!/usr/bin/env python3
# AI-hint: Drift gate for AGY task unique IDs and dependency resolution (AGY-1687).
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: AGY task IDs in AGY-TASKS.md are unique and dependency links resolve."""

import os
import re
import sys

AGY_TASKS_FILE = "AGY-TASKS.md"

def extract_dep_ids(dep_str: str) -> list[int]:
    """Extract all AGY task IDs referenced in a Dep line, including ranges."""
    ids = []
    def expand_range(match):
        start = int(match.group(1))
        end = int(match.group(2))
        return " ".join(f"AGY-{i}" for i in range(start, end + 1))

    normalized = re.sub(r"AGY-(\d+)\.\.(?:AGY-)?(\d+)", expand_range, dep_str)

    for m in re.finditer(r"\bAGY-(\d+)\b", normalized):
        ids.append(int(m.group(1)))
    return ids


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT", os.environ.get("MIOS_TOML_ROOT", "."))
    path = os.path.join(root, AGY_TASKS_FILE)
    if not os.path.isfile(path):
        print(f"VIOLATION: {AGY_TASKS_FILE} not found under {root}")
        return 1

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Pattern for AGY headers: single task '## AGY-123' or range '## AGY-123..259' / '## AGY-123..AGY-259'
    header_pattern = re.compile(r"^(#+)\s*AGY-(\d+)(?:\.\.(?:AGY-)?(\d+))?(?:\s+.*)?$", re.MULTILINE)

    task_occurrences = {}
    task_ids = set()

    for line_idx, line in enumerate(content.splitlines(), 1):
        m = header_pattern.match(line)
        if m:
            start_str, end_str = m.group(2), m.group(3)
            if end_str:
                start_id, end_id = int(start_str), int(end_str)
                for tid in range(start_id, end_id + 1):
                    task_ids.add(tid)
            else:
                tid = int(start_str)
                task_ids.add(tid)
                if tid not in task_occurrences:
                    task_occurrences[tid] = []
                task_occurrences[tid].append((line_idx, line))

    problems = []

    # Check for duplicate standalone task IDs
    for tid, occs in task_occurrences.items():
        if len(occs) > 1:
            locs = ", ".join(f"line {l}" for l, _ in occs)
            problems.append(f"VIOLATION: AGY-{tid} is defined multiple times ({locs})")

    # Check for dangling Dep references
    dep_pattern = re.compile(r"\*\*Dep:\*\*\s*(.*)", re.IGNORECASE)
    for line_idx, line in enumerate(content.splitlines(), 1):
        m = dep_pattern.search(line)
        if not m:
            continue
        dep_str = m.group(1).strip()
        if dep_str.lower() in ("none", "n/a", ""):
            continue

        ref_ids = extract_dep_ids(dep_str)
        for ref_id in ref_ids:
            if ref_id not in task_ids:
                problems.append(
                    f"VIOLATION: line {line_idx} has dangling dependency reference AGY-{ref_id}"
                )

    if problems:
        for p in problems:
            print(p)
        return 1

    print(
        f"AGY task ID parity check passed (tasks={len(task_ids)}, standalone_ids={len(task_occurrences)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
