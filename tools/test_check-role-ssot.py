# AI-hint: !/usr/bin/env python3 Unit tests for tools/check-role-ssot.py.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_role_ssot_py.md
"""Tests for the blade role-SSOT gate."""

import os
import shutil
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_NOROOT = os.path.join(_HERE, "no-such-root")
mod = SourceFileLoader(
    "check_role_ssot", os.path.join(_HERE, "check-role-ssot.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def data(btype="hybrid", archetypes=None, alias=None, fallback="headless"):
    if archetypes is None:
        archetypes = {"hybrid": ["x"], "endpoint": []}
    # `or` would swallow an intentionally EMPTY table -- the exact case one of
    # these tests exists to exercise.
    blade = {"type": btype, "fallback": fallback, "archetypes": dict(archetypes)}
    if alias is not None:
        blade["role_aliases"] = dict(alias)
    return {"blade": blade}


def tree(tmp, units):
    """A fake root: {unit-filename: body}."""
    d = os.path.join(tmp, mod.UNIT_DIR)
    os.makedirs(d, exist_ok=True)
    for name, body in units.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    return tmp


def target(name, conflicts=()):
    return ("[Unit]\nDescription=x\nRequires=multi-user.target\n"
            "Conflicts=%s\nAllowIsolate=yes\n\n[Install]\n"
            "WantedBy=multi-user.target\n" % " ".join(conflicts))


class TestType(unittest.TestCase):
    def test_a_legal_type_is_clean(self):
        self.assertEqual(mod.check_type(data()), [])

    def test_an_empty_type_fails(self):
        self.assertTrue(mod.check_type(data(btype="")))

    def test_a_type_naming_no_archetype_fails(self):
        # The exact shape [profile].role shipped in: "developer" was never one.
        out = mod.check_type(data(btype="developer"))
        self.assertTrue(out)
        self.assertIn("developer", out[0])

    def test_an_empty_archetype_table_fails_rather_than_passing_vacuously(self):
        self.assertTrue(mod.check_type(data(archetypes={})))


class TestTargets(unittest.TestCase):
    def test_a_missing_target_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, {"mios-hybrid.target": target("hybrid")})
            out = mod.check_targets(data(), tmp)
            self.assertTrue(any("mios-endpoint.target" in v for v in out))

    def test_an_archetype_name_that_is_not_a_unit_stem_fails(self):
        out = mod.check_targets(data(archetypes={"Not Legal": []}), _NOROOT)
        self.assertTrue(any("legal unit-name stem" in v for v in out))


class TestCapabilitiesConsumed(unittest.TestCase):
    def test_a_capability_nothing_requires_fails(self):
        d = data(archetypes={"hybrid": ["x", "decorative"], "endpoint": []})
        d["blade"]["requires"] = {"a": ["x"]}
        out = mod.check_capabilities_consumed(d)
        self.assertTrue(any("decorative" in v for v in out))

    def test_a_fully_consumed_table_is_clean(self):
        d = data(archetypes={"hybrid": ["x"], "endpoint": []})
        d["blade"]["requires"] = {"a": ["x"]}
        self.assertEqual(mod.check_capabilities_consumed(d), [])

    def test_the_seat_granting_nothing_is_not_a_violation(self):
        d = data(archetypes={"endpoint": []})
        d["blade"]["requires"] = {}
        self.assertEqual(mod.check_capabilities_consumed(d), [])


class TestAliases(unittest.TestCase):
    def test_an_alias_onto_an_archetype_is_clean(self):
        self.assertEqual(mod.check_aliases(data(alias={"k3s": "hybrid"})), [])

    def test_an_alias_onto_nothing_fails(self):
        self.assertTrue(mod.check_aliases(data(alias={"k3s": "nope"})))

    def test_an_alias_shadowing_an_archetype_fails(self):
        self.assertTrue(mod.check_aliases(data(alias={"hybrid": "endpoint"})))


class TestConflicts(unittest.TestCase):
    def test_a_complete_graph_is_clean(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, {
                "mios-hybrid.target": target("hybrid", ["mios-endpoint.target"]),
                "mios-endpoint.target": target("endpoint", ["mios-hybrid.target"]),
            })
            self.assertEqual(mod.check_conflicts(data(), tmp), [])

    def test_a_role_conflicting_with_nothing_fails(self):
        # This is exactly what mios-hybrid.target -- the DEFAULT -- shipped as.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, {
                "mios-hybrid.target": target("hybrid"),
                "mios-endpoint.target": target("endpoint", ["mios-hybrid.target"]),
            })
            out = mod.check_conflicts(data(), tmp)
            self.assertTrue(any("mios-hybrid.target does not conflict" in v
                                for v in out))

    def test_a_conflict_with_a_non_role_target_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, {
                "mios-hybrid.target": target(
                    "hybrid", ["mios-endpoint.target", "mios-k3s-worker.target"]),
                "mios-endpoint.target": target("endpoint", ["mios-hybrid.target"]),
            })
            out = mod.check_conflicts(data(), tmp)
            self.assertTrue(any("not a role target" in v for v in out))


class TestUnitAliases(unittest.TestCase):
    def test_a_suffix_matching_alias_is_clean(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, {"mios-hybrid.target":
                       "[Install]\nAlias=mios-default.target\n"})
            self.assertEqual(mod.check_aliases_in_units(tmp), [])

    def test_the_shipped_default_target_alias_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tree(tmp, {"mios-hybrid.target":
                       "[Install]\nAlias=default.target.mios-hybrid\n"})
            out = mod.check_aliases_in_units(tmp)
            self.assertTrue(out)
            self.assertIn("same suffix", out[0])


