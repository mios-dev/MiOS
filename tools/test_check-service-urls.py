#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-service-urls.py. Cover the four ways a port's addressing can be wrong -- unclassified, double-classified, a register entry naming a port that does not exist, and a duplicated register entry -- plus the empty-set case, because a gate that passes over no ports is the failure this whole family of gates exists to prevent.
# AI-related: tools/check-service-urls.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh
"""Tests for the one-canonical-address-per-service gate."""

import os
import sys
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_service_urls", os.path.join(_HERE, "check-service-urls.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def data(ports=None, urls=None, register=None):
    d = {"ports": dict(ports or {}), "urls": dict(urls or {})}
    if register is not None:
        d["urls"]["non_addressable"] = list(register)
    return d


class TestPortKeys(unittest.TestCase):
    def test_stack_id_is_not_a_port(self):
        self.assertEqual(mod.port_keys(data({"a": 1, "stack_id": 0})), {"a"})

    def test_non_numeric_is_not_a_port(self):
        self.assertEqual(mod.port_keys(data({"a": 1, "categories": {}})), {"a"})


class TestCovered(unittest.TestCase):
    def test_templated_port_is_covered(self):
        d = data({"forge_http": 8400}, {"forge": "http://x:${MIOS_PORT_FORGE_HTTP}"})
        self.assertEqual(mod.covered_ports(d), {"forge_http"})

    def test_one_url_may_cover_several_ports(self):
        d = data({"a": 1, "b": 2}, {"u": "${MIOS_PORT_A}/${MIOS_PORT_B}"})
        self.assertEqual(mod.covered_ports(d), {"a", "b"})

    def test_literal_port_number_does_not_count_as_covered(self):
        # A literal is exactly the hardcoding the gate wants replaced.
        d = data({"forge_http": 8400}, {"forge": "http://x:8400"})
        self.assertEqual(mod.covered_ports(d), set())

    def test_register_list_is_not_scanned_as_a_url(self):
        d = data({"a": 1}, {}, ["a"])
        self.assertEqual(mod.covered_ports(d), set())


class TestClassify(unittest.TestCase):
    def test_clean_tree_has_no_violations(self):
        d = data({"a": 1, "b": 2}, {"u": "http://x:${MIOS_PORT_A}"}, ["b"])
        self.assertEqual(mod.classify(d), [])

    def test_unclassified_port_fails(self):
        d = data({"a": 1, "b": 2}, {"u": "http://x:${MIOS_PORT_A}"}, [])
        self.assertEqual(len(mod.classify(d)), 1)
        self.assertIn("'b'", mod.classify(d)[0])

    def test_port_in_both_fails(self):
        d = data({"a": 1}, {"u": "http://x:${MIOS_PORT_A}"}, ["a"])
        self.assertIn("two answers", mod.classify(d)[0])

    def test_register_naming_a_missing_port_fails(self):
        d = data({"a": 1}, {"u": "http://x:${MIOS_PORT_A}"}, ["ghost"])
        self.assertIn("not a [ports] key", mod.classify(d)[0])

    def test_duplicate_register_entry_fails(self):
        d = data({"a": 1, "b": 2}, {"u": "http://x:${MIOS_PORT_A}"}, ["b", "b"])
        self.assertIn("twice", mod.classify(d)[0])

    def test_empty_port_table_fails_rather_than_passing_vacuously(self):
        self.assertIn("vacuously", mod.classify(data({}, {}, []))[0])

    def test_register_whitespace_and_blanks_are_ignored(self):
        d = data({"a": 1, "b": 2}, {"u": "${MIOS_PORT_A}"}, [" b ", "", "  "])
        self.assertEqual(mod.classify(d), [])


