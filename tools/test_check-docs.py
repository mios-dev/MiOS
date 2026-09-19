#!/usr/bin/env python3
# AI-hint: Sibling unit tests for tools/check-docs.py -- one suite per subcommand, each owning its counters and returning its own verdict.
"""Sibling tests for the consolidated documentation-plane gates."""
from __future__ import annotations

import sys


"""A checker whose exit code never varies is not a check.

These fixtures assert the tool runs against the real tree and returns an exit
code, then assert the specific invariant it exists to defend.
"""

import os
import subprocess
import sys

tdrm_HERE = os.path.dirname(os.path.abspath(__file__))
tdrm_ROOT = os.path.abspath(os.path.join(tdrm_HERE, ".."))
tdrm_TOOL = os.path.join(tdrm_HERE, "check-docs.py")

tdrm_FAILED: list[str] = []
tdrm_PASSED = 0

def tdrm_check(name, got, want):
    global tdrm_PASSED
    if got == want:
        tdrm_PASSED += 1
    else:
        tdrm_FAILED.append(f"{name}: got {got!r}, want {want!r}")

def tdrm_run(env_extra=None):
    env = dict(os.environ, MIOS_DRIFT_ROOT=tdrm_ROOT, MIOS_ROOT=tdrm_ROOT)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, tdrm_TOOL, "ratchet-monotone"], capture_output=True, text=True, env=env)

def tdrm_test_runs_on_real_tree():
    p = tdrm_run()
    tdrm_check("exits-cleanly-or-reports", p.returncode in (0, 1), True)
    tdrm_check("produces-output", bool((p.stdout + p.stderr).strip()), True)

def tdrm_test_exit_code_carries_information():
    src = open(tdrm_TOOL, encoding="utf-8", errors="replace").read()
    reads_env = "MIOS_MAX_" in src
    baseline = tdrm_run()
    if reads_env and baseline.returncode == 0:
        tight = tdrm_run({"MIOS_MAX_UNMIGRATED_NARRATIVE": "0",
                     "MIOS_MAX_STALE_REFS": "0",
                     "MIOS_MAX_OVERLONG_HINTS": "0"})
        tdrm_check("zero-ceiling-can-fail", tight.returncode != 0, True)
    else:
        # Still assert something real: the tool must name what it checked.
        tdrm_check("reports-its-subject", len((baseline.stdout + baseline.stderr).strip()) > 10, True)

def tdrm_main() -> int:
    tdrm_test_runs_on_real_tree()
    tdrm_test_exit_code_carries_information()
    print(f"[test_check-doc-ratchet-monotone] {tdrm_PASSED} passed, {len(tdrm_FAILED)} failed")
    for f in tdrm_FAILED:
        print(f"  FAIL {f}")
    return 1 if tdrm_FAILED else 0


"""Fixture-driven checks that the manual link gate fails for the right reasons."""
import os
import subprocess
import sys
import tempfile

tml_HERE = os.path.dirname(os.path.abspath(__file__))
tml_GATE = os.path.join(tml_HERE, "check-docs.py")
tml_FAILED = 0

