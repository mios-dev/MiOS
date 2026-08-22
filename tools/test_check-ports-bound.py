#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-ports-bound.py. Cover the four ways an allocated port can be wrong -- unreferenced and unregistered, registered though it IS referenced (the register must only shrink), a register entry naming no real port, and a duplicated entry -- plus the empty-set case, because a gate that passes over no ports is the exact failure this family of gates exists to prevent.
# AI-related: tools/check-ports-bound.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh
"""Tests for the allocated-but-unbound port gate."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_ports_bound", os.path.join(_HERE, "check-ports-bound.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def data(ports=None, unbound=None):
    d = {"ports": dict(ports or {})}
    if unbound is not None:
        d["ports"]["unbound"] = list(unbound)
    return d


class TestPortKeys(unittest.TestCase):
    def test_stack_id_is_not_a_port(self):
        self.assertEqual(mod.port_keys(data({"a": 1, "stack_id": 0})), {"a"})

    def test_the_register_itself_is_not_a_port(self):
        self.assertEqual(mod.port_keys(data({"a": 1}, ["a"])), {"a"})


class TestClassify(unittest.TestCase):
    def test_referenced_port_is_clean(self):
        self.assertEqual(mod.classify(data({"a": 1}), {"a"}), [])

    def test_registered_and_unreferenced_is_clean(self):
        self.assertEqual(mod.classify(data({"a": 1}, ["a"]), set()), [])

    def test_unreferenced_and_unregistered_fails(self):
        v = mod.classify(data({"a": 1}), set())
        self.assertEqual(len(v), 1)
        self.assertIn("guards a number nothing binds", v[0])

    def test_register_only_shrinks(self):
        # Wired since it was registered -> the entry must be removed.
        v = mod.classify(data({"a": 1}, ["a"]), {"a"})
        self.assertIn("only shrinks", v[0])

    def test_register_naming_a_missing_port_fails(self):
        v = mod.classify(data({"a": 1}, ["ghost"]), {"a"})
        self.assertTrue(any("not a [ports] key" in x for x in v))

    def test_duplicate_register_entry_fails(self):
        v = mod.classify(data({"a": 1, "b": 2}, ["b", "b"]), {"a"})
        self.assertTrue(any("twice" in x for x in v))

    def test_empty_port_table_fails_rather_than_passing_vacuously(self):
        self.assertIn("vacuously", mod.classify(data({}, []), set())[0])

    def test_whitespace_entries_are_ignored(self):
        self.assertEqual(mod.classify(data({"a": 1, "b": 2}, [" b ", ""]), {"a"}), [])


class TestSkipSurfaces(unittest.TestCase):
    def test_ssot_and_docs_cannot_prove_a_binding(self):
        # A port mentioned only where ports are DESCRIBED is still unbound.
        for p in ("usr/share/mios/mios.toml", "usr/share/doc/mios/x.md",
                  "automation/lib/globals.sh", "TASKS.md", "ADR.md"):
            self.assertTrue(p.startswith(mod.SKIP_PREFIXES), p)

    def test_a_quadlet_is_not_skipped(self):
        for p in ("usr/share/containers/systemd/mios-guacd.container",
                  "usr/lib/systemd/system/mios-agent-pipe.service",
                  "usr/lib/mios/agent-pipe/server.py"):
            self.assertFalse(p.startswith(mod.SKIP_PREFIXES), p)


class TestShippedTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_real_ssot_accounts_for_every_port(self):
        ref = mod.referenced_ports(_ROOT, mod.port_keys(self.real))
        self.assertEqual(mod.classify(self.real, ref), [])

    def test_every_register_entry_is_a_real_port(self):
        self.assertTrue(set(mod.register(self.real)) <= mod.port_keys(self.real))

    def test_the_ports_that_were_wired_are_really_referenced(self):
        # The four T-318 drains: if any regresses, this fails before the gate does.
        ref = mod.referenced_ports(_ROOT, mod.port_keys(self.real))
        for k in ("guacd", "redis", "pxe_hub_api", "forge_ssh"):
            self.assertIn(k, ref, k)


if __name__ == "__main__":
    unittest.main()
