#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-blade-coverage.py.
# AI-doc: usr/share/doc/mios/manual/tools.md
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

def data(conts=(), archetypes=None, req=None, ungated=None, fallbacks=None):
    blade = {"archetypes": dict(archetypes or {"hybrid": ["gpu-serving"]})}
    if req is not None:
        blade["requires"] = dict(req)
    if ungated is not None:
        blade["ungated"] = list(ungated)
    # ADR-0017 D2: a gpu-serving unit must name a CPU lane to degrade to. The
    # fixtures below opt in explicitly so that rule is exercised by its own
    # test rather than firing as a side effect of every other one.
    if fallbacks is not None:
        blade["cpu_fallbacks"] = dict(fallbacks)
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
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=["b"],
                 fallbacks={"a": ["cpu"]})
        self.assertEqual(mod.classify(d, _NOROOT), [])

    def test_unclassified_container_fails(self):
        d = data(["a", "b"], req={"a": ["gpu-serving"]}, ungated=[],
                 fallbacks={"a": ["cpu"]})
        self.assertEqual(len(mod.classify(d, _NOROOT)), 1)
        self.assertIn("'b'", mod.classify(d, _NOROOT)[0])

    def test_gpu_unit_without_a_cpu_fallback_fails(self):
        """ADR-0017 D2: GPU-gated work degrades to a CPU lane, it does not vanish."""
        d = data(["a"], req={"a": ["gpu-serving"]}, ungated=[], fallbacks={})
        self.assertTrue(any("cpu_fallbacks" in v for v in mod.classify(d, _NOROOT)))
        ok = data(["a"], req={"a": ["gpu-serving"]}, ungated=[], fallbacks={"a": ["cpu"]})
        self.assertFalse(any("cpu_fallbacks" in v for v in mod.classify(ok, _NOROOT)))

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

class TestSeatDeadWeight(unittest.TestCase):
    """The AI plane couples over ADDRESSES, which the dependency walk cannot see."""

    def _tree(self, tmp, units, seat, req, urls=None, endpoint=""):
        d = os.path.join(tmp, "usr/lib/systemd/system")
        os.makedirs(d, exist_ok=True)
        for name, body in units.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        return {"ports": {"worker_cdp": 9223, "front": 8700},
                "urls": dict(urls or {}),
                "ai": {"endpoint": endpoint},
                "blade": {"archetypes": {"hybrid": ["service-plane"], "endpoint": []},
                          "seat_side": list(seat), "requires": dict(req)}}

    def test_a_seat_side_binder_whose_only_client_is_gated_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self._tree(tmp, {
                "browser-w.service": "Environment=MIOS_PORT_WORKER_CDP=9223\n",
                "worker.service": "Environment=URL=http://localhost:9223\n",
            }, seat=["browser-w"], req={"worker": ["service-plane"]})
            out = mod.seat_dead_weight(d, tmp)
            self.assertTrue(any("browser-w" in v for v in out), out)

    def test_an_ungated_client_clears_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self._tree(tmp, {
                "browser-w.service": "Environment=MIOS_PORT_WORKER_CDP=9223\n",
                "tool.service": "Environment=URL=http://localhost:9223\n",
            }, seat=["browser-w"], req={})
            self.assertEqual(mod.seat_dead_weight(d, tmp), [])

    def test_a_person_facing_port_is_exempt(self):
        # The front door's client is every human and CLI, not another unit.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self._tree(tmp, {
                "front.service": "Environment=MIOS_PORT_FRONT=8700\n",
                "owui.service": "Environment=URL=http://localhost:8700\n",
            }, seat=["front"], req={"owui": ["service-plane"]},
                endpoint="http://localhost:${MIOS_PORT_FRONT}/v1")
            self.assertEqual(mod.seat_dead_weight(d, tmp), [])

    def test_a_urls_entry_also_makes_a_port_person_facing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self._tree(tmp, {
                "front.service": "Environment=MIOS_PORT_FRONT=8700\n",
                "owui.service": "Environment=URL=http://localhost:8700\n",
            }, seat=["front"], req={"owui": ["service-plane"]},
                urls={"front": "http://localhost:${MIOS_PORT_FRONT}/"})
            self.assertEqual(mod.seat_dead_weight(d, tmp), [])

    def test_the_real_tree_has_no_dead_weight_on_a_seat(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            real = tomllib.load(fh)
        self.assertEqual(mod.seat_dead_weight(real, _ROOT), [])

if __name__ == "__main__":
    unittest.main()