class TestShippedTree(unittest.TestCase):
    def test_the_real_ssot_classifies_every_port(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            real = tomllib.load(fh)
        self.assertEqual(mod.classify(real), [])

    def test_every_register_entry_is_a_real_port(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            real = tomllib.load(fh)
        self.assertTrue(set(mod.register(real)) <= mod.port_keys(real))

    def test_the_register_is_not_empty_yet(self):
        # Guards the test itself: if the register ever empties, these assertions
        # stop proving anything and this line is the reminder to delete them.
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            real = tomllib.load(fh)
        self.assertGreater(len(mod.register(real)), 0)


class TestBrowserOpenable(unittest.TestCase):
    """[urls] is what a person clicks -- one meaning, not two."""

    def test_an_http_entry_is_clean(self):
        self.assertEqual(mod.browser_openable(
            {"urls": {"forge": "http://localhost:${MIOS_PORT_FORGE_HTTP}"}}), [])

    def test_an_https_entry_is_clean(self):
        self.assertEqual(mod.browser_openable(
            {"urls": {"cockpit": "https://localhost:${MIOS_PORT_COCKPIT}"}}), [])

    def test_a_dsn_fails(self):
        # [urls].pgvector shipped as a postgresql:// DSN, which made the table
        # mean both "a tile" and "an inter-service address".
        out = mod.browser_openable(
            {"urls": {"pgvector": "postgresql://mios@localhost:8600/mios"}})
        self.assertTrue(out)
        self.assertIn("postgresql", out[0])

    def test_a_non_url_fails(self):
        self.assertTrue(mod.browser_openable({"urls": {"x": "localhost:8600"}}))

    def test_the_register_list_is_not_treated_as_a_url(self):
        self.assertEqual(mod.browser_openable(
            {"urls": {"non_addressable": ["a", "b"]}}), [])

    def test_the_shipped_table_is_browser_openable(self):
        import os
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            self.assertEqual(mod.browser_openable(tomllib.load(fh)), [])


class TestBarePortAddresses(unittest.TestCase):
    """An address an /etc/mios overlay cannot move is a service that can never
    be offloaded -- which is the whole of MiOS-Mini."""

    def test_a_bare_port_localhost_url_fails(self):
        out = mod.bare_port_addresses(
            {"ports": {"llm_light": 8500},
             "ai": {"endpoint": "http://localhost:8500/v1"}})
        self.assertTrue(out)
        self.assertIn("MIOS_PORT_LLM_LIGHT", out[0])

    def test_the_loopback_spelling_is_caught_too(self):
        self.assertTrue(mod.bare_port_addresses(
            {"ports": {"crawl4ai": 8810},
             "x": {"y": "http://127.0.0.1:8810/crawl"}}))

    def test_a_templated_url_is_clean(self):
        self.assertEqual(mod.bare_port_addresses(
            {"ports": {"llm_light": 8500},
             "ai": {"endpoint": "http://localhost:${MIOS_PORT_LLM_LIGHT}/v1"}}), [])

    def test_a_port_that_is_not_ours_is_ignored(self):
        self.assertEqual(mod.bare_port_addresses(
            {"ports": {"llm_light": 8500},
             "x": {"y": "http://localhost:9999/"}}), [])

    def test_rendered_unit_bodies_are_out_of_scope(self):
        # units/containers carry ${VAR:-N} defaults by design; check_port_fallbacks
        # owns those, and double-owning would make both registers lie.
        self.assertEqual(mod.bare_port_addresses(
            {"ports": {"llm_light": 8500},
             "units": {"x.service": {"Service": {"Exec": "--listen :8500"}}}}), [])

    def test_a_non_local_host_is_not_this_rule(self):
        self.assertEqual(mod.bare_port_addresses(
            {"ports": {"llm_light": 8500},
             "x": {"y": "http://blade-01:8500/v1"}}), [])

    def test_the_shipped_tree_has_no_unmovable_address(self):
        import os
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            self.assertEqual(mod.bare_port_addresses(tomllib.load(fh)), [])


if __name__ == "__main__":
    unittest.main()
