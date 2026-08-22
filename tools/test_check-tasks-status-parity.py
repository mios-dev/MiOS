# AI-hint: !/usr/bin/env python3 Sibling unit test for tools/check-tasks-status-parity.py.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_tasks_status_parity_py.md

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "check_tasks_status_parity", os.path.join(_HERE, "check-tasks-status-parity.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))


def mkrepo(rows, sections):
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
    open(os.path.join(root, M.TASKS), "w", encoding="utf-8").write("\n".join(body) + "\n")
    return root


def run(root):
    p = subprocess.run([sys.executable, os.path.join(_HERE, "check-tasks-status-parity.py")],
                       env={**os.environ, "MIOS_DRIFT_ROOT": root},
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    roots = []

    r = mkrepo([("T-001", "P1", "done"), ("T-002", "P2", "planned")],
               [("T-001", "--", "done"), ("T-002", ":", "planned")])
    roots.append(r)
    rc, out = run(r)
    check("agreeing surfaces pass (both heading styles)", rc == 0, out)
    check("the pass line reports the open count", "open=1" in out, out)

    r = mkrepo([("T-001", "P1", "done")], [("T-001", "--", "planned")])
    roots.append(r)
    rc, out = run(r)
    check("a disagreeing cell fails", rc == 1 and "T-001" in out, out)

    r = mkrepo([("T-001", "P1", "?")], [("T-001", "--", "in-progress")])
    roots.append(r)
    rc, out = run(r)
    check("'?' fails when a section can answer it", rc == 1 and "'?'" in out, out)

    r = mkrepo([("T-001", "P1", "done")],
               [("T-001", "--", "done -- a long explanation with -- dashes in it")])
    roots.append(r)
    rc, out = run(r)
    check("free prose after ' -- ' is ignored", rc == 0, out)

    r = mkrepo([("T-001", "P1", "in-progress")],
               [("T-001", "--", "in-progress (built-gated)")])
    roots.append(r)
    rc, out = run(r)
    check("a ' (qualifier)' is ignored", rc == 0, out)

    r = mkrepo([("T-001", "P1", "finished")], [("T-001", "--", "finished")])
    roots.append(r)
    rc, out = run(r)
    check("an unknown status word fails even when both agree",
          rc == 1 and "unknown status" in out, out)

    r = mkrepo([("T-001", "P1", "done")],
               [("T-001", "--", "done"), ("T-002", "--", "done")])
    roots.append(r)
    rc, out = run(r)
    check("a section with no summary row fails",
          rc == 1 and "T-002" in out and "no row in the summary table" in out, out)

    r = mkrepo([], [])
    roots.append(r)
    rc, out = run(r)
    check("an unparseable summary table fails rather than passing vacuously",
          rc == 1 and "no parseable rows" in out, out)

    r = mkrepo([("T-001", "P1", "?")], [])
    roots.append(r)
    rc, out = run(r)
    check("'?' with no section to resolve it still fails", rc == 1, out)

    r = mkrepo([("T-001", "P1", "done")], [])
    roots.append(r)
    rc, out = run(r)
    check("a row with no section is allowed when it carries a real status",
          rc == 0, out)

    check("head_token strips the continuation", M.head_token("done -- x") == "done")
    check("head_token strips the qualifier", M.head_token("planned (decision)") == "planned")
    check("head_token lowercases", M.head_token("Done") == "done")

    for r in roots:
        shutil.rmtree(r, ignore_errors=True)
    print(f"\n{'FAIL' if _fails else 'PASS'}: {_fails} failure(s)")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
