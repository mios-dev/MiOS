#!/usr/bin/env python3
# AI-hint: Sibling test for tools/ci-suites.py; proves the registry reader fails on the shapes it exists to catch.
# AI-related: tools/ci-suites.py, usr/share/mios/mios.toml
"""Each case is a mutation the checker must reject.

A checker that passes on a deliberately broken registry is the defect this
whole registry exists to prevent, so every assertion here is a red, not a green.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

def _load():
    spec = importlib.util.spec_from_file_location(
        "ci_suites", os.path.join(_HERE, "ci-suites.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

MOD = _load()

class TestRegistryReader(unittest.TestCase):
    def _ci(self, **over):
        base = {
            "max_exempt_suites": 1,
            "runners": ["tests/run-suites.sh"],
            "tiers": {"lint": ["automation/lint-json.sh"]},
            "globs": {},
            "exempt": {"tests/bake-smoke.sh": "takes an image reference"},
            "python": {"packages": ["pyflakes"]},
        }
        base.update(over)
        return base

    def test_a_ceiling_below_the_count_fails(self):
        ci = self._ci(exempt={"a": "r", "b": "r"}, max_exempt_suites=1)
        with tempfile.TemporaryDirectory() as d:
            self.assertNotEqual(0, MOD.cmd_check(d, ci))

    def test_an_absent_ceiling_fails(self):
        ci = self._ci()
        del ci["max_exempt_suites"]
        with tempfile.TemporaryDirectory() as d:
            self.assertNotEqual(0, MOD.cmd_check(d, ci))

    def test_an_exemption_without_a_reason_fails(self):
        ci = self._ci(exempt={"tests/x.sh": "   "})
        with tempfile.TemporaryDirectory() as d:
            self.assertNotEqual(0, MOD.cmd_check(d, ci))

    def test_a_suite_in_two_tiers_fails(self):
        ci = self._ci(tiers={"lint": ["automation/lint-json.sh"],
                             "gate": ["automation/lint-json.sh"]})
        with tempfile.TemporaryDirectory() as d:
            self.assertNotEqual(0, MOD.cmd_check(d, ci))

    def test_an_unknown_tier_is_not_silently_empty(self):
        self.assertEqual(2, MOD.cmd_list(_ROOT, self._ci(), "no-such-tier"))

    def test_the_shipped_registry_passes(self):
        ci = MOD._load(_ROOT)
        self.assertEqual(0, MOD.cmd_check(_ROOT, ci))

    def test_pip_arguments_carry_the_requirements_file(self):
        ci = MOD._load(_ROOT)
        reqs = (ci.get("python") or {}).get("requirements") or []
        self.assertTrue(reqs, "[ci.python].requirements is what stopped the "
                              "hand-written package list drifting from the code")
        for r in reqs:
            self.assertTrue(os.path.isfile(os.path.join(_ROOT, r)), r)

    @unittest.skipIf(os.name == "nt", "the shim is a POSIX shell script")
    def test_a_refusing_git_is_not_a_fully_registered_tree(self):
        """The corpus used to come back empty and the unregistered-suite
        direction retired itself, reporting the same success as a clean run."""
        shim = tempfile.mkdtemp(prefix="gitshim-")
        self.addCleanup(shutil.rmtree, shim, True)
        exe = os.path.join(shim, "git")
        with open(exe, "w") as fh:
            fh.write('#!/bin/sh\necho "fatal: detected dubious ownership" >&2\n'
                     'exit 128\n')
        os.chmod(exe, 0o755)
        old = os.environ["PATH"]
        os.environ["PATH"] = shim + os.pathsep + old
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = MOD.cmd_check(_ROOT, MOD._load(_ROOT))
        finally:
            os.environ["PATH"] = old
        self.assertNotEqual(0, rc)
        self.assertIn("cannot enumerate tracked suites", buf.getvalue())

    def test_every_registered_path_exists(self):
        ci = MOD._load(_ROOT)
        for path, tier in MOD._registered(_ROOT, ci).items():
            self.assertTrue(os.path.isfile(os.path.join(_ROOT, path)),
                            "%s (tier %s)" % (path, tier))

if __name__ == "__main__":
    unittest.main(verbosity=1)
