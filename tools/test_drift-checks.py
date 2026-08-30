#!/usr/bin/env python3
# AI-hint: Sibling test for tools/drift-checks.py; asserts each extracted check is importable, dispatchable and agrees with the shell gate.
# AI-related: tools/drift-checks.py, automation/98-drift-checks.sh
"""These three checks used to be heredocs, where a syntax error surfaced only
when the check ran and nothing could lint them. The point of the extraction is
that they are now reachable from a test, so this asserts exactly that.
"""
import ast
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_MOD_PATH = os.path.join(_HERE, "drift-checks.py")

def _load():
    spec = importlib.util.spec_from_file_location("drift_checks", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

MOD = _load()

class TestExtractedChecks(unittest.TestCase):
    def test_the_module_imports(self):
        """A heredoc could not be imported at all; that was the defect."""
        self.assertTrue(callable(MOD.check_doc_refs_resolve))

    def test_every_subcommand_maps_to_a_callable(self):
        # Not a fixed count: the module grows as more checks leave their
        # heredocs, and asserting the number only breaks the test when the
        # extraction it exists to encourage actually happens.
        self.assertGreaterEqual(len(MOD.SUBCOMMANDS), 3)
        for name, fn in MOD.SUBCOMMANDS.items():
            self.assertTrue(callable(fn), name)
            self.assertNotIn("_", name, "subcommands are hyphenated: %s" % name)

    def test_an_unknown_subcommand_exits_two(self):
        r = subprocess.run([sys.executable, _MOD_PATH, "no-such-check"],
                           capture_output=True, text=True, cwd=_ROOT)
        self.assertEqual(2, r.returncode)

    def test_no_subcommand_exits_two(self):
        r = subprocess.run([sys.executable, _MOD_PATH],
                           capture_output=True, text=True, cwd=_ROOT)
        self.assertEqual(2, r.returncode)

    def test_each_check_runs_against_the_shipped_tree(self):
        env = dict(os.environ, MIOS_DRIFT_ROOT=_ROOT, MIOS_ROOT=_ROOT)
        for name in MOD.SUBCOMMANDS:
            r = subprocess.run([sys.executable, _MOD_PATH, name],
                               capture_output=True, text=True, cwd=_ROOT, env=env)
            if r.returncode == 0:
                continue
            # A check whose input tool cannot execute on THIS host must still
            # report that as a violation rather than crash. Asserting a bare 0
            # made the test depend on the host: mios-env-snapshot's shebang
            # does not resolve on Windows, so the check correctly reports a
            # missing input there while passing on Linux.
            # Non-zero has two legitimate causes and one illegitimate one.
            # Legitimate: the check found a real violation, or its input tool
            # cannot execute on THIS host (mios-env-snapshot's shebang does not
            # resolve on Windows) -- both are the check REPORTING. Illegitimate:
            # it crashed, or it exited non-zero saying nothing at all, which is
            # indistinguishable from a pass to anyone reading the log.
            #
            # Requiring a specific phrase here was wrong: it made a check that
            # correctly reported a real legibility violation look like a broken
            # check, because the violation text does not say "missing".
            out = (r.stdout or "") + (r.stderr or "")
            self.assertNotIn("Traceback", out,
                             "%s crashed instead of reporting" % name)
            self.assertTrue(
                out.strip(),
                "%s exited %d silently -- a non-zero exit with no diagnostic "
                "cannot be acted on" % (name, r.returncode))

    def test_the_shell_gate_calls_the_module_not_a_heredoc(self):
        with open(os.path.join(_ROOT, "automation/98-drift-checks.sh"), encoding="utf-8", errors="replace") as fh:
            gate = fh.read()
        for name in MOD.SUBCOMMANDS:
            self.assertIn("tools/drift-checks.py %s" % name, gate,
                          "check_%s no longer dispatches to the module"
                          % name.replace("-", "_"))


# A checkout that never had a file is a skip; a TRACKED file that has gone
# missing is the gate's own subject disappearing, and nineteen checks answered
# that with a silent 0.
_BOOTSTRAP_EXEMPT = "check_templates_bootstrap_sync"

class TestMissingDeliverable(unittest.TestCase):
    def _repo(self, rel, track=True):
        d = tempfile.mkdtemp(prefix="absent-")
        self.addCleanup(shutil.rmtree, d, True)
        full = os.path.join(d, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w").write("x\n")
        subprocess.run(["git", "-C", d, "init", "-q"], check=True)
        if track:
            subprocess.run(["git", "-C", d, "add", "-A"], check=True,
                           capture_output=True)
        return d, full

    def test_a_present_file_is_not_a_verdict(self):
        d, full = self._repo("usr/share/mios/mios.toml")
        self.assertIsNone(MOD._absent(d, full))

    def test_a_tracked_file_that_went_missing_fails(self):
        d, full = self._repo("usr/share/mios/mios.toml")
        os.remove(full)
        self.assertEqual(1, MOD._absent(d, full))

    def test_an_untracked_missing_file_still_skips(self):
        d, full = self._repo("usr/share/mios/mios.toml", track=False)
        os.remove(full)
        self.assertEqual(0, MOD._absent(d, full))

    def test_a_root_that_is_not_a_checkout_still_skips(self):
        """Fixture roots are bare temp directories, not repositories."""
        d = tempfile.mkdtemp(prefix="absent-plain-")
        self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(0, MOD._absent(d, os.path.join(d, "nothing/here.toml")))

    def test_no_check_still_answers_a_missing_subject_with_a_bare_zero(self):
        with open(_MOD_PATH, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        offenders, seen = [], 0
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("check_"):
                continue
            seen += 1
            if fn.name == _BOOTSTRAP_EXEMPT:
                continue        # reads the sibling repo, which a clone need not have
            for node in ast.walk(fn):
                if not isinstance(node, ast.If):
                    continue
                t = node.test
                if not (isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not)):
                    continue
                c = t.operand
                if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                        and c.func.attr in ("isfile", "isdir", "exists")):
                    continue
                if len(node.body) != 1:
                    continue
                s = node.body[0]
                bare = (isinstance(s, ast.Return) and isinstance(s.value, ast.Constant)
                        and type(s.value.value) is int and s.value.value == 0)
                if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
                    f = s.value.func
                    if isinstance(f, ast.Attribute) and f.attr == "exit" and s.value.args:
                        a = s.value.args[0]
                        bare = (isinstance(a, ast.Constant)
                                and type(a.value) is int and a.value == 0)
                if bare:
                    offenders.append("%s:%d" % (fn.name, node.lineno))
        self.assertGreater(seen, 50, "the module did not parse into checks")
        self.assertEqual([], offenders,
                         "route these through _absent(root, path)")

if __name__ == "__main__":
    unittest.main(verbosity=1)
