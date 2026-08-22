# AI-hint: !/usr/bin/env python3 Unit tests for tools/check-port-fallbacks.py.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_port_fallbacks_py.md
"""Tests for the port-literal gate."""

import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_port_fallbacks", os.path.join(_HERE, "check-port-fallbacks.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

DATA = {"ports": {"agent_pipe": 8700, "llm_light": 8500, "pgvector": 8600,
                  "arbiter": 8760}}


def tree(tmp, files, register=None):
    for rel, body in files.items():
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    d = {"ports": dict(DATA["ports"])}
    if register is not None:
        d["ports"]["stale_fallbacks"] = list(register)
    return d


class TestIdioms(unittest.TestCase):
    def _one(self, body, rel="usr/libexec/mios/probe"):
        with tempfile.TemporaryDirectory() as tmp:
            d = tree(tmp, {rel: body})
            return mod.findings(d, tmp)

    def test_an_unconditional_environment_pin_is_found(self):
        # The shape that made agent-pipe bind a retired port.
        f = self._one("Environment=MIOS_PORT_AGENT_PIPE=8640\n",
                      "usr/lib/systemd/system/x.service")
        self.assertIn("usr/lib/systemd/system/x.service:AGENT_PIPE", f)

    def test_a_shell_fallback_is_found(self):
        # 8450 is DELIBERATELY wrong -- [ports].llm_light is 8500. A fixture
        # carrying the CORRECT value produces no finding, so the assertion
        # would pass over nothing.
        self.assertTrue(self._one('P="${MIOS_PORT_LLM_LIGHT:-8450}"\n'))

    def test_a_python_get_default_is_found(self):
        self.assertTrue(self._one('p = os.environ.get("MIOS_PORT_LLM_LIGHT", "8450")\n'))

    def test_the_second_literal_of_a_double_fallback_is_found(self):
        # get(K, "correct") or WRONG -- the `or` is what runs when the var is
        # empty, and the first sweep of this gate missed it entirely.
        f = self._one('p = int(e.get("MIOS_PORT_PGVECTOR", "8600") or 8432)\n')
        self.assertIn("usr/libexec/mios/probe:PGVECTOR", f)

    def test_a_bare_or_fallback_is_found(self):
        self.assertTrue(self._one('p = os.environ.get("MIOS_PORT_LLM_LIGHT") or "8450"\n'))

    def test_the_powershell_table_shape_is_found(self):
        self.assertTrue(self._one("_MiosPort 'MIOS_PORT_LLM_LIGHT' 8450\n"))

    def test_the_alias_spelling_is_found(self):
        self.assertTrue(self._one('p = os.environ.get("MIOS_ARBITER_PORT", "8650")\n'))

    def test_an_agreeing_literal_is_not_a_finding(self):
        self.assertEqual(self._one('p = os.environ.get("MIOS_PORT_LLM_LIGHT", "8500")\n'), {})

    def test_a_templated_reference_is_not_a_finding(self):
        self.assertEqual(self._one('P="${MIOS_PORT_LLM_LIGHT}"\n'), {})

    def test_a_comment_is_never_a_finding(self):
        self.assertEqual(self._one('# MIOS_PORT_LLM_LIGHT used to be 8450\n'), {})

    def test_a_name_with_no_ports_key_is_ignored(self):
        self.assertEqual(self._one('p = os.environ.get("MIOS_PG_PORT", "5432")\n'), {})


class TestRegister(unittest.TestCase):
    def test_a_registered_finding_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = tree(tmp, {"usr/libexec/mios/probe": 'x = "${MIOS_PORT_LLM_LIGHT:-8450}"\n'},
                     register=["usr/libexec/mios/probe:LLM_LIGHT"])
            self.assertEqual(mod.classify(d, tmp), [])

    def test_an_unregistered_finding_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = tree(tmp, {"usr/libexec/mios/probe": 'x = "${MIOS_PORT_LLM_LIGHT:-8450}"\n'},
                     register=[])
            self.assertTrue(mod.classify(d, tmp))

    def test_the_register_only_shrinks(self):
        # An entry that no longer reproduces must be REMOVED, not left to rot.
        with tempfile.TemporaryDirectory() as tmp:
            d = tree(tmp, {"usr/libexec/mios/probe": "clean\n"},
                     register=["usr/libexec/mios/probe:LLM_LIGHT"])
            out = mod.classify(d, tmp)
            self.assertTrue(any("only shrinks" in v for v in out))

    def test_a_duplicated_register_entry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = tree(tmp, {"usr/libexec/mios/probe": 'x = "${MIOS_PORT_LLM_LIGHT:-8450}"\n'},
                     register=["usr/libexec/mios/probe:LLM_LIGHT"] * 2)
            self.assertTrue(any("twice" in v for v in mod.classify(d, tmp)))


class TestRealTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_shipped_tree_is_clean(self):
        self.assertEqual(mod.classify(self.real, _ROOT), [])

    def test_the_gate_actually_scans_something(self):
        # A gate that walks an empty set reports success over nothing.
        self.assertGreater(sum(1 for _ in mod.scan_paths(_ROOT)), 200)

    def test_the_register_is_drained_and_stays_drained(self):
        self.assertEqual(mod.register(self.real), [])


if __name__ == "__main__":
    unittest.main()