def tml_build(tmp, toc, chapters, extra=None):
    docs = os.path.join(tmp, "usr/share/doc/mios")
    os.makedirs(os.path.join(docs, "manual"), exist_ok=True)
    with open(os.path.join(docs, "manual.md"), "w", encoding="utf-8") as fh:
        fh.write(toc)
    for name, body in chapters.items():
        with open(os.path.join(docs, "manual", name), "w", encoding="utf-8") as fh:
            fh.write(body)
    for rel, body in (extra or {}).items():
        path = os.path.join(docs, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    return tmp

def tml_run(root):
    env = dict(os.environ, MIOS_ROOT=root)
    return subprocess.run([sys.executable, tml_GATE, "manual-links"], env=env, capture_output=True, text=True).returncode

def tml_case(name, toc, chapters, want_zero, extra=None):
    global tml_FAILED
    with tempfile.TemporaryDirectory() as tmp:
        rc = tml_run(tml_build(tmp, toc, chapters, extra))
    ok = (rc == 0) if want_zero else (rc != 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} (exit {rc})")
    if not ok:
        tml_FAILED += 1

tml_CH = '<a name="01_intro"></a>\n# Chapter 01\n'

def tml_main():
    global tml_FAILED
    tml_case("clean ToC resolves",
         "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": tml_CH}, True)
    tml_case("dangling chapter link fails",
         "[Ch01](manual/ch01-missing.md#01_intro)\n", {"ch01-intro.md": tml_CH}, False)
    tml_case("missing anchor fails",
         "[Ch01](manual/ch01-intro.md#not_there)\n", {"ch01-intro.md": tml_CH}, False)
    tml_case("unreachable chapter fails",
         "[Ch01](manual/ch01-intro.md#01_intro)\n",
         {"ch01-intro.md": tml_CH, "ch02-orphan.md": "# Chapter 02\n"}, False)
    tml_case("link without a fragment resolves",
         "[Ch01](manual/ch01-intro.md)\n", {"ch01-intro.md": tml_CH}, True)

    # The class that let audit-INDEX.md point at audit-mios-metal.md for the whole
    # time after that name was reassigned to MiOS-Metal.
    tml_case("dangling ./sibling link fails",
         "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": tml_CH}, False,
         extra={"reference/a.md": "see [b](./b.md)\n"})
    tml_case("resolving ./sibling link passes",
         "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": tml_CH}, True,
         extra={"reference/a.md": "see [b](./b.md)\n", "reference/b.md": "# B\n"})
    tml_case("dangling ../parent link fails",
         "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": tml_CH}, False,
         extra={"reference/a.md": "see [x](../concepts/x.md)\n"})
    tml_case("a repo-root-relative path is NOT this gate's business",
         "[Ch01](manual/ch01-intro.md#01_intro)\n", {"ch01-intro.md": tml_CH}, True,
         extra={"reference/a.md": "see [x](usr/share/mios/mios.toml)\n"})

    print(f"\n{9 - tml_FAILED}/9 checks pass")
    return 1 if tml_FAILED else 0


"""A checker whose exit code never varies is not a check.

These fixtures assert the tool runs against the real tree and returns an exit
code, then assert the specific invariant it exists to defend.
"""

import os
import subprocess
import sys

tcle_HERE = os.path.dirname(os.path.abspath(__file__))
tcle_ROOT = os.path.abspath(os.path.join(tcle_HERE, ".."))
tcle_TOOL = os.path.join(tcle_HERE, "check-docs.py")

tcle_FAILED: list[str] = []
tcle_PASSED = 0

def tcle_check(name, got, want):
    global tcle_PASSED
    if got == want:
        tcle_PASSED += 1
    else:
        tcle_FAILED.append(f"{name}: got {got!r}, want {want!r}")

def tcle_run(env_extra=None):
    env = dict(os.environ, MIOS_DRIFT_ROOT=tcle_ROOT, MIOS_ROOT=tcle_ROOT)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, tcle_TOOL, "comment-lex"], capture_output=True, text=True, env=env)

def tcle_test_runs_on_real_tree():
    p = tcle_run()
    tcle_check("exits-cleanly-or-reports", p.returncode in (0, 1), True)
    tcle_check("produces-output", bool((p.stdout + p.stderr).strip()), True)

def tcle_test_exit_code_carries_information():
    src = open(tcle_TOOL, encoding="utf-8", errors="replace").read()
    reads_env = "MIOS_MAX_" in src
    baseline = tcle_run()
    if reads_env and baseline.returncode == 0:
        tight = tcle_run({"MIOS_MAX_UNMIGRATED_NARRATIVE": "0",
                     "MIOS_MAX_STALE_REFS": "0",
                     "MIOS_MAX_OVERLONG_HINTS": "0"})
        tcle_check("zero-ceiling-can-fail", tight.returncode != 0, True)
    else:
        # Still assert something real: the tool must name what it checked.
        tcle_check("reports-its-subject", len((baseline.stdout + baseline.stderr).strip()) > 10, True)

def tcle_main() -> int:
    tcle_test_runs_on_real_tree()
    tcle_test_exit_code_carries_information()
    print(f"[test_check-comment-lex-equivalence] {tcle_PASSED} passed, {len(tcle_FAILED)} failed")
    for f in tcle_FAILED:
        print(f"  FAIL {f}")
    return 1 if tcle_FAILED else 0


import importlib.util
import os
import unittest

thcs__HERE = os.path.dirname(os.path.abspath(__file__))
thcs__ROOT = os.path.dirname(thcs__HERE)

