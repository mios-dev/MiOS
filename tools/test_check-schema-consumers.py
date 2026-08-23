#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-schema-consumers.py.
# AI-doc: usr/share/doc/mios/manual/tools.md

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "check_schema_consumers", os.path.join(_HERE, "check-schema-consumers.py"))
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


def mkrepo(tables, consumers=None, register=(), doc_mentions=(), toml_mentions=()):
    """tables: names to CREATE. consumers: {table: relpath} code files that
    reference it. register: [(table, reason)]. Returns the repo root."""
    root = tempfile.mkdtemp(prefix="schemacons-")
    os.makedirs(os.path.join(root, "usr/share/mios/postgres"), exist_ok=True)
    os.makedirs(os.path.join(root, "usr/lib/mios"), exist_ok=True)
    os.makedirs(os.path.join(root, "usr/share/doc/mios"), exist_ok=True)

    sql = "".join(f"CREATE TABLE IF NOT EXISTS {t} (id bigint);\n" for t in tables)
    open(os.path.join(root, M.SCHEMA), "w").write(sql)

    rows = "\n".join('    { table = "%s", reason = "%s" },' % (t, r) for t, r in register)
    open(os.path.join(root, "usr/share/mios/mios.toml"), "w").write(
        "[schema]\nunconsumed = [\n%s\n]\n" % rows
        + "".join('# policy mentions %s\n' % t for t in toml_mentions))

    for table, rel in (consumers or {}).items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w").write(f'SQL = "SELECT * FROM {table}"\n')

    for t in doc_mentions:
        open(os.path.join(root, "usr/share/doc/mios/notes.md"), "a").write(
            f"the {t} table is planned\n")

    subprocess.run(["git", "-C", root, "init", "-q"], check=True)
    subprocess.run(["git", "-C", root, "add", "-A"], check=True,
                   capture_output=True)
    return root


def run(root):
    env = dict(os.environ, MIOS_DRIFT_ROOT=root)
    r = subprocess.run([sys.executable, os.path.join(_HERE, "check-schema-consumers.py")],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def t_real_consumer_passes():
    r = mkrepo(["knowledge"], consumers={"knowledge": "usr/lib/mios/reader.py"})
    try:
        rc, out = run(r)
        check("a table with a code consumer passes", rc == 0, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_dead_table_fails():
    r = mkrepo(["ghost"])
    try:
        rc, out = run(r)
        check("a table with no consumer fails", rc == 1, out)
        check("the message says what to do", "wire it, drop it, or record it" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_doc_mention_is_not_a_consumer():
    r = mkrepo(["ghost"], doc_mentions=["ghost"])
    try:
        rc, out = run(r)
        check("a doc mention does NOT count as a consumer", rc == 1, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_toml_mention_is_not_a_consumer():
    # The register itself names the table; if .toml counted, the register
    # would satisfy the gate on its own and the whole check would be vacuous.
    r = mkrepo(["ghost"], toml_mentions=["ghost"])
    try:
        rc, out = run(r)
        check("a .toml mention does NOT count as a consumer", rc == 1, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_generated_projection_is_not_a_consumer():
    """A file generated FROM mios.toml re-emits the register itself, so counting
    it would make every registered table look consumed -- which is exactly what
    happened once automation/lib/globals.sh was regenerated."""
    r = mkrepo(["ghost"], register=[("ghost", "planned")])
    try:
        gen = os.path.join(r, "automation/lib/globals.sh")
        os.makedirs(os.path.dirname(gen), exist_ok=True)
        with open(gen, "w") as fh:
            fh.write("# AI-hint: GENERATED IN FULL from usr/share/mios/mios.toml\n"
                     "MIOS_SCHEMA_UNCONSUMED_0_TABLE='ghost'\n")
        subprocess.run(["git", "-C", r, "add", "-A"], check=True, capture_output=True)
        rc, out = run(r)
        check("a GENERATED projection does NOT count as a consumer", rc == 0, out)
        check("the table stays registered rather than looking wired",
              "registered-unconsumed=1" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_registered_dead_table_passes():
    r = mkrepo(["ghost"], register=[("ghost", "planned")])
    try:
        rc, out = run(r)
        check("a REGISTERED dead table passes", rc == 0, out)
        check("the count is reported", "registered-unconsumed=1" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_registered_table_that_gained_a_consumer_fails():
    r = mkrepo(["ghost"], consumers={"ghost": "usr/lib/mios/reader.py"},
               register=[("ghost", "planned")])
    try:
        rc, out = run(r)
        check("a registered table that GAINED a consumer fails (register shrinks)",
              rc == 1 and "now HAS a consumer" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_stale_register_entry_fails():
    r = mkrepo(["knowledge"], consumers={"knowledge": "usr/lib/mios/reader.py"},
               register=[("gone", "planned")])
    try:
        rc, out = run(r)
        check("a register entry for a dropped table fails",
              rc == 1 and "no longer declares" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)


def main():
    t_real_consumer_passes()
    t_dead_table_fails()
    t_doc_mention_is_not_a_consumer()
    t_toml_mention_is_not_a_consumer()
    t_generated_projection_is_not_a_consumer()
    t_registered_dead_table_passes()
    t_registered_table_that_gained_a_consumer_fails()
    t_stale_register_entry_fails()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
