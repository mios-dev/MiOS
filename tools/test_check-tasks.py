#!/usr/bin/env python3
# AI-hint: Sibling unit tests for tools/check-tasks.py -- one suite per subcommand (status-parity, schema, agy), each with its own failure counter.
"""Sibling tests for the consolidated task-plane gates."""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile


sp__HERE = os.path.dirname(os.path.abspath(__file__))
sp__spec = importlib.util.spec_from_file_location(
    "check_tasks", os.path.join(sp__HERE, "check-tasks.py"))
sp_M = importlib.util.module_from_spec(sp__spec)
sp__spec.loader.exec_module(sp_M)

sp__fails = 0

def sp_check(name, cond, detail=""):
    global sp__fails
    if cond:
        print(f"ok   - {name}")
    else:
        sp__fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))

def sp_mkrepo(rows, sections):
    """rows: [(tid, pri, status)] summary table. sections: [(tid, sep, status)]."""
    root = tempfile.mkdtemp(prefix="tasksparity-")
    body = ["| ID | Pri | Status | Domain | Title |",
            "|----|-----|--------|--------|-------|"]
    for tid, pri, status in rows:
        body.append(f"| {tid} | {pri} | {status} | Domain | Title |")
    body.append("")
    for tid, sep, status in sections:
        body.append(f"## {tid} {sep} Title  (WS-X | P1 | S)")
        body.append("**Goal:** goal.")
        body.append(f"**Status:** {status} | **Domain:** Domain")
        body.append("")
    open(os.path.join(root, sp_M.TASKS), "w", encoding="utf-8").write("\n".join(body) + "\n")
    return root

