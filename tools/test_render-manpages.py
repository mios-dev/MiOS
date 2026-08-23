#!/usr/bin/env python3
# AI-hint: Sibling test for tools/render-manpages.py; asserts the emitted roff is well-formed and that every declared verb gets a page.
# AI-related: tools/render-manpages.py, usr/share/mios/mios.toml
"""A malformed man page fails at the reader, not at build time.

roff is forgiving: a stray leading dot silently swallows a line, so a page can
install cleanly and render wrong. These cases assert the structure man(1)
depends on, and that the page set tracks the verb list rather than drifting
from it.
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
KNOWN = {".TH", ".SH", ".SS", ".B", ".I", ".BR", ".IR", ".TP", ".PP",
         ".LP", ".br", ".nf", ".fi", ".RS", ".RE", ".sp", ".IP"}


def _load():
    spec = importlib.util.spec_from_file_location(
        "render_manpages", os.path.join(_HERE, "render-manpages.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def _ssot():
    import tomllib
    with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
        return tomllib.load(fh)


class TestRoffEscaping(unittest.TestCase):
    def test_a_leading_dot_is_neutralised(self):
        """Unescaped, roff reads the line as a request and drops the text."""
        self.assertTrue(MOD.roff(".hidden").startswith(chr(92) + "&"))

    def test_a_leading_apostrophe_is_neutralised(self):
        self.assertTrue(MOD.roff(chr(39) + "quoted").startswith(chr(92) + "&"))

    def test_a_backslash_is_escaped(self):
        self.assertNotIn(chr(92) + "n", MOD.roff(chr(92) + "n"))

    def test_a_hyphen_becomes_a_minus(self):
        self.assertIn(chr(92) + "-", MOD.roff("well-formed"))

    def test_plain_prose_is_untouched(self):
        self.assertEqual("plain words here", MOD.roff("plain words here"))


class TestPages(unittest.TestCase):
    def setUp(self):
        self.pages = MOD.pages(_ROOT, _ssot())

    def test_every_declared_verb_has_a_page(self):
        verbs = (_ssot().get("verbs") or {})
        for name in verbs:
            self.assertIn("usr/share/man/man1/mios-%s.1" % name, self.pages, name)

    def test_the_index_the_config_and_the_concept_page_exist(self):
        for rel in ("usr/share/man/man1/mios.1",
                    "usr/share/man/man5/mios.toml.5",
                    "usr/share/man/man7/mios.7"):
            self.assertIn(rel, self.pages, rel)

    def test_every_page_opens_with_TH_and_has_a_NAME(self):
        for rel, body in self.pages.items():
            lines = body.split(chr(10))
            self.assertTrue(lines[0].startswith(".TH "), rel)
            self.assertIn(".SH NAME", lines, rel)

    def test_no_page_emits_an_unknown_roff_request(self):
        for rel, body in self.pages.items():
            for k, line in enumerate(body.split(chr(10))):
                if line.startswith("."):
                    self.assertIn(line.split(" ")[0], KNOWN,
                                  "%s line %d: %s" % (rel, k + 1, line[:40]))

    def test_no_page_carries_a_date(self):
        """A date makes two builds of one tree differ, and Law 7 rejects it."""
        import re
        for rel, body in self.pages.items():
            self.assertIsNone(re.search(r"\b20\d{2}-\d{2}-\d{2}\b", body), rel)

    def test_rendering_is_deterministic(self):
        self.assertEqual(self.pages, MOD.pages(_ROOT, _ssot()))

    def test_the_shipped_tree_matches_what_the_renderer_emits(self):
        for rel, body in self.pages.items():
            full = os.path.join(_ROOT, rel)
            self.assertTrue(os.path.isfile(full), "%s is not shipped" % rel)
            with open(full, encoding="utf-8") as fh:
                self.assertEqual(body, fh.read(), "%s is stale" % rel)


if __name__ == "__main__":
    unittest.main(verbosity=1)
