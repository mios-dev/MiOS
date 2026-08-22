#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-unit-projection.py. One case per way the [units] projection register can stop measuring: an entry naming a unit the SSOT does not project, one naming a file the tree does not ship, a duplicate, an unsorted list that hides an addition inside a reordering, a missing table, a missing ceiling, a ceiling raised to absorb new drift, and a ceiling left high after the debt shrank. Plus the alias half of [units] (string values are name aliases, not projected units) and the real tree.
# AI-related: tools/check-unit-projection.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh, tools/native/mios-unit-gen/tests/projection.rs
"""Tests for the [units] projection debt-register gate."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_unit_projection", os.path.join(_HERE, "check-unit-projection.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Two real units, so `shipped()` finds them without a fixture tree.
A = "mios-agent-pipe.service"
B = "mios-daemon.service"


def data(drift, max_drift=None, units=(A, B), aliases=None, table=True):
    u = {name: {"Unit": {"Description": "x"}} for name in units}
    for k, v in (aliases or {}).items():
        u[k] = v
    d = {"units": u}
    if table:
        proj = {"drift": list(drift)}
        if max_drift is not None:
            proj["max_drift"] = max_drift
        d["unit_projection"] = proj
    return d


def only(viols, needle):
    return [v for v in viols if needle in v]


class TestHygiene(unittest.TestCase):
    def test_a_clean_register_is_silent(self):
        self.assertEqual(mod.hygiene(data([A], 1), _ROOT), [])

    def test_an_empty_register_is_the_goal_not_an_error(self):
        self.assertEqual(mod.hygiene(data([], 0), _ROOT), [])

    def test_entry_not_projected_by_units(self):
        v = mod.hygiene(data(["mios-nope.service"], 1), _ROOT)
        self.assertTrue(only(v, "which [units.*] does"), v)

    def test_entry_the_tree_does_not_ship(self):
        # Projected, so it passes the first check -- but there is no such file.
        v = mod.hygiene(data(["ghost.service"], 1, units=(A, "ghost.service")), _ROOT)
        self.assertTrue(only(v, "which the tree does"), v)

    def test_duplicate_entry(self):
        v = mod.hygiene(data([A, A], 2), _ROOT)
        self.assertTrue(only(v, "lists a unit twice"), v)

    def test_unsorted_register(self):
        v = mod.hygiene(data([B, A], 2), _ROOT)
        self.assertTrue(only(v, "not sorted"), v)

    def test_absent_table(self):
        v = mod.hygiene(data([], table=False), _ROOT)
        self.assertTrue(only(v, "[unit_projection] is absent"), v)

    def test_absent_drift_key(self):
        d = data([], 0)
        del d["unit_projection"]["drift"]
        v = mod.hygiene(d, _ROOT)
        self.assertTrue(only(v, "declares no `drift` key"), v)

    def test_absent_ceiling(self):
        v = mod.hygiene(data([A]), _ROOT)
        self.assertTrue(only(v, "max_drift is unset"), v)

    def test_register_over_the_ceiling(self):
        v = mod.hygiene(data([A, B], 1), _ROOT)
        self.assertTrue(only(v, "over the ratchet ceiling"), v)

    def test_ceiling_left_high_after_the_debt_shrank(self):
        # The ground gained must be HELD. A ceiling that stays above the real
        # count is room for the next unit to drift into unnoticed.
        v = mod.hygiene(data([A], 9), _ROOT)
        self.assertTrue(only(v, "lower the ceiling"), v)

    def test_empty_units_table_fails_rather_than_passing_vacuously(self):
        v = mod.hygiene({"units": {}, "unit_projection": {"drift": [], "max_drift": 0}},
                        _ROOT)
        self.assertTrue(only(v, "vacuously"), v)


class TestAliasHalf(unittest.TestCase):
    """[units] carries both `[units."x.service".Unit]` projections and bare
    `name = "unit.service"` aliases. Counting the aliases as projected units
    overstated the projection by 16 and would let one be 'registered'."""

    def test_string_values_are_not_projected_units(self):
        d = data([], 0, aliases={"agent_pipe": A})
        self.assertNotIn("agent_pipe", mod.declared_units(d))
        self.assertIn("agent_pipe", mod.unit_aliases(d))

    def test_an_alias_cannot_be_registered_as_drift(self):
        v = mod.hygiene(data(["agent_pipe"], 1, aliases={"agent_pipe": A}), _ROOT)
        self.assertTrue(only(v, "which [units.*] does"), v)


class TestRealTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_shipped_register_is_clean(self):
        self.assertEqual(mod.hygiene(self.real, _ROOT), [])

    def test_the_ceiling_equals_the_register(self):
        self.assertEqual(mod.max_drift(self.real), len(mod.register(self.real)))

    def test_every_registered_unit_is_projected_and_shipped(self):
        units, on_disk = mod.declared_units(self.real), mod.shipped(_ROOT)
        for name in mod.register(self.real):
            self.assertIn(name, units, name)
            self.assertIn(name, on_disk, name)

    def test_the_register_does_not_cover_the_whole_projection(self):
        # If every projected unit were registered the gate would assert nothing.
        self.assertLess(len(mod.register(self.real)),
                        len(mod.declared_units(self.real)))


if __name__ == "__main__":
    unittest.main()
