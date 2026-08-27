#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-header-comment-syntax.py; proves it catches a C-style header in a hash-comment format.
# AI-related: tools/check-header-comment-syntax.py
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

def _load():
    spec = importlib.util.spec_from_file_location(
        "check_header_comment_syntax",
        os.path.join(_HERE, "check-header-comment-syntax.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

MOD = _load()

class TestHeaderCommentSyntax(unittest.TestCase):
    def test_the_shipped_tree_is_clean(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT
        self.assertEqual(0, MOD.main())

    def test_systemd_and_ini_formats_are_covered(self):
        for ext in (".service", ".timer", ".target", ".conf", ".toml"):
            self.assertIn(ext, MOD.HASH_COMMENT)

    def test_c_style_formats_are_not_covered(self):
        """A Rust or CSS file comments with /* */, and must not be flagged."""
        for ext in (".rs", ".css"):
            self.assertNotIn(ext, MOD.HASH_COMMENT)

    def test_the_pattern_matches_a_whole_line_header_only(self):
        self.assertTrue(MOD.BAD.search("/* AI-doc: x */"))
        self.assertTrue(MOD.BAD.search("/* AI-hint: y */"))
        self.assertIsNone(MOD.BAD.search("# AI-doc: x"))
        self.assertIsNone(MOD.BAD.search("code(); /* AI-doc: trailing */"))

    def test_the_wsl_pair_that_broke_a_build_is_consistent(self):
        a = open(os.path.join(_ROOT, "usr/lib/wsl.conf"), encoding="utf-8").read()
        b = open(os.path.join(_ROOT, "etc/wsl.conf"), encoding="utf-8").read()
        self.assertEqual(a, b, "the /usr reference and its /etc twin must match")
        self.assertNotIn("/*", a)

if __name__ == "__main__":
    unittest.main(verbosity=1)