class TestProfileRetired(unittest.TestCase):
    def test_no_profile_section_is_clean(self):
        self.assertEqual(mod.check_profile_retired(data(), _NOROOT), [])

    def test_a_resurrected_illegal_role_fails(self):
        d = data()
        d["profile"] = {"role": "developer"}
        self.assertTrue(mod.check_profile_retired(d, _NOROOT))

    def test_the_capital_R_spelling_is_caught_too(self):
        # user-setup.sh emitted `Role`, which no reader spells that way.
        d = data()
        d["profile"] = {"Role": "developer"}
        self.assertTrue(mod.check_profile_retired(d, _NOROOT))

    def test_a_legal_role_alias_is_permitted(self):
        d = data()
        d["profile"] = {"role": "hybrid"}
        self.assertEqual(mod.check_profile_retired(d, _NOROOT), [])

    def test_features_may_not_come_back(self):
        d = data()
        d["profile"] = {"features": ["ai"]}
        self.assertTrue(mod.check_profile_retired(d, _NOROOT))

    def test_a_keep_list_naming_the_retired_vars_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, mod.KEEP_LISTS[0])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('WALK_EMIT_KEEP = {"MIOS_PROFILE_ROLE"}\n')
            out = mod.check_profile_retired(data(), tmp)
            self.assertTrue(any("MIOS_PROFILE_ROLE" in v for v in out))


class TestNoHardcodedRoles(unittest.TestCase):
    def test_a_literal_archetype_in_blade_code_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, mod.BLADE_CODE[0])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('case "$ROLE" in\n  endpoint) TARGET=x ;;\nesac\n')
            out = mod.check_no_hardcoded_roles(data(), tmp)
            self.assertTrue(any("endpoint" in v for v in out))

    def test_a_heredoc_body_is_not_shell_control_flow(self):
        # The embedded python that READS [blade.archetypes] necessarily names
        # TOML keys, and `endpoint` is both an archetype and an ordinary config
        # key -- flagging it would punish the SSOT read this rule requires.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, mod.BLADE_CODE[0])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("_q() {\n    python3 - <<'PY'\n"
                         "print((d.get('ai') or {}).get('endpoint'))\n"
                         "PY\n}\n")
            self.assertEqual(mod.check_no_hardcoded_roles(data(), tmp), [])

    def test_a_case_arm_AFTER_a_heredoc_is_still_caught(self):
        # ...and closing the heredoc must resume checking, or the exclusion
        # becomes a way to hide anything.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, mod.BLADE_CODE[0])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("_q() {\n    python3 - <<'PY'\nprint('x')\nPY\n}\n"
                         'case "$ROLE" in\n  endpoint) T=x ;;\nesac\n')
            out = mod.check_no_hardcoded_roles(data(), tmp)
            self.assertTrue(any("endpoint" in v for v in out), out)

    def test_a_mention_in_a_comment_is_not_a_hardcode(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, mod.BLADE_CODE[0])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# an endpoint blade is a seat\ntrue\n")
            self.assertEqual(mod.check_no_hardcoded_roles(data(), tmp), [])


class TestRealTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_shipped_tree_passes_every_rule(self):
        self.assertEqual(mod.collect(self.real, _ROOT), [])

    def test_the_seat_is_declared_and_grants_nothing(self):
        arche = mod.archetypes(self.real)
        seats = [n for n, caps in arche.items() if not caps]
        self.assertEqual(seats, ["endpoint"])

    def test_the_fallback_is_itself_an_archetype(self):
        blade = self.real["blade"]
        self.assertIn(blade["fallback"], mod.archetypes(self.real))

    def test_every_role_target_conflicts_with_every_other(self):
        targets = mod.role_targets(self.real)
        self.assertGreater(len(targets), 1)
        for unit in targets:
            body = mod.unit_body(_ROOT, unit)
            have = set()
            for line in body.splitlines():
                if line.startswith("Conflicts="):
                    have |= set(line.split("=", 1)[1].split())
            self.assertEqual(have, set(targets) - {unit}, unit)


class TestKeyAccessIsNotAnArchetype(unittest.TestCase):
    """`endpoint` is both an archetype and an ordinary TOML key. A token after
    `.` is a key access; a bare one, or one after `-`, is a hardcoded role."""

    def _scan(self, body):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        path = os.path.join(root, "usr/lib/mios/blade.sh")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        data = {"blade": {"archetypes": {"endpoint": [], "hybrid": ["service-plane"]}}}
        return mod.check_no_hardcoded_roles(data, root)

    def test_a_toml_key_access_is_not_flagged(self):
        self.assertEqual(self._scan('printf "no [ai].endpoint resolved"\n'), [])

    def test_a_bare_role_literal_is_still_flagged(self):
        self.assertTrue(self._scan('case "$r" in endpoint) : ;; esac\n'))

    def test_a_hyphenated_unit_literal_is_still_flagged(self):
        # `-` is NOT excluded: mios-endpoint.target restates the archetype.
        self.assertTrue(self._scan('systemctl start mios-endpoint.target\n'))


if __name__ == "__main__":
    unittest.main()
