#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-temp-fixture-cleanup.py; proves it names a test that makes a temp directory and never removes it.
# AI-related: tools/check-temp-fixture-cleanup.py
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_temp_fixture_cleanup",
        os.path.join(_HERE, "check-temp-fixture-cleanup.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


class TestCleanupGate(unittest.TestCase):
    def test_the_markers_cover_the_common_idioms(self):
        for m in ("rmtree", "TemporaryDirectory", "addCleanup"):
            self.assertIn(m, MOD.MARKERS)

    def test_the_shipped_tree_is_clean(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT
        self.assertEqual(0, MOD.main())

    def test_every_test_that_makes_a_temp_dir_declares_a_cleanup(self):
        """The gate's own claim, restated where a reader can see it fail."""
        import subprocess
        out = subprocess.run(["git", "-C", _ROOT, "ls-files",
                              "tools/test_*.py", "tests/*.py",
                              "usr/lib/mios/agent-pipe/test_*.py"],
                             capture_output=True, text=True, check=False).stdout
        for rel in (p.strip() for p in out.splitlines() if p.strip()):
            full = os.path.join(_ROOT, rel)
            try:
                s = open(full, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if MOD.MAKER in s and not rel.endswith("check-temp-fixture-cleanup.py"):
                self.assertTrue(any(m in s for m in MOD.MARKERS), rel)


if __name__ == "__main__":
    unittest.main(verbosity=1)
