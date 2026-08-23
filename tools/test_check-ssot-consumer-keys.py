#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-ssot-consumer-keys.py.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_ssot_consumer_keys_py.md
"""Tests for the SSOT<->consumer key-contract gate."""

import os
import shutil
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_ssot_consumer_keys",
    os.path.join(_HERE, "check-ssot-consumer-keys.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def tree(files: dict) -> str:
    """A throwaway root holding usr/<path> = <body> for each entry."""
    root = tempfile.mkdtemp()
    for rel, body in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
    return root


def data(unresolved=(), max_unresolved=None, ssot=None, table=True):
    d = {"security": {"api_require_auth": False}, "offline": {"memory_provider": "x"}}
    if ssot:
        d.update(ssot)
    if table:
        t = {"unresolved": list(unresolved)}
        if max_unresolved is not None:
            t["max_unresolved"] = max_unresolved
        d["ssot_consumers"] = t
    return d


def only(viols, needle):
    return [v for v in viols if needle in v]


class TestConsumerReads(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for r in self.roots:
            shutil.rmtree(r, ignore_errors=True)

    def make(self, files):
        r = tree(files)
        self.roots.append(r)
        return r

    def test_both_call_spellings_are_matched(self):
        root = self.make({"usr/a.py":
                          '_toml_section("security").get("api_require_auth", False)\n'
                          'x = (_toml_section("offline") or {}).get("memory_provider")\n'})
        self.assertEqual(
            set(mod.consumer_reads(root)),
            {("security", "api_require_auth"), ("offline", "memory_provider")})

    def test_tests_are_not_scanned(self):
        # A test may legitimately read a key it stubs itself.
        root = self.make({"usr/test_a.py": '_toml_section("nope").get("nope")\n'})
        self.assertEqual(mod.consumer_reads(root), {})

    def test_pycache_is_not_scanned(self):
        root = self.make({"usr/__pycache__/a.py": '_toml_section("nope").get("nope")\n'})
        self.assertEqual(mod.consumer_reads(root), {})

    def test_a_resolving_read_is_silent(self):
        root = self.make({"usr/a.py": '_toml_section("security").get("api_require_auth")\n'})
        self.assertEqual(mod.violations(data((), 0), root), [])

    def test_a_misplaced_key_names_both_paths(self):
        root = self.make({"usr/a.py": '_toml_section("pgvector").get("memory_provider")\n'})
        v = mod.violations(data((), 0, {"pgvector": {}}), root)
        hit = only(v, "pgvector.memory_provider")
        self.assertTrue(hit, v)
        self.assertIn("offline.memory_provider", hit[0])

    def test_an_undeclared_key_says_so(self):
        root = self.make({"usr/a.py": '_toml_section("ai").get("permission_tiers")\n'})
        v = mod.violations(data((), 0, {"ai": {}}), root)
        self.assertTrue(only(v, "declared NOWHERE"), v)

    def test_registering_it_silences_it(self):
        root = self.make({"usr/a.py": '_toml_section("ai").get("permission_tiers")\n'})
        self.assertEqual(
            mod.violations(data(("ai.permission_tiers",), 1, {"ai": {}}), root), [])

    def test_an_entry_that_resolves_again_must_leave(self):
        root = self.make({"usr/a.py": '_toml_section("security").get("api_require_auth")\n'})
        v = mod.violations(data(("security.api_require_auth",), 1), root)
        self.assertTrue(only(v, "resolves now"), v)

    def test_an_entry_nothing_reads_must_leave(self):
        root = self.make({"usr/a.py": '_toml_section("security").get("api_require_auth")\n'})
        v = mod.violations(data(("ghost.key",), 1), root)
        self.assertTrue(only(v, "no shipped consumer reads"), v)

    def test_unsorted_register(self):
        root = self.make({"usr/a.py":
                          '_toml_section("ai").get("b")\n_toml_section("ai").get("a")\n'})
        v = mod.violations(data(("ai.b", "ai.a"), 2, {"ai": {}}), root)
        self.assertTrue(only(v, "not sorted"), v)

    def test_duplicate_register_entry(self):
        root = self.make({"usr/a.py": '_toml_section("ai").get("a")\n'})
        v = mod.violations(data(("ai.a", "ai.a"), 2, {"ai": {}}), root)
        self.assertTrue(only(v, "twice"), v)

    def test_ceiling_absent_over_and_left_high(self):
        root = self.make({"usr/a.py":
                          '_toml_section("ai").get("a")\n_toml_section("ai").get("b")\n'})
        both = ("ai.a", "ai.b")
        self.assertTrue(only(mod.violations(data(both, None, {"ai": {}}), root),
                             "max_unresolved is unset"))
        self.assertTrue(only(mod.violations(data(both, 1, {"ai": {}}), root),
                             "over the ratchet ceiling"))
        self.assertTrue(only(mod.violations(data(both, 9, {"ai": {}}), root),
                             "lower it to 2"))

    def test_absent_table(self):
        root = self.make({"usr/a.py": '_toml_section("ai").get("a")\n'})
        v = mod.violations(data(table=False), root)
        self.assertTrue(only(v, "[ssot_consumers] is absent"), v)

    def test_no_reads_at_all_fails_rather_than_passing_vacuously(self):
        root = self.make({"usr/a.py": "print('nothing to see')\n"})
        v = mod.violations(data((), 0), root)
        self.assertTrue(only(v, "vacuously"), v)


class TestRealTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_shipped_register_is_clean(self):
        self.assertEqual(mod.violations(self.real, _ROOT), [])

    def test_the_ceiling_equals_the_register(self):
        self.assertEqual(mod.max_unresolved(self.real),
                         len(mod.register(self.real)))

    def test_the_nine_security_controls_resolve(self):
        # T-325: these sat under an unclosed [security.nohc_allowlist] header, so
        # every one of them silently took its compiled default.
        for key in ("api_require_auth", "api_caller_keys_path", "principal_bind_mode",
                    "rule_of_two_mode", "quarantine_mode", "firewall_high_privilege_verbs",
                    "taint_verbs", "text_view_taint_prefixes", "internal_tld_suffixes",
                    "allowlist_hosts", "provenance_taint"):
            self.assertIn(key, self.real["security"], key)

    def test_the_allowlist_header_holds_only_its_own_lists(self):
        self.assertEqual(set(self.real["security"]["nohc_allowlist"]),
                         {"exempt_files", "exempt_patterns"})

    def test_the_register_does_not_cover_every_read(self):
        # If it did, the gate would assert nothing.
        self.assertLess(len(mod.register(self.real)),
                        len(mod.consumer_reads(_ROOT)))


if __name__ == "__main__":
    unittest.main()
