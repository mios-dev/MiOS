#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-negatives-registered.py; proves it names a negative test the harness defines but never invokes.
# AI-related: tools/check-negatives-registered.py, tests/drift-gate-negatives.sh
import importlib.util
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

def _load():
    spec = importlib.util.spec_from_file_location(
        "check_negatives_registered",
        os.path.join(_HERE, "check-negatives-registered.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

MOD = _load()

class TestNegativesRegistered(unittest.TestCase):
    def test_the_shipped_harness_invokes_everything_it_defines(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT
        self.assertEqual(0, MOD.main())

    def test_the_harness_defines_a_substantial_number(self):
        """A harness that defines nothing would pass vacuously."""
        s = open(os.path.join(_ROOT, MOD.HARNESS), encoding="utf-8").read()
        self.assertGreater(len(set(re.findall(r"^(test_[a-z0-9_]+)\(\)", s, re.M))), 100)

    def test_an_unregistered_test_is_detected(self):
        """The regex pair is the whole gate; assert it separates the two sets."""
        s = "test_alpha() {\n:\n}\ntest_beta() {\n:\n}\n    _run_test test_alpha\n"
        defined = set(re.findall(r"^(test_[a-z0-9_]+)\(\)", s, re.M))
        invoked = set(re.findall(r"^\s*_run_test\s+(test_[a-z0-9_]+)\s*$", s, re.M))
        self.assertEqual({"test_beta"}, defined - invoked)

if __name__ == "__main__":
    unittest.main(verbosity=1)