def sp_run(root):
    p = subprocess.run([sys.executable, os.path.join(sp__HERE, "check-tasks.py"), "status-parity"],
                       env={**os.environ, "MIOS_DRIFT_ROOT": root},
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

def sp_main():
    roots = []

    r = sp_mkrepo([("T-001", "P1", "done"), ("T-002", "P2", "planned")],
               [("T-001", "--", "done"), ("T-002", ":", "planned")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("agreeing surfaces pass (both heading styles)", rc == 0, out)
    sp_check("the pass line reports the open count", "open=1" in out, out)

    r = sp_mkrepo([("T-001", "P1", "done")], [("T-001", "--", "planned")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("a disagreeing cell fails", rc == 1 and "T-001" in out, out)

    r = sp_mkrepo([("T-001", "P1", "?")], [("T-001", "--", "in-progress")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("'?' fails when a section can answer it", rc == 1 and "'?'" in out, out)

    r = sp_mkrepo([("T-001", "P1", "done")],
               [("T-001", "--", "done -- a long explanation with -- dashes in it")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("free prose after ' -- ' is ignored", rc == 0, out)

    r = sp_mkrepo([("T-001", "P1", "in-progress")],
               [("T-001", "--", "in-progress (built-gated)")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("a ' (qualifier)' is ignored", rc == 0, out)

    r = sp_mkrepo([("T-001", "P1", "finished")], [("T-001", "--", "finished")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("an unknown status word fails even when both agree",
          rc == 1 and "unknown status" in out, out)

    r = sp_mkrepo([("T-001", "P1", "done")],
               [("T-001", "--", "done"), ("T-002", "--", "done")])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("a section with no summary row fails",
          rc == 1 and "T-002" in out and "no row in the summary table" in out, out)

    r = sp_mkrepo([], [])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("an unparseable summary table fails rather than passing vacuously",
          rc == 1 and "no parseable rows" in out, out)

    r = sp_mkrepo([("T-001", "P1", "?")], [])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("'?' with no section to resolve it still fails", rc == 1, out)

    r = sp_mkrepo([("T-001", "P1", "done")], [])
    roots.append(r)
    rc, out = sp_run(r)
    sp_check("a row with no section is allowed when it carries a real status",
          rc == 0, out)

    sp_check("head_token strips the continuation", sp_M.status_parity_head_token("done -- x") == "done")
    sp_check("head_token strips the qualifier", sp_M.status_parity_head_token("planned (decision)") == "planned")
    sp_check("head_token lowercases", sp_M.status_parity_head_token("Done") == "done")

    for r in roots:
        shutil.rmtree(r, ignore_errors=True)
    print(f"\n{'FAIL' if sp__fails else 'PASS'}: {sp__fails} failure(s)")
    return 1 if sp__fails else 0


sch__HERE = os.path.dirname(os.path.abspath(__file__))
sch__fails = 0

def sch_check(name, cond, detail=""):
    global sch__fails
    if cond:
        print(f"ok   - {name}")
    else:
        sch__fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))

def sch_run_tool(root):
    p = subprocess.run(
        [sys.executable, os.path.join(sch__HERE, "check-tasks.py"), "schema"],
        env={**os.environ, "MIOS_DRIFT_ROOT": root},
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr

def sch_main():
    root = tempfile.mkdtemp(prefix="task-schema-test-")
    try:
        os.makedirs(os.path.join(root, "usr/share/mios"), exist_ok=True)
        shutil.copy(
            os.path.join(sch__HERE, "../usr/share/mios/mios.toml"),
            os.path.join(root, "usr/share/mios/mios.toml"),
        )
        shutil.copy(
            os.path.join(sch__HERE, "../AGY-TASKS.md"),
            os.path.join(root, "AGY-TASKS.md"),
        )

        rc, out = sch_run_tool(root)
        sch_check("valid AGY-TASKS.md passes task schema check", rc == 0, f"rc={rc} out={out}")

        # Test missing field failure on a schema-governed task
        bad_task = """
## AGY-1608 -- Test task  (WS-TEST | P0 | S)
**Goal:** test
**What+How:** test
**Where:** test
**Done When:** test
**Why:** test
**Dep:** none
"""
        with open(os.path.join(root, "AGY-TASKS.md"), "a", encoding="utf-8") as f:
            f.write(bad_task)

        rc, out = sch_run_tool(root)
        sch_check("missing required field (Verify / Do NOT) fails", rc != 0, f"rc={rc} out={out}")

    finally:
        shutil.rmtree(root, ignore_errors=True)

    if sch__fails > 0:
        return 1


agy__HERE = os.path.dirname(os.path.abspath(__file__))
agy__fails = 0

def agy_check(name, cond, detail=""):
    global agy__fails
    if cond:
        print(f"ok   - {name}")
    else:
        agy__fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))

def agy_run_tool(root):
    p = subprocess.run(
        [sys.executable, os.path.join(agy__HERE, "check-tasks.py"), "agy"],
        env={**os.environ, "MIOS_DRIFT_ROOT": root},
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr

def agy_main():
    root = tempfile.mkdtemp(prefix="agy-tasks-test-")
    try:
        content_clean = """
## AGY-1 -- First task
**Dep:** none

## AGY-2 -- Second task
**Dep:** AGY-1
"""
        with open(os.path.join(root, "AGY-TASKS.md"), "w", encoding="utf-8") as f:
            f.write(content_clean)

        rc, out = agy_run_tool(root)
        agy_check("clean AGY tasks passes", rc == 0, f"rc={rc} out={out}")

        content_dup = content_clean + "\n## AGY-1 -- Duplicate task\n"
        with open(os.path.join(root, "AGY-TASKS.md"), "w", encoding="utf-8") as f:
            f.write(content_dup)

        rc, out = agy_run_tool(root)
        agy_check("duplicate AGY task ID fails", rc != 0, f"rc={rc} out={out}")

        content_dangling = content_clean + "\n## AGY-3 -- Task\n**Dep:** AGY-99999\n"
        with open(os.path.join(root, "AGY-TASKS.md"), "w", encoding="utf-8") as f:
            f.write(content_dangling)

        rc, out = agy_run_tool(root)
        agy_check("dangling dependency reference fails", rc != 0, f"rc={rc} out={out}")

    finally:
        shutil.rmtree(root, ignore_errors=True)

    if agy__fails > 0:
        return 1

def main():
    # Every suite runs even when an earlier one fails; the old scripts called
    # sys.exit, which in one file would hide the suites after the first failure.
    rc = 0
    for fn in (sp_main, sch_main, agy_main):
        rc |= (fn() or 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
