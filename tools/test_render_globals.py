#!/usr/bin/env python3
# AI-hint: Unit tests for render-globals.py -- proves shell and PowerShell constants are escaped so the generated resolvers always parse, that ${MIOS_X...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_render_globals_py.md

import importlib.util
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "render_globals", os.path.join(_HERE, "render-globals.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rg = load_module()


class TestShAssign(unittest.TestCase):
    def test_simple_value_uses_the_idiomatic_form(self):
        # several drift checks parse this exact shape out of globals.sh
        self.assertEqual(rg._sh_assign("MIOS_PORT_SSH", "8100"),
                         ': "${MIOS_PORT_SSH:=8100}"')

    def test_value_with_a_brace_avoids_the_expansion_form(self):
        # a `}` would close ${VAR:= early and break the whole file
        out = rg._sh_assign("MIOS_MSG", "hello {name}")
        self.assertNotIn(":=", out)
        self.assertIn("MIOS_MSG+x", out)

    def test_value_with_an_apostrophe_is_quoted_safely(self):
        # "the operator's phone" previously produced an unterminated quote
        out = rg._sh_assign("MIOS_JOB", "the operator's phone")
        self.assertNotIn(":=", out)
        self.assertIn("""'"'"'""", out)

    def test_template_stays_live(self):
        out = rg._sh_assign("MIOS_FORGE_URL",
                            "http://localhost:${MIOS_PORT_FORGE_HTTP}")
        self.assertIn('"${MIOS_PORT_FORGE_HTTP}"', out)

    def test_assignment_is_conditional_so_env_wins(self):
        for value in ("8100", "has }brace", "has 'quote"):
            out = rg._sh_assign("MIOS_X", value)
            self.assertTrue(":=" in out or "+x" in out, out)


class TestPsAssign(unittest.TestCase):
    def test_numeric_is_emitted_bare(self):
        # check 28 parses `else { <digits> }`
        out = rg._ps_assign("MIOS_PORT_SSH", "8100")
        self.assertIn("else { 8100 }", out)

    def test_string_is_single_quoted(self):
        out = rg._ps_assign("MIOS_USER", "mios")
        self.assertIn("else { 'mios' }", out)

    def test_embedded_quote_is_doubled(self):
        out = rg._ps_assign("MIOS_JOB", "operator's phone")
        self.assertIn("''", out)

    def test_template_becomes_a_subexpression(self):
        out = rg._ps_assign("MIOS_FORGE_URL",
                            "http://localhost:${MIOS_PORT_FORGE_HTTP}")
        self.assertIn("$($script:MIOS_PORT_FORGE_HTTP)", out)

    def test_dollar_in_a_template_value_is_escaped(self):
        out = rg._ps_assign("MIOS_X", "a $literal and ${MIOS_PORT_SSH}")
        self.assertIn("`$literal", out)

    def test_env_override_still_wins(self):
        out = rg._ps_assign("MIOS_PORT_SSH", "8100")
        self.assertIn("if ($env:MIOS_PORT_SSH)", out)


class TestSanitize(unittest.TestCase):
    def test_illegal_identifier_characters_are_replaced(self):
        # a container key like mios-llm-worker@ produced MIOS_..._WORKER@_...
        # which is neither valid sh nor valid PowerShell
        self.assertEqual(rg._sanitize("MIOS_A@B-C.D"), "MIOS_A_B_C_D")

    def test_legal_name_is_untouched(self):
        self.assertEqual(rg._sanitize("MIOS_PORT_SSH"), "MIOS_PORT_SSH")


class TestOrdering(unittest.TestCase):
    def test_template_is_emitted_after_the_name_it_references(self):
        exports = {
            "MIOS_URLS_FORGE": "http://localhost:${MIOS_PORT_FORGE_HTTP}",
            "MIOS_PORT_FORGE_HTTP": "8400",
        }
        names = rg.ordered_names(exports)
        self.assertLess(names.index("MIOS_PORT_FORGE_HTTP"),
                        names.index("MIOS_URLS_FORGE"))


class TestExpandTemplate(unittest.TestCase):
    def test_shell_keeps_the_brace_form(self):
        self.assertEqual(rg.expand_template("a${MIOS_X}b", "sh"), "a${MIOS_X}b")

    def test_powershell_uses_script_scope(self):
        self.assertEqual(rg.expand_template("a${MIOS_X}b", "ps"),
                         "a$($script:MIOS_X)b")


class TestGeneratedFilesAreParseable(unittest.TestCase):
    def test_generated_sh_has_balanced_quoting(self):
        """Whole-file, not per-line: a value may legitimately be multi-line
        (e.g. MIOS_OWUI_SYSTEM_PROMPT_TEMPLATE), and single quotes span
        newlines in shell, so a per-line balance check false-alarms."""
        path = os.path.join(os.path.dirname(_HERE), "automation/lib/globals.sh")
        if not os.path.isfile(path):
            self.skipTest("globals.sh not generated in this tree")
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        stripped = body.replace("""'"'"'""", "")
        self.assertEqual(stripped.count("'") % 2, 0,
                         "globals.sh has an unbalanced single quote")

    def test_generated_ps1_uses_legal_identifiers(self):
        path = os.path.join(os.path.dirname(_HERE), "automation/lib/globals.ps1")
        if not os.path.isfile(path):
            self.skipTest("globals.ps1 not generated in this tree")
        with open(path, encoding="utf-8") as fh:
            names = re.findall(r"^\$script:([^\s=]+)\s*=", fh.read(), re.M)
        self.assertTrue(names, "no constants found in globals.ps1")
        for name in names:
            self.assertRegex(name, r"^[A-Za-z0-9_]+$",
                             f"illegal PowerShell identifier: {name}")


if __name__ == "__main__":
    unittest.main()
