#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-blade-coverage.py. Cover every way the activation axis can be wrong -- a container classified neither way, one classified both ways, a requires or register entry naming no real container, an empty capability list that gates nothing, a capability no archetype grants, and a duplicated register entry -- plus the empty-set case, because a gate that passes over no containers is the failure this family exists to prevent.
# AI-related: tools/check-blade-coverage.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh
"""Tests for the blade activation-coverage gate."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
# A root with no usr/lib/systemd/system: synthetic cases must see only their
# own declared containers, never the real tree's 18 long-running units.
_NOROOT = os.path.join(_HERE, "no-such-root")
mod = SourceFileLoader(
    "check_blade_coverage", os.path.join(_HERE, "check-blade-coverage.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def data(conts=(), archetypes=None, req=None, ungated=None):
    blade = {"archetypes": dict(archetypes or {"hybrid": ["gpu-serving"]})}
    if req is not None:
        blade["requires"] = dict(req)
    if ungated is not None:
        blade["ungated"] = list(ungated)
    return {"containers": {c: {} for c in conts}, "blade": blade}


class TestReaders(unittest.TestCase):
    def test_a_bare_string_capability_is_read_as_a_list(self):
        d = data(["a"], req={"a": "gpu-serving"})
        self.assertEqual(mod.requires(d), {"a": ["gpu-serving"]})

    def test_archetype_caps_unions_every_archetype(self):
        d = data(archetypes={"hybrid": ["x", "y"], "compute": ["y"], "seat": []})
        self.assertEqual(mod.archetype_caps(d), {"x", "y"})


class TestClassify(unittest.TestCase):
    def test_fully_classified_is_clean(self):
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=["b"])
        self.assertEqual(mod.classify(d, _NOROOT), [])

    def test_unclassified_container_fails(self):
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=[])
        self.assertEqual(len(mod.classify(d, _NOROOT)), 1)
        self.assertIn("'b'", mod.classify(d, _NOROOT)[0])

    def test_classified_both_ways_fails(self):
        d = data(["a"], req={"a": ["gpu-serving"]}, ungated=["a"])
        self.assertTrue(any("classified more than once" in v for v in mod.classify(d, _NOROOT)))

    def test_requires_naming_a_missing_container_fails(self):
        d = data(["a"], req={"ghost": ["gpu-serving"]}, ungated=["a"])
        self.assertTrue(any("not a declared container" in v for v in mod.classify(d, _NOROOT)))

    def test_register_naming_a_missing_container_fails(self):
        d = data(["a"], req={"a": ["gpu-serving"]}, ungated=["ghost"])
        self.assertTrue(any("not a declared container" in v for v in mod.classify(d, _NOROOT)))

    def test_empty_capability_list_fails(self):
        d = data(["a"], req={"a": []}, ungated=[])
        self.assertTrue(any("gates nothing" in v for v in mod.classify(d, _NOROOT)))

    def test_capability_no_archetype_grants_fails(self):
        d = data(["a"], archetypes={"hybrid": ["gpu-serving"]},
                 req={"a": ["storage-serving"]}, ungated=[])
        self.assertTrue(any("granted by NO" in v for v in mod.classify(d, _NOROOT)))

    def test_duplicate_register_entry_fails(self):
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=["b", "b"])
        self.assertTrue(any("twice" in v for v in mod.classify(d, _NOROOT)))

    def test_empty_container_table_fails_rather_than_passing_vacuously(self):
        self.assertIn("vacuously", mod.classify(data([], req={}, ungated=[]), _NOROOT)[0])


class TestShippedTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_real_ssot_classifies_every_container(self):
        self.assertEqual(mod.classify(self.real, _ROOT), [])

    def test_the_gpu_lanes_are_capability_gated(self):
        req = mod.requires(self.real)
        for svc in ("mios-llm-heavy", "mios-llm-heavy-alt", "mios-llm-worker@"):
            self.assertIn("gpu-serving", req.get(svc, []), svc)

    def test_the_seat_archetype_grants_nothing(self):
        # An endpoint (a seat) must expand to NO capabilities, or it is not a seat.
        self.assertEqual(self.real["blade"]["archetypes"]["endpoint"], [])

    def test_the_register_is_drained_and_stays_drained(self):
        # This assertion started as "not empty yet" -- a guard that fired the
        # moment T-319 drained the register. Revisited as designed: empty is now
        # the goal state, so the claim is the stronger one.
        self.assertEqual(mod.register(self.real), [])

    def test_every_container_is_capability_gated(self):
        req = mod.requires(self.real)
        for c in sorted(mod.containers(self.real)):
            self.assertTrue(req.get(c), "%s is gated by nothing" % c)

    def test_the_long_running_units_are_in_scope(self):
        # This gate once counted CONTAINERS only and reported "23 of 23" over a
        # set that excluded 18 long-running units. Guard the wider scope.
        units = mod.long_running_units(_ROOT)
        self.assertGreater(len(units), 10)
        self.assertIn("mios-agent-pipe", units)
        self.assertNotIn("mios-firstboot", units)   # oneshots need no blade gate

    def test_seat_side_units_are_not_also_gated(self):
        req, seat = mod.requires(self.real), set(mod.seat_side(self.real))
        self.assertFalse(seat & set(req))

    def test_the_front_door_is_seat_side(self):
        # A seat with no agent-pipe has no way to reach its blade.
        self.assertIn("mios-agent-pipe", mod.seat_side(self.real))

    def test_no_unit_activates_a_gated_unit_without_its_capability(self):
        # Derived, not hand-classified: this found 11 units that would start on a
        # blade where their dependency is condition-skipped and fail forever --
        # a seat running pgvector backups against a database it does not have.
        self.assertEqual(mod.dependency_violations(self.real, _ROOT), [])

    def test_after_alone_does_not_propagate_a_gate(self):
        # After= is ordering only; it activates nothing, so it must not force a
        # capability onto a unit that merely sequences behind a gated one.
        pulls = mod.unit_pulls(_ROOT)
        self.assertNotIn("mios-llm-heavy", pulls.get("mios-gpu-nvidia", set()))

    def test_the_soft_ok_exemption_names_only_real_units(self):
        self.assertTrue(set(mod.soft_ok(self.real))
                        <= mod.known_units(self.real, _ROOT))

    def test_oneshots_may_be_gated_but_are_not_required_to_be(self):
        must = mod.all_units(self.real, _ROOT)
        known = mod.known_units(self.real, _ROOT)
        self.assertTrue(must < known)                       # strictly wider
        self.assertIn("mios-pgvector-backup", set(mod.requires(self.real)))
        self.assertNotIn("mios-pgvector-backup", must)      # a oneshot

    def test_every_long_running_unit_has_exactly_one_classification(self):
        req = set(mod.requires(self.real))
        seat = set(mod.seat_side(self.real))
        reg = set(mod.register(self.real))
        for u in sorted(mod.long_running_units(_ROOT)):
            hits = [g for g, s in (("requires", req), ("seat_side", seat),
                                   ("ungated", reg)) if u in s]
            self.assertEqual(len(hits), 1, "%s -> %s" % (u, hits))


if __name__ == "__main__":
    unittest.main()
