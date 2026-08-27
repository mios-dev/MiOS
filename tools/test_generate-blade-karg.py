#!/usr/bin/env python3
# AI-hint: Unit tests for tools/generate-blade-karg.py.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Tests for the deploy-time blade karg projection."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "generate_blade_karg", os.path.join(_HERE, "generate-blade-karg.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

def data(btype, archetypes=("hybrid", "endpoint")):
    return {"blade": {"type": btype,
                      "archetypes": {a: [] for a in archetypes}}}

class TestRender(unittest.TestCase):
    def test_emits_a_single_bare_kargs_array(self):
        body = mod.render(data("endpoint"))
        self.assertIn('kargs = [\n    "mios.blade=endpoint"\n]', body)
        # bootc rejects a table header here; the format is a bare array only.
        # Checked over EXECUTABLE lines: the header comment names [kargs] to
        # warn against it, and a naive substring check would trip on that.
        code = [l for l in body.splitlines() if not l.lstrip().startswith("#")]
        self.assertNotIn("[kargs]", "\n".join(code))

    def test_marks_itself_generated(self):
        self.assertIn("DO NOT EDIT", mod.render(data("hybrid")))

    def test_empty_type_is_refused(self):
        for bad in ("", "   ", None):
            with self.assertRaises(SystemExit):
                mod.render({"blade": {"type": bad, "archetypes": {"hybrid": []}}})

    def test_type_naming_no_archetype_is_refused(self):
        with self.assertRaises(SystemExit):
            mod.render(data("nosucharchetype"))

    def test_absent_blade_section_is_refused(self):
        with self.assertRaises(SystemExit):
            mod.render({})

class TestShippedTree(unittest.TestCase):
    def test_the_committed_karg_matches_the_ssot(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            real = tomllib.load(fh)
        with open(os.path.join(_ROOT, mod.TARGET), encoding="utf-8") as fh:
            on_disk = fh.read()
        self.assertEqual(on_disk, mod.render(real))

    def test_the_karg_names_the_declared_type(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            real = tomllib.load(fh)
        with open(os.path.join(_ROOT, mod.TARGET), encoding="utf-8") as fh:
            on_disk = fh.read()
        self.assertIn("mios.blade=%s" % real["blade"]["type"], on_disk)

    def test_the_reader_parses_the_token_this_file_emits(self):
        # The producer is only useful if the consumer reads the same spelling.
        # The reader moved into the shared resolver when role-apply and the
        # `mios blade` verb were made to share one implementation.
        with open(os.path.join(_ROOT, "usr/lib/mios/blade.sh"),
                  encoding="utf-8") as fh:
            lib = fh.read()
        self.assertIn("_cmdline_tok mios.blade", lib)
        self.assertIn('"${key}="*)', lib)
        with open(os.path.join(_ROOT, "usr/libexec/mios/role-apply"),
                  encoding="utf-8") as fh:
            self.assertIn("blade.sh", fh.read())

if __name__ == "__main__":
    unittest.main()
