#!/usr/bin/env python3
# AI-hint: Fails when an AGY task omits a required field, names a dependency that does not exist, or reuses an id beyond the shrink-only ceiling.
# AI-related: AGY-TASKS.md, usr/share/mios/mios.toml, automation/98-drift-checks.sh
"""A task without a Verify line is a task anyone can call done.

Every field here exists because its absence let something through. Verify is an
exact command whose failure is the proof; Do NOT names the dodge that would
satisfy the task falsely -- raising a ceiling, wrapping a hint, spelling a check
name in a log line. Dep is checked because a dependency pointing at a
non-existent id is an ordering nobody can follow, and ids are counted because 25
of them are already used twice, which makes every Dep naming one ambiguous.
"""
import os
import re
import sys

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

def main() -> int:
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

if __name__ == "__main__":
    sys.exit(main())
