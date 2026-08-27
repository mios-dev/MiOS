#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-fleet-safety.py -- both detectors independently, plus every way the accepted register can stop measuring.
# AI-related: tools/check-fleet-safety.py, usr/share/mios/mios.toml, tests/drift-gate-negatives.sh

import os
import shutil
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "check_fleet_safety", os.path.join(_HERE, "check-fleet-safety.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

K3S_SERVER = "[Container]\nExec=k3s server --disable=traefik\n"
K3S_JOIN = "[Container]\nEnvironment=K3S_URL=https://blade-01:6443\nExec=k3s agent\n"

def data(accepted=(), max_accepted=None, max_nodes=6, grantors=2,
         hazards_table=True, requires=("controller",)):
    arche = {"headless": ["service-plane"]}
    for i in range(grantors):
        arche["ctl%d" % i] = list(requires) + ["service-plane"]
    d = {
        "blades": {"min_nodes": 1, "typical_nodes": 3},
        "blade": {"archetypes": arche,
                  "requires": {"mios-k3s": list(requires)}},
    }
    if max_nodes is not None:
        d["blades"]["max_nodes"] = max_nodes
    if hazards_table:
        h = {"accepted": list(accepted)}
        if max_accepted is not None:
            h["max_accepted"] = max_accepted
        d["blades"]["hazards"] = h
    return d

def tree(k3s_body=K3S_SERVER, ha_body=""):
    root = tempfile.mkdtemp()
    qd = os.path.join(root, "usr/share/containers/systemd")
    os.makedirs(qd)
    with open(os.path.join(qd, "mios-k3s.container"), "w", newline="\n") as fh:
        fh.write(k3s_body)
    ud = os.path.join(root, "usr/lib/systemd/system")
    os.makedirs(ud)
    if ha_body:
        with open(os.path.join(ud, "mios-ha-bootstrap.service"), "w", newline="\n") as fh:
            fh.write(ha_body)
    return root

def only(viols, needle):
    return [v for v in viols if needle in v]

class TestK3sDetector(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for r in self.roots:
            shutil.rmtree(r, ignore_errors=True)

    def make(self, **kw):
        r = tree(**kw)
        self.roots.append(r)
        return r

    def test_two_grantors_and_no_join_path_is_a_hazard(self):
        self.assertIn("k3s-multi-server", mod.detect(data(), self.make()))

    def test_one_grantor_is_not_a_hazard(self):
        # A single archetype standing up one control plane is the correct shape.
        self.assertNotIn("k3s-multi-server",
                         mod.detect(data(grantors=1), self.make()))

    def test_a_join_path_clears_it(self):
        # K3S_URL means the peers join rather than each initialising.
        self.assertNotIn("k3s-multi-server",
                         mod.detect(data(), self.make(k3s_body=K3S_JOIN)))

    def test_a_commented_out_server_is_not_a_hazard(self):
        r = self.make(k3s_body="[Container]\n# Exec=k3s server\nExec=/bin/true\n")
        self.assertNotIn("k3s-multi-server", mod.detect(data(), r))

    def test_the_detail_names_the_grantors(self):
        detail = mod.detect(data(grantors=3), self.make())["k3s-multi-server"]
        self.assertIn("ctl0", detail)
        self.assertIn("K3S_URL", detail)

class TestPacemakerDetector(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for r in self.roots:
            shutil.rmtree(r, ignore_errors=True)

    def test_fencing_disabled_is_a_hazard(self):
        r = tree(ha_body="ExecStart=pcs property set stonith-enabled=false\n")
        self.roots.append(r)
        found = mod.detect(data(), r)
        self.assertIn("pacemaker-unfenced", found)
        self.assertIn("mios-ha-bootstrap.service:1", found["pacemaker-unfenced"])

    def test_a_comment_about_fencing_is_not_a_hazard(self):
        r = tree(ha_body="# we used to set stonith-enabled=false here\nExecStart=/bin/true\n")
        self.roots.append(r)
        self.assertNotIn("pacemaker-unfenced", mod.detect(data(), r))

    def test_no_pacemaker_config_is_not_a_hazard(self):
        r = tree()
        self.roots.append(r)
        self.assertNotIn("pacemaker-unfenced", mod.detect(data(), r))

class TestRegister(unittest.TestCase):
    def setUp(self):
        self.root = tree()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_an_accepted_hazard_is_silent(self):
        self.assertEqual(
            mod.violations(data(("k3s-multi-server",), 1), self.root), [])

    def test_an_unaccepted_hazard_fails(self):
        v = mod.violations(data((), 0), self.root)
        self.assertTrue(only(v, "k3s-multi-server"), v)

    def test_standalone_disarms_the_hazards(self):
        # max_nodes = 1 is a real deployment, not a loophole: the hazards
        # genuinely do not bite, and raising max_nodes re-arms them.
        self.assertEqual(mod.violations(data((), 0, max_nodes=1), self.root), [])
        self.assertTrue(mod.violations(data((), 0, max_nodes=2), self.root))

    def test_max_nodes_must_be_declared(self):
        v = mod.violations(data((), 0, max_nodes=None), self.root)
        self.assertTrue(only(v, "max_nodes is unset"), v)

    def test_absent_hazards_table(self):
        v = mod.violations(data(hazards_table=False), self.root)
        self.assertTrue(only(v, "[blades.hazards] is absent"), v)

    def test_an_entry_that_no_longer_reproduces_must_leave(self):
        v = mod.violations(data(("k3s-multi-server", "pacemaker-unfenced"), 2),
                           self.root)
        self.assertTrue(only(v, "no longer reproduces"), v)

    def test_an_unknown_hazard_id_can_never_retire(self):
        v = mod.violations(data(("ghost-hazard", "k3s-multi-server"), 2), self.root)
        self.assertTrue(only(v, "no detector produces"), v)

    def test_unsorted_and_duplicated(self):
        self.assertTrue(only(mod.violations(
            data(("pacemaker-unfenced", "k3s-multi-server"), 2), self.root),
            "not sorted"))
        self.assertTrue(only(mod.violations(
            data(("k3s-multi-server", "k3s-multi-server"), 2), self.root),
            "twice"))

    def test_ceiling_absent_over_and_left_high(self):
        self.assertTrue(only(mod.violations(data(("k3s-multi-server",)), self.root),
                             "max_accepted is unset"))
        self.assertTrue(only(mod.violations(data(("k3s-multi-server",), 0), self.root),
                             "over the ratchet ceiling"))
        self.assertTrue(only(mod.violations(data(("k3s-multi-server",), 9), self.root),
                             "lower it to 1"))

class TestRealTree(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            self.real = tomllib.load(fh)

    def test_the_shipped_register_is_clean(self):
        self.assertEqual(mod.violations(self.real, _ROOT), [])

    def test_the_operators_fleet_shape_is_declared(self):
        shape = mod.fleet_shape(self.real)
        self.assertEqual(shape["max_nodes"], 6)
        self.assertEqual(shape["typical_nodes"], 3)
        self.assertEqual(shape["min_nodes"], 1)

    def test_both_hazards_really_reproduce_in_the_tree(self):
        # If they stopped, the register entries must go -- this is what makes
        # the register shrink-only rather than decorative.
        self.assertEqual(set(mod.detect(self.real, _ROOT)),
                         {"k3s-multi-server", "pacemaker-unfenced"})

    def test_the_ceiling_equals_the_register(self):
        self.assertEqual(mod.max_accepted(self.real),
                         len(mod.register(self.real)))

if __name__ == "__main__":
    unittest.main()
