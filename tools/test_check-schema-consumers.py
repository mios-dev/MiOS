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

_MADE = []

def _cleanup_fixtures():
    """Remove the fixture repos this module made.

    mkdtemp leaves its directory behind, so every run added one per fixture;
    forty had accumulated in the temp directory, where an editor lists any of
    them that contain a repository as a checkout.
    """
    import shutil
    import stat

    for d in _MADE:
        for base, dirs, files in os.walk(d):
            for name in dirs + files:
                try:
                    os.chmod(os.path.join(base, name), stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
        shutil.rmtree(d, ignore_errors=True)
    _MADE.clear()

def mkrepo(tables, consumers=None, register=(), doc_mentions=(), toml_mentions=()):
    """tables: names to CREATE. consumers: {table: relpath} code files that
    reference it. register: [(table, reason)]. Returns the repo root."""
    root = tempfile.mkdtemp(prefix="schemacons-")
    _MADE.append(root)
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

def run(root, git=None):
    """git: a directory to prepend to PATH, used to stand a refusing git in
    front of the real one."""
    env = dict(os.environ, MIOS_DRIFT_ROOT=root)
    if git:
        env["PATH"] = git + os.pathsep + env.get("PATH", "")
    r = subprocess.run([sys.executable, os.path.join(_HERE, "check-schema-consumers.py")],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr

def mkshim():
    """A git that refuses, the way one does over a foreign-owned checkout."""
    d = tempfile.mkdtemp(prefix="gitshim-")
    _MADE.append(d)
    p = os.path.join(d, "git")
    open(p, "w").write('#!/bin/sh\n'
                       'echo "fatal: detected dubious ownership in repository" >&2\n'
                       'exit 128\n')
    os.chmod(p, 0o755)
    return d

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

def t_deleted_tracked_schema_fails():
    """The subject of the gate, deleted. It stays in the index, so this is a
    dropped deliverable and not the partial checkout the skip was written for."""
    r = mkrepo(["knowledge"], consumers={"knowledge": "usr/lib/mios/reader.py"})
    try:
        os.remove(os.path.join(r, M.SCHEMA))
        rc, out = run(r)
        check("deleting the TRACKED schema fails rather than passing",
              rc == 1, out)
        check("the message names the missing subject",
              "declares no CREATE TABLE" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)

def t_untracked_missing_schema_still_skips():
    """A checkout that never had the file is the state the skip exists for."""
    r = mkrepo(["knowledge"], consumers={"knowledge": "usr/lib/mios/reader.py"})
    try:
        os.remove(os.path.join(r, M.SCHEMA))
        subprocess.run(["git", "-C", r, "rm", "-q", "--cached", M.SCHEMA],
                       check=True, capture_output=True)
        rc, out = run(r)
        check("an UNtracked missing schema still skips", rc == 0, out)
        check("the skip says why", "partial checkout" in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)

def t_refusing_git_is_not_a_verdict_on_the_tables():
    """git grep exits >1 when it cannot search. Reading that as "no match" made
    every live table look dead, and the remedy the message named would have
    registered the whole schema as unconsumed."""
    r = mkrepo(["knowledge"], consumers={"knowledge": "usr/lib/mios/reader.py"})
    try:
        rc, out = run(r, git=mkshim())
        check("a refusing git fails the gate", rc == 1, out)
        check("it blames git, not the tables",
              "cannot" in out and "no reader and no writer" not in out, out)
    finally:
        shutil.rmtree(r, ignore_errors=True)

def main():
    t_real_consumer_passes()
    t_deleted_tracked_schema_fails()
    t_untracked_missing_schema_still_skips()
    t_refusing_git_is_not_a_verdict_on_the_tables()
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
    try:
        _rc = main()
    finally:
        # main() has its own exit path, so the fixtures are removed here rather
        # than from a unittest hook this module never reaches.
        _cleanup_fixtures()
    sys.exit(_rc)
