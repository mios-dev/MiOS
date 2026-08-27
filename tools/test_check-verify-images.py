#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-verify-images.py; asserts the gate drives the real verifier rather than restating its result.
# AI-related: tools/check-verify-images.py, tools/verify-images.py, Justfile
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

def _load():
    spec = importlib.util.spec_from_file_location(
        "check_verify_images", os.path.join(_HERE, "check-verify-images.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

MOD = _load()

class TestCheckVerifyImages(unittest.TestCase):
    def setUp(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT

    def test_the_shipped_tree_passes(self):
        self.assertEqual(0, MOD.main() if MOD.main.__code__.co_argcount == 0 else MOD.main([]))

    def test_the_recipe_still_delegates_to_the_verifier(self):
        """A recipe that stops calling the script is the regression to catch."""
        just = open(os.path.join(_ROOT, "Justfile"), encoding="utf-8", errors="replace").read()
        self.assertIn("tools/verify-images.py", just)

    def test_publish_still_depends_on_verify_images(self):
        just = open(os.path.join(_ROOT, "Justfile"), encoding="utf-8", errors="replace").read()
        line = [l for l in just.split(chr(10)) if l.startswith("publish:")]
        self.assertTrue(line, "no publish recipe")
        self.assertIn("verify-images", line[0])

if __name__ == "__main__":
    unittest.main(verbosity=1)
