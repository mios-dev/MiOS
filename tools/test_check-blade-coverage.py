#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-blade-coverage.py. Cover every way the activation axis can be wrong -- a container classified neither way, one classified both ways, a requires or register entry naming no real container, an empty capability list that gates nothing, a capability no archetype grants, and a duplicated register entry -- plus the empty-set case, because a gate that passes over no containers is the failure this family exists to prevent.
# AI-related: tools/check-blade-coverage.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh
"""Tests for the blade activation-coverage gate."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
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
        self.assertEqual(mod.classify(d), [])

    def test_unclassified_container_fails(self):
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=[])
        self.assertEqual(len(mod.classify(d)), 1)
        self.assertIn("'b'", mod.classify(d)[0])

    def test_classified_both_ways_fails(self):
        d = data(["a"], req={"a": ["gpu-serving"]}, ungated=["a"])
        self.assertTrue(any("only shrinks" in v for v in mod.classify(d)))

    def test_requires_naming_a_missing_container_fails(self):
        d = data(["a"], req={"ghost": ["gpu-serving"]}, ungated=["a"])
        self.assertTrue(any("not a declared container" in v for v in mod.classify(d)))

    def test_register_naming_a_missing_container_fails(self):
        d = data(["a"], req={"a": ["gpu-serving"]}, ungated=["ghost"])
        self.assertTrue(any("not a declared container" in v for v in mod.classify(d)))

    def test_empty_capability_list_fails(self):
        d = data(["a"], req={"a": []}, ungated=[])
        self.assertTrue(any("gates nothing" in v for v in mod.classify(d)))

    def test_capability_no_archetype_grants_fails(self):
        d = data(["a"], archetypes={"hybrid": ["gpu-serving"]},
                 req={"a": ["storage-serving"]}, ungated=[])
        self.assertTrue(any("granted by NO" in v for v in mod.classify(d)))

    def test_duplicate_register_entry_fails(self):
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=["b", "b"])
        self.assertTrue(any("twice" in v for v in mod.classify(d)))

    def test_empty_container_table_fails_rather_than_passing_vacuously(self):
        self.assertIn("vacuously", mod.classify(data([], req={}, ungated=[]))[0])


class TestShippedTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_real_ssot_classifies_every_container(self):
        self.assertEqual(mod.classify(self.real), [])

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


if __name__ == "__main__":
    unittest.main()
