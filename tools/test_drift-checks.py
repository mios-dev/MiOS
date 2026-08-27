#!/usr/bin/env python3
# AI-hint: Sibling test for tools/drift-checks.py; asserts each extracted check is importable, dispatchable and agrees with the shell gate.
# AI-related: tools/drift-checks.py, automation/98-drift-checks.sh
"""These three checks used to be heredocs, where a syntax error surfaced only
when the check ran and nothing could lint them. The point of the extraction is
that they are now reachable from a test, so this asserts exactly that.
"""
import importlib.util
import os
import subprocess
import sys
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

if __name__ == "__main__":
    unittest.main(verbosity=1)
