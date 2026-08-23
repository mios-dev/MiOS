#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-node-pool.py.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Tests for the fan-out pool gate."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_node_pool", os.path.join(_HERE, "check-node-pool.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

VOCAB = "gpu:8,cpu:7,accelerator:6,igpu:3,mobile:2,_default:5"


def data(nodes, blades=None, vocab=VOCAB):
    d = {"dispatch": {"lane_priority": vocab}, "nodes": dict(nodes)}
    if blades is not None:
        d["blades"] = dict(blades)
    return d


GPU = {"endpoint": "http://localhost:${MIOS_PORT_SGLANG}/v1",
       "model": "mios-heavy", "lane": "gpu"}


class TestAliases(unittest.TestCase):
    def test_an_exact_duplicate_fails(self):
        # Four of six shipped nodes were this.
        out = mod.aliases(data({"a": dict(GPU), "b": dict(GPU)}))
        self.assertTrue(out)
        self.assertIn("duplicates", out[0])

    def test_a_different_model_on_one_endpoint_is_not_an_alias(self):
        b = dict(GPU); b["model"] = "mios-agent-cpu"
        self.assertEqual(mod.aliases(data({"a": dict(GPU), "b": b})), [])

    def test_an_inert_placeholder_is_never_an_alias(self):
        inert = {"endpoint": "", "model": "mios-igpu", "lane": "igpu"}
        self.assertEqual(
            mod.aliases(data({"a": dict(inert), "b": dict(inert)})), [])


class TestLanes(unittest.TestCase):
    def test_one_endpoint_declared_as_two_lanes_fails(self):
        b = dict(GPU); b["lane"] = "cpu"; b["model"] = "other"
        out = mod.lane_conflicts(data({"a": dict(GPU), "b": b}))
        self.assertTrue(out)
        self.assertIn("one endpoint", out[0])

    def test_a_lane_dispatch_does_not_budget_fails(self):
        n = dict(GPU); n["lane"] = "quantum"
        out = mod.illegal_lanes(data({"a": n}))
        self.assertTrue(out)
        self.assertIn("quantum", out[0])

    def test_an_empty_vocabulary_fails_rather_than_passing_vacuously(self):
        self.assertTrue(mod.illegal_lanes(data({"a": dict(GPU)}, vocab="")))

    def test_the_real_vocabulary_is_read_from_dispatch(self):
        self.assertEqual(mod.lane_vocabulary(data({})),
                         {"gpu", "cpu", "accelerator", "igpu", "mobile"})


class TestBlades(unittest.TestCase):
    def test_omitting_blade_is_legal(self):
        # No blade == the LOCAL blade, whose name comes from [identity].hostname.
        self.assertEqual(mod.orphan_blades(data({"a": dict(GPU)})), [])

    def test_naming_a_blade_that_does_not_exist_fails(self):
        n = dict(GPU); n["blade"] = "blade-99"
        self.assertTrue(mod.orphan_blades(data({"a": n}, blades={})))

    def test_naming_a_declared_blade_is_clean(self):
        n = dict(GPU); n["blade"] = "blade-01"
        self.assertEqual(
            mod.orphan_blades(data({"a": n}, blades={"blade-01": {}})), [])


class TestOffloadability(unittest.TestCase):
    def test_a_baked_local_port_fails(self):
        n = {"endpoint": "http://localhost:8530/v1", "model": "m", "lane": "gpu"}
        out = mod.unmovable_endpoints(data({"a": n}))
        self.assertTrue(out)
        self.assertIn("8530", out[0])

    def test_a_templated_local_port_is_clean(self):
        self.assertEqual(mod.unmovable_endpoints(data({"a": dict(GPU)})), [])

    def test_a_remote_host_is_clean(self):
        n = {"endpoint": "http://blade-01.mesh:8530/v1", "model": "m", "lane": "gpu"}
        self.assertEqual(mod.unmovable_endpoints(data({"a": n})), [])


class TestRealTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, mod.TOML), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_shipped_pool_is_clean(self):
        self.assertEqual(mod.classify(self.real), [])

    def test_an_empty_pool_fails_rather_than_passing_vacuously(self):
        self.assertTrue(mod.classify({"dispatch": {"lane_priority": VOCAB},
                                      "nodes": {}}))

    def test_the_pool_actually_has_a_cpu_lane(self):
        # It did not: local-cpu pointed at the GPU endpoint with lane="gpu".
        lanes = {str(c.get("lane") or "") for c in mod.nodes(self.real).values()}
        self.assertIn("cpu", lanes)

    def test_every_reachable_endpoint_is_distinct(self):
        eps = [c["endpoint"] for c in mod.nodes(self.real).values()
               if c.get("endpoint")]
        self.assertEqual(len(eps), len(set(eps)))


if __name__ == "__main__":
    unittest.main()
