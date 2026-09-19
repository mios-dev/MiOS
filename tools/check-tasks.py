#!/usr/bin/env python3
# AI-hint: Task-plane drift gates in one module: TASKS.md table-vs-section parity, AGY task schema, and AGY id/dependency resolution. The subcommand selects the gate.
# AI-doc: usr/share/doc/mios/manual/tools.md
# AI-functions: main, status_parity_main, schema_main, agy_main
"""Task-plane drift gates. One module, one subcommand per gate."""

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

def status_parity_head_token(status: str) -> str:
    """The comparable head of a free-prose status: everything before the first
    ` -- ` continuation or ` (` qualifier."""
    return re.split(r"\s+--\s+|\s*\(", status, maxsplit=1)[0].strip().rstrip(".,;:").lower()

def status_parity_detail_statuses(text: str) -> dict:
    out = {}
    for m in _SECTION_RE.finditer(text):
        sm = _STATUS_RE.search(m.group(0))
        if sm:
            out[m.group(1)] = sm.group(1).strip()
    return out

def status_parity_table_rows(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = _ROW_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out

def status_parity_collect_agy_task_ids(root: str) -> set[int]:
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

def status_parity_main() -> int:
    """Gate: TASKS.md summary table agrees with each section and AGY refs resolve."""
    root = os.environ.get("MIOS_DRIFT_ROOT", os.environ.get("MIOS_TOML_ROOT", "."))
    path = os.path.join(root, TASKS)
    if not os.path.isfile(path):
        print(f"{TASKS} not found under {root}")
        return 1
    text = open(path, encoding="utf-8", errors="replace").read()
    detail = status_parity_detail_statuses(text)
    rows = status_parity_table_rows(text)
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
        want = status_parity_head_token(detail[tid])
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
    agy_ids = status_parity_collect_agy_task_ids(root)
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


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# The id below which the schema is not yet demanded. It lives in the SSOT as a
# shrink-only ratchet, not as a constant here, so retro-fitting a batch of older
# tasks is a measurable step rather than an edit nobody notices. A task marked
# DONE is exempt whatever its id: it has already been done, so a Verify line
# added now would be one nobody checked.
SCHEMA_FROM_DEFAULT = 1607
DONE_MARKER = "[DONE]"

REQUIRED = ("Goal", "What+How", "Where", "Verify", "Do NOT", "Done When", "Why", "Dep")
HEAD_RE = re.compile(r"^#{2,3} AGY-(\d+)(?:\.\.(\d+))? ", re.M)

def schema_main() -> int:
    """Gate: every AGY task carries the full schema; a missing Verify is a task anyone can call done."""
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    path = os.path.join(root, "AGY-TASKS.md")
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"AGY-TASKS.md unreadable: {exc}")
        return 1

    try:
        with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
            tasks_tbl = (tomllib.load(fh).get("tasks") or {})
    except OSError:
        tasks_tbl = {}
    schema_from = tasks_tbl.get("schema_from")
    if schema_from is None:
        print("mios.toml has no [tasks].schema_from -- without it the schema"
              " floor is a constant nobody can lower on purpose")
        return 1
    schema_from = int(schema_from)

    blocks = re.split(r"(?=^#{2,3} AGY-\d+(?:\.\.\d+)? )", text, flags=re.M)
    ids, covered, viol = [], set(), []
    for b in blocks:
        m = HEAD_RE.match(b)
        if not m:
            continue
        tid = int(m.group(1))
        # `## AGY-106..122 -- Campaign banner` covers every id in the range, so
        # a Dep naming one of them names a task that exists -- but the banner
        # plus its individual children is the NORMAL shape, not a collision, so
        # only individual headings count toward the duplicate ceiling.
        if m.group(2):
            covered.update(range(tid, int(m.group(2)) + 1))
            continue
        ids.append(tid)
        if tid < schema_from or DONE_MARKER in b.split(chr(10))[0]:
            continue
        for field in REQUIRED:
            if f"**{field}:**" not in b:
                viol.append(f"AGY-{tid}: missing **{field}:**")

    known = set(ids) | covered
    for b in blocks:
        m = HEAD_RE.match(b)
        if not m or m.group(2) or int(m.group(1)) < schema_from:
            continue
        dep = re.search(r"^\*\*Dep:\*\*\s*(.+)$", b, re.M)
        if not dep:
            continue
        for ref in re.findall(r"AGY-(\d+)", dep.group(1)):
            if int(ref) not in known:
                viol.append(f"AGY-{m.group(1)}: **Dep:** names AGY-{ref}, which does not exist")

    dupes = sorted({i for i in ids if ids.count(i) > 1})
    try:
        with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
            ceil = ((tomllib.load(fh).get("tasks") or {}).get("max_duplicate_ids"))
    except OSError:
        ceil = None
    if ceil is None:
        viol.append("mios.toml has no [tasks].max_duplicate_ids -- absent is a broken"
                    " ceiling, not an open one")
    elif len(dupes) > int(ceil):
        viol.append(f"duplicate task ids {len(dupes)} > ceiling {ceil}: "
                    f"{['AGY-%d' % d for d in dupes[:8]]}")

    print("\n".join(viol))
    if not viol:
        n = sum(1 for i in ids if i >= schema_from)
        print(f"[check-task-schema] {n} task(s) carry the full schema; "
              f"{len(dupes)}/{ceil} duplicate ids", file=sys.stderr)
    return 1 if viol else 0


AGY_TASKS_FILE = "AGY-TASKS.md"

def agy_extract_dep_ids(dep_str: str) -> list[int]:
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

def agy_main() -> int:
    """Gate: AGY task IDs are unique and dependency links resolve."""
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

        ref_ids = agy_extract_dep_ids(dep_str)
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

_GATES = {"status-parity": status_parity_main, "schema": schema_main, "agy": agy_main}


def main() -> int:
    # An unknown or missing subcommand must FAIL, never report a clean gate.
    if len(sys.argv) < 2 or sys.argv[1] not in _GATES:
        sys.stderr.write("usage: check-tasks.py {%s}\n" % "|".join(sorted(_GATES)))
        return 2
    return _GATES[sys.argv.pop(1)]()


if __name__ == "__main__":
    sys.exit(main())
