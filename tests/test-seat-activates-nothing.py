#!/usr/bin/env python3
# AI-hint: The executable definition of MiOS-Mini. A seat is [blade].type = "endpoint", an archetype granting NO capabilities, so it must activate ZERO of the declared containers while every other archetype keeps exactly what it had. Resolves capability sets the way the drop-in fanout does -- a unit runs when its required markers are all present, since repeated ConditionPathExists is an AND -- and asserts the seat starts nothing, the non-seat roles are unchanged, and every capability a service requires is grantable by some archetype.
# AI-related: usr/share/mios/mios.toml, tools/generate-blade-dropins.py, automation/48-mios-dropin-fanout.sh, usr/share/doc/mios/adr/0016-blade-node-topology.md
"""Proof: an endpoint blade -- a MiOS-Mini -- activates no service."""

import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

SEAT = "endpoint"


def _load():
    with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
        return tomllib.load(fh)


def _caps(v):
    return [v] if isinstance(v, str) else list(v or [])


def starts(data, archetype) -> set:
    """Containers a blade of this archetype activates.

    The fanout writes one ConditionPathExists per required capability, and
    systemd ANDs them, so a unit runs only when the archetype grants ALL of them.
    """
    blade = data["blade"]
    have = set(_caps(blade["archetypes"][archetype]))
    req = {k: set(_caps(v)) for k, v in blade["requires"].items()}
    return {c for c in data["containers"] if req.get(c, set()) <= have}


class TestSeatActivatesNothing(unittest.TestCase):
    def setUp(self):
        self.d = _load()
        self.conts = set(self.d["containers"])

    def test_the_seat_grants_no_capability(self):
        self.assertEqual(_caps(self.d["blade"]["archetypes"][SEAT]), [])

    def test_the_seat_starts_no_container(self):
        self.assertEqual(starts(self.d, SEAT), set())

    def test_every_container_is_gated(self):
        # If any container required nothing it would start on a seat too, which
        # is the exact state this replaced.
        req = self.d["blade"]["requires"]
        ungated = sorted(c for c in self.conts if not _caps(req.get(c)))
        self.assertEqual(ungated, [])

    def test_the_ungated_register_is_drained(self):
        self.assertEqual(list(self.d["blade"].get("ungated") or []), [])

    def test_non_seat_archetypes_still_start_the_service_plane(self):
        for a in ("hybrid", "compute", "controller", "headless", "desktop"):
            self.assertGreater(len(starts(self.d, a)), 0, a)

    def test_only_gpu_archetypes_start_the_gpu_lanes(self):
        gpu = {"mios-llm-heavy", "mios-llm-heavy-alt", "mios-llm-worker@"}
        for a in ("hybrid", "compute"):
            self.assertTrue(gpu <= starts(self.d, a), a)
        for a in ("controller", "headless", "desktop", SEAT):
            self.assertFalse(gpu & starts(self.d, a), a)

    def test_every_required_capability_is_grantable(self):
        granted = set()
        for caps in self.d["blade"]["archetypes"].values():
            granted |= set(_caps(caps))
        for svc, caps in self.d["blade"]["requires"].items():
            for cap in _caps(caps):
                self.assertIn(cap, granted, "%s requires ungrantable %s" % (svc, cap))

    def test_a_dropin_exists_for_every_required_capability(self):
        need = set()
        for caps in self.d["blade"]["requires"].values():
            need |= set(_caps(caps))
        for cap in sorted(need):
            path = os.path.join(_ROOT, "usr/share/mios/dropins", "blade-%s.conf" % cap)
            self.assertTrue(os.path.isfile(path), path)
            with open(path, encoding="utf-8") as fh:
                self.assertIn("ConditionPathExists=/etc/mios/blade.d/%s" % cap, fh.read())


if __name__ == "__main__":
    unittest.main()