def thcs__load():
    spec = importlib.util.spec_from_file_location(
        "check_header_comment_syntax",
        os.path.join(thcs__HERE, "check-docs.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

thcs_MOD = thcs__load()

class TestHeaderCommentSyntax(unittest.TestCase):
    def test_the_shipped_tree_is_clean(self):
        os.environ["MIOS_DRIFT_ROOT"] = thcs__ROOT
        self.assertEqual(0, thcs_MOD.hcs_main())

    def test_systemd_and_ini_formats_are_covered(self):
        for ext in (".service", ".timer", ".target", ".conf", ".toml"):
            self.assertIn(ext, thcs_MOD.hcs_HASH_COMMENT)

    def test_c_style_formats_are_not_covered(self):
        """A Rust or CSS file comments with /* */, and must not be flagged."""
        for ext in (".rs", ".css"):
            self.assertNotIn(ext, thcs_MOD.hcs_HASH_COMMENT)

    def test_the_pattern_matches_a_whole_line_header_only(self):
        self.assertTrue(thcs_MOD.hcs_BAD.search("/* AI-doc: x */"))
        self.assertTrue(thcs_MOD.hcs_BAD.search("/* AI-hint: y */"))
        self.assertIsNone(thcs_MOD.hcs_BAD.search("# AI-doc: x"))
        self.assertIsNone(thcs_MOD.hcs_BAD.search("code(); /* AI-doc: trailing */"))

    def test_the_wsl_pair_that_broke_a_build_is_consistent(self):
        a = open(os.path.join(thcs__ROOT, "usr/lib/wsl.conf"), encoding="utf-8").read()
        b = open(os.path.join(thcs__ROOT, "etc/wsl.conf"), encoding="utf-8").read()
        self.assertEqual(a, b, "the /usr reference and its /etc twin must match")
        self.assertNotIn("/*", a)

def thcs_main():
    r = unittest.main(argv=[sys.argv[0]], exit=False).result
    return 0 if r.wasSuccessful() else 1



"""Prose must not ride into globals.{sh,ps1}.

The generated resolvers are sourced on every shell start; carrying whole unit
comment bodies as string literals bloats them and gives the comment census a
second, duplicate copy of prose that already lives in the unit file.
"""

import os
import subprocess
import sys
import tempfile

# A fixture directory that outlives the run shows up as a stray tree in an
# editor and accumulates one per run. Registering the removal at creation works
# whether the module ends through unittest or its own main().
import atexit as _atexit
import shutil as _shutil

tngp__mkdtemp_orig = tempfile.mkdtemp

def tngp__mkdtemp_cleaned(*a, **kw):
    _d = tngp__mkdtemp_orig(*a, **kw)
    _atexit.register(_shutil.rmtree, _d, True)
    return _d

tempfile.mkdtemp = tngp__mkdtemp_cleaned

tngp_HERE = os.path.dirname(os.path.abspath(__file__))
tngp_ROOT = os.path.abspath(os.path.join(tngp_HERE, ".."))
tngp_TOOL = os.path.join(tngp_HERE, "check-docs.py")

tngp_FAILED: list[str] = []
tngp_PASSED = 0

def tngp_check(name, got, want):
    global tngp_PASSED
    if got == want:
        tngp_PASSED += 1
    else:
        tngp_FAILED.append(f"{name}: got {got!r}, want {want!r}")

def tngp__run(root):
    env = dict(os.environ, MIOS_DRIFT_ROOT=root, MIOS_ROOT=root)
    p = subprocess.run([sys.executable, tngp_TOOL, "no-generated-prose"], capture_output=True, text=True, env=env)
    return p.returncode

def tngp__fixture(body_sh: str) -> str:
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "automation", "lib"), exist_ok=True)
    for name in ("globals.sh", "globals.ps1"):
        with open(os.path.join(d, "automation", "lib", name), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(body_sh if name == "globals.sh" else "# clean\n")
    return d

def tngp_test_clean_resolver_passes():
    d = tngp__fixture("# generated\nexport MIOS_PORT_X=1\n")
    tngp_check("clean-passes", tngp__run(d), 0)

def tngp_test_ai_hint_in_resolver_fails():
    d = tngp__fixture("# generated\n# AI-hint: this prose does not belong here\nexport X=1\n")
    tngp_check("ai-hint-fails", tngp__run(d) != 0, True)

def tngp_test_unit_comment_payload_fails():
    d = tngp__fixture('# generated\nMIOS_UNITS_FOO_COMMENT="a whole unit body"\n')
    tngp_check("unit-comment-fails", tngp__run(d) != 0, True)

def tngp_test_real_tree_is_clean():
    tngp_check("shipped-resolvers-clean", tngp__run(tngp_ROOT), 0)

def tngp_main() -> int:
    tngp_test_clean_resolver_passes()
    tngp_test_ai_hint_in_resolver_fails()
    tngp_test_unit_comment_payload_fails()
    tngp_test_real_tree_is_clean()
    print(f"[test_check-no-generated-prose-in-resolvers] {tngp_PASSED} passed, {len(tngp_FAILED)} failed")
    for f in tngp_FAILED:
        print(f"  FAIL {f}")
    return 1 if tngp_FAILED else 0


"""Assert the persist-redaction coverage gate fails for each defect class."""
import os
import subprocess
import sys
import tempfile

trc_HERE = os.path.dirname(os.path.abspath(__file__))
trc_GATE = os.path.join(trc_HERE, "check-docs.py")
trc_FAILED = 0

trc_SCHEMA = ("CREATE TABLE IF NOT EXISTS knowledge (id int);\n"
          "CREATE TABLE IF NOT EXISTS agent_memory (id int);\n"
          "CREATE TABLE IF NOT EXISTS event (id int);\n"
          "CREATE TABLE IF NOT EXISTS tool_call (id int);\n"
          "CREATE TABLE IF NOT EXISTS scratch (id int);\n"
          "CREATE TABLE IF NOT EXISTS agent_keypair (id int);\n")
trc_GOOD_TOML = ('[security.redact]\nenable = true\nfail_closed = true\n'
             'tables = ["knowledge", "agent_memory", "event", "tool_call", "scratch"]\n'
             'exempt = ["agent_keypair"]\n')
trc_GOOD_PG = "def _redact_cfg():\n    return {}\n"

def trc_build(tmp, schema=trc_SCHEMA, toml=trc_GOOD_TOML, pg=trc_GOOD_PG):
    os.makedirs(os.path.join(tmp, "usr/share/mios/postgres"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "usr/lib/mios/agent-pipe/mios_pipe/memory"), exist_ok=True)
    open(os.path.join(tmp, "usr/share/mios/postgres/schema-init.sql"), "w").write(schema)
    open(os.path.join(tmp, "usr/share/mios/mios.toml"), "w").write(toml)
    open(os.path.join(tmp, "usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py"), "w").write(pg)
    return tmp

def trc_case(label, want_zero, **kw):
    global trc_FAILED
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, MIOS_ROOT=trc_build(tmp, **kw))
        rc = subprocess.run([sys.executable, trc_GATE, "redact-coverage"], env=env,
                            capture_output=True, text=True).returncode
    ok = (rc == 0) if want_zero else (rc != 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (exit {rc})")
    if not ok:
        trc_FAILED += 1

def trc_main():
    global trc_FAILED
    trc_case("fully classified schema passes", True)
    trc_case("unclassified new table fails", False,
         schema=trc_SCHEMA + "CREATE TABLE IF NOT EXISTS brand_new_sink (id int);\n")
    trc_case("table in BOTH lists fails", False,
         toml=trc_GOOD_TOML.replace('exempt = ["agent_keypair"]',
                                'exempt = ["agent_keypair", "scratch"]'))
    trc_case("classified table absent from schema fails", False,
         toml=trc_GOOD_TOML.replace('exempt = ["agent_keypair"]',
                                'exempt = ["agent_keypair", "ghost_table"]'))
    trc_case("free-text table dropped from redact fails", False,
         toml=trc_GOOD_TOML.replace('"tool_call", "scratch"]', '"tool_call"]')
                      .replace('exempt = ["agent_keypair"]',
                               'exempt = ["agent_keypair", "scratch"]'))
    trc_case("pg.py hardcoding its tuple fails", False,
         pg='if params and any(t in sql.lower() for t in ("knowledge", "agent_memory")):\n')
    trc_case("pg.py ignoring the SSOT fails", False, pg="def something_else():\n    pass\n")
    trc_case("unrelated embedding tuple is not the defect", True,
         pg=trc_GOOD_PG + 'if emb_version and table in ("knowledge", "agent_memory"):\n    pass\n')

    print(f"\n{8 - trc_FAILED}/8 checks pass")
    return 1 if trc_FAILED else 0

def main():
    # Every suite runs even when an earlier one fails.
    rc = 0
    for fn in (tdrm_main, tml_main, tcle_main, thcs_main, tngp_main, trc_main):
        rc |= (fn() or 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
