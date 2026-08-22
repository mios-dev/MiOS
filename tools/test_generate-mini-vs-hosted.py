#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/generate-mini-vs-hosted.py. The comparison document exists because a hand-written one goes stale the moment an archetype gains a capability, so these assert the numbers are DERIVED: change the SSOT and the rendered counts move with it. Also pins the two facts the document exists to state -- a seat starts strictly fewer units than any other archetype, and it has zero local inference lanes.
# AI-related: tools/generate-mini-vs-hosted.py, usr/share/mios/mios.toml, usr/share/doc/mios/reference/mini-vs-hosted.md
"""Tests for the seat-vs-blade comparison projector."""

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
mod = SourceFileLoader(
    "gen_mini", os.path.join(_HERE, "generate-mini-vs-hosted.py")).load_module()

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def synthetic(seat_side=("front",), extra_gated=0):
    req = {"a": ["service-plane"], "b": ["gpu-serving", "service-plane"]}
    for i in range(extra_gated):
        req["extra%d" % i] = ["service-plane"]
    return {
        "blade": {
            "archetypes": {"endpoint": [], "hybrid": ["service-plane", "gpu-serving"]},
            "requires": req,
            "seat_side": list(seat_side),
        },
        "greenboot": {"critical_services": ["agent-pipe"],
                      "probe": {}, "blade_reachability_critical": False},
        "urls": {},
    }


class TestDerivation(unittest.TestCase):
    def test_the_seat_starts_no_gated_unit(self):
        rows = dict((r[0], r) for r in mod.archetype_rows(synthetic()))
        self.assertEqual(rows["endpoint"][2], 0)

    def test_a_new_gated_unit_moves_the_hosted_count(self):
        before = dict((r[0], r) for r in mod.archetype_rows(synthetic()))["hybrid"][2]
        after = dict((r[0], r) for r in
                     mod.archetype_rows(synthetic(extra_gated=3)))["hybrid"][2]
        self.assertEqual(after, before + 3)

    def test_a_new_seat_side_unit_moves_BOTH_totals(self):
        # seat_side runs everywhere, so it is not a difference between them.
        one = dict((r[0], r) for r in mod.archetype_rows(synthetic()))
        two = dict((r[0], r) for r in
                   mod.archetype_rows(synthetic(seat_side=("front", "ui"))))
        self.assertEqual(two["endpoint"][3], one["endpoint"][3] + 1)
        self.assertEqual(two["hybrid"][3], one["hybrid"][3] + 1)

    def test_gated_off_names_the_missing_capability(self):
        out = dict(mod.gated_off_on_seat(synthetic()))
        self.assertEqual(out["a"], ["service-plane"])
        self.assertEqual(out["b"], ["gpu-serving", "service-plane"])


class TestRendering(unittest.TestCase):
    def test_the_document_states_both_modes_are_one_image(self):
        # Assert the CLAIM, not one phrasing of it.
        text = mod.render(synthetic())
        self.assertIn("same OCI image", text)
        for denial in ("no separate Containerfile", "tag or conditional bake"):
            self.assertIn(denial, text)

    def test_it_states_mini_boots_the_whole_image(self):
        # Two earlier revisions defined MiOS-Mini and both were wrong.
        # ADR-0016 D9 holds the history; T-331/T-335 hold the corrections.
        text = mod.render(synthetic())
        self.assertIn("boots the **entire** image", text)
        self.assertIn("D9", text)
        for wrong in ("never an artifact", "MiOS-Mini is the BOX",
                      "NOT about MiOS-Mini"):
            self.assertNotIn(wrong, text)

    def test_it_keeps_the_two_comparisons_apart(self):
        # The confusion these two parts exist to prevent is exactly what
        # produced the wrong revisions: an archetype is a posture, not a
        # product, so the page must never let one stand in for the other.
        text = mod.render(synthetic())
        self.assertIn("Part 1 — the two products", text)
        self.assertIn("Part 2 — the two modes", text)
        self.assertLess(text.index("Part 1"), text.index("Part 2"))
        self.assertIn("grants nothing", text)
        self.assertIn("not a product at all", text)

    def test_the_rendered_counts_are_the_derived_ones(self):
        d = synthetic(extra_gated=2)
        rows = dict((r[0], r) for r in mod.archetype_rows(d))
        text = mod.render(d)
        self.assertIn("| Units started | **%d** | **%d** |"
                      % (rows["endpoint"][3], rows["hybrid"][3]), text)

    def test_render_is_deterministic(self):
        self.assertEqual(mod.render(synthetic()), mod.render(synthetic()))


class TestBakedPayloads(unittest.TestCase):
    """The seat's disk cost is DERIVED from the bake specs, never hand-listed --
    a hand-listed one goes stale the first time a model is swapped."""

    def test_the_gguf_spec_splits_into_local_and_source(self):
        d = {"llamacpp": {"bake_models": "a.gguf=org/repo:a-Q4.gguf,b.gguf=org2/repo2:b.gguf"}}
        self.assertEqual(mod.baked_payloads(d),
                         [("a.gguf", "org/repo:a-Q4.gguf"), ("b.gguf", "org2/repo2:b.gguf")])

    def test_a_malformed_entry_is_skipped_not_guessed(self):
        d = {"llamacpp": {"bake_models": "a.gguf=org/repo:a.gguf,,justaname"}}
        self.assertEqual(mod.baked_payloads(d), [("a.gguf", "org/repo:a.gguf")])

    def test_the_vllm_snapshot_counts_as_a_payload(self):
        d = {"ai": {"vllm": {"bake_model": "org/Model-AWQ"}}}
        self.assertEqual(mod.baked_payloads(d), [("vLLM snapshot", "org/Model-AWQ")])

    def test_an_empty_vllm_model_bakes_nothing(self):
        self.assertEqual(mod.baked_payloads({"ai": {"vllm": {"bake_model": ""}}}), [])

    def test_no_bake_spec_at_all_is_an_empty_list(self):
        self.assertEqual(mod.baked_payloads({}), [])

    def test_the_document_names_every_payload(self):
        d = synthetic()
        d["llamacpp"] = {"bake_models": "x.gguf=org/repo:x.gguf"}
        d["ai"] = {"vllm": {"bake_model": "org/Big-AWQ", "enable": False}}
        text = mod.render(d)
        self.assertIn("x.gguf", text)
        self.assertIn("org/Big-AWQ", text)
        # Baked while the lane is off is worth saying out loud (ADR-0016 D7).
        self.assertIn("T-330", text)

    def test_an_enabled_vllm_lane_draws_no_complaint(self):
        d = synthetic()
        d["ai"] = {"vllm": {"bake_model": "org/Big-AWQ", "enable": True}}
        self.assertNotIn("T-330", mod.render(d))


class TestRealTree(unittest.TestCase):
    def setUp(self):
        self.real = mod.load(_ROOT)

    def test_the_shipped_document_matches_the_ssot(self):
        with open(os.path.join(_ROOT, mod.OUT), encoding="utf-8") as fh:
            self.assertEqual(fh.read().replace("\r\n", "\n"), mod.render(self.real))

    def test_the_seat_is_strictly_the_smallest_archetype(self):
        rows = mod.archetype_rows(self.real)
        seat = next(r for r in rows if r[0] == mod.SEAT)
        for r in rows:
            if r[0] != mod.SEAT:
                self.assertLess(seat[3], r[3], r[0])

    def test_the_seat_has_no_local_inference_lane(self):
        # The document's central claim; if a lane becomes ungated this fails.
        off = {u for u, _ in mod.gated_off_on_seat(self.real)}
        for lane in ("mios-llm-light", "mios-llm-heavy", "mios-llm-heavy-alt",
                     "mios-cpu-node"):
            self.assertIn(lane, off, lane)



def with_planes(**over):
    """A synthetic SSOT that DOES declare planes, plus the packages that would
    prove them baked."""
    d = synthetic()
    d["packages"] = {"base": {"pkgs": ["libvirt"]},
                     "nested": {"sections": {"deep": {"pkgs": ["ceph-common"]}}}}
    d["blade"]["planes"] = {
        "hypervisor": {"role": "metal", "owner": "mini",
                       "markers": ["libvirt"], "wired_by": "Justfile"},
        "radio": {"role": "wifi", "owner": "mini",
                  "markers": ["hostapd"], "wired_by": ""},
        "storage": {"role": "cephfs", "owner": "either",
                    "markers": ["ceph-common"], "wired_by": "Justfile"},
        "ai": {"role": "lanes", "owner": "either",
               "markers": [], "wired_by": "Justfile"},
    }
    d["blade"]["planes"].update(over)
    return d


class TestPlanes(unittest.TestCase):
    """Part 1's verdicts are derived, so neither column can be faked in the
    SSOT (Law 8). See ADR-0016 D10."""

    def test_packages_are_collected_at_every_nesting_depth(self):
        # [packages] mixes flat lists, {pkgs=[...]} tables and nested section
        # maps. A marker found by only one shape would report a baked plane
        # as absent.
        have = mod.all_packages(with_planes())
        self.assertIn("libvirt", have)
        self.assertIn("ceph-common", have)

    def test_a_marker_absent_from_packages_reads_not_baked(self):
        rows = dict((r[0], r) for r in mod.plane_rows(_ROOT, with_planes()))
        self.assertEqual(rows["radio"][4], ["hostapd"])
        self.assertEqual(rows["hypervisor"][4], [])

    def test_adding_the_missing_package_flips_the_verdict(self):
        d = with_planes()
        d["packages"]["base"]["pkgs"].append("hostapd")
        rows = dict((r[0], r) for r in mod.plane_rows(_ROOT, d))
        self.assertEqual(rows["radio"][4], [])

    def test_wiring_is_the_file_existing_not_a_declared_verdict(self):
        d = with_planes()
        d["blade"]["planes"]["storage"]["wired_by"] = "no/such/file"
        rows = dict((r[0], r) for r in mod.plane_rows(_ROOT, d))
        self.assertFalse(rows["storage"][6])
        self.assertTrue(rows["hypervisor"][6])

    def test_an_empty_wired_by_is_unwired(self):
        rows = dict((r[0], r) for r in mod.plane_rows(_ROOT, with_planes()))
        self.assertFalse(rows["radio"][6])

    def test_owner_alone_decides_what_can_be_shed(self):
        # This IS the definition of offload (ADR-0016 D10) -- not bakedness,
        # not wiring. An unbaked `either` plane is still shed-able in principle.
        movable, fixed = mod.shed_split(mod.plane_rows(_ROOT, with_planes()))
        self.assertEqual(movable, ["ai", "storage"])
        self.assertEqual(fixed, ["hypervisor", "radio"])

    def test_flipping_an_owner_moves_the_plane_between_sets(self):
        d = with_planes()
        d["blade"]["planes"]["radio"]["owner"] = "either"
        movable, fixed = mod.shed_split(mod.plane_rows(_ROOT, d))
        self.assertIn("radio", movable)
        self.assertNotIn("radio", fixed)

    def test_an_unknown_owner_is_not_shed_able(self):
        # Fail closed: a typo'd owner must never grant mobility by accident.
        d = with_planes()
        d["blade"]["planes"]["storage"]["owner"] = "eithr"
        movable, fixed = mod.shed_split(mod.plane_rows(_ROOT, d))
        self.assertNotIn("storage", movable)
        self.assertIn("storage", fixed)

    def test_the_rendered_shed_count_is_the_derived_one(self):
        d = with_planes()
        movable, _ = mod.shed_split(mod.plane_rows(_ROOT, d))
        text = mod.render(d, _ROOT)
        self.assertIn("**%d of %d planes**" % (len(movable), 4), text)

    def test_no_markers_means_the_package_test_says_nothing(self):
        # The AI plane ships as GGUF payloads, not RPMs. Reporting it "baked"
        # because it declared zero markers would be a vacuous pass.
        text = mod.render(with_planes(), _ROOT)
        self.assertIn("n/a — payload, not RPM", text)

    def test_an_unbaked_plane_is_named_in_the_open_items(self):
        text = mod.render(with_planes(), _ROOT)
        self.assertIn("`radio` (`mini`) is **not baked**", text)
        self.assertNotIn("`hypervisor` (`mini`) is **not baked**", text)

    def test_an_empty_planes_table_is_reported_as_a_defect(self):
        # synthetic() declares no planes at all. Rendering "0 of 0" as though
        # it were an answer is the failure mode this pins shut.
        text = mod.render(synthetic(), _ROOT)
        self.assertIn("`[blade.planes]` is empty", text)
        self.assertNotIn("**0 of 0 planes**", text)

    def test_the_shipped_planes_match_the_shipped_packages(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            data = tomllib.load(fh)
        rows = mod.plane_rows(_ROOT, data)
        self.assertTrue(rows, "[blade.planes] must not be empty")
        for name, _role, owner, _m, _mi, wired_by, wired in rows:
            self.assertIn(owner, ("mini", "either"),
                          "%s declares an owner outside the two tiers" % name)
            if wired_by:
                self.assertTrue(wired, "%s points at a file that is gone: %s"
                                % (name, wired_by))


class TestHardwareFloor(unittest.TestCase):
    """The floor is INTERFACES, not radios: any mix counts as long as two are
    separate and one can be an AP. ADR-0016 D11."""

    def test_the_floor_is_rendered_from_the_ssot(self):
        d = with_planes()
        d["blade"]["hardware"] = {"min_interfaces": 3, "min_ap_capable": 2}
        text = mod.render(d, _ROOT)
        self.assertIn("**3 separate interfaces**", text)
        self.assertIn("least **2**", text)

    def test_no_declared_floor_renders_no_claim(self):
        # Better silent than inventing a floor the SSOT never stated.
        text = mod.render(with_planes(), _ROOT)
        self.assertNotIn("separate interfaces", text)

    def test_the_shipped_floor_admits_a_wired_plus_radio_box(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            hw = (tomllib.load(fh)["blade"]).get("hardware") or {}
        self.assertEqual(hw.get("min_interfaces"), 2)
        # One AP-capable interface, not two radios -- 1 radio + 1 wired WAN
        # must satisfy the floor.
        self.assertEqual(hw.get("min_ap_capable"), 1)


class TestOpenItemsClaim(unittest.TestCase):
    """The "only a Mini can supply these" sentence is a CLAIM about the open
    set. It must be derived, or moving one owner silently makes it false."""

    def test_all_mini_open_items_keep_the_strong_claim(self):
        text = mod.render(with_planes(), _ROOT)
        self.assertIn("only ones adding a peer cannot supply", text)

    def test_an_open_either_plane_retracts_it(self):
        d = with_planes()
        d["blade"]["planes"]["storage"]["markers"] = ["not-a-package"]
        text = mod.render(d, _ROOT)
        self.assertNotIn("only ones adding a peer cannot supply", text)
        self.assertIn("can be supplied by adding a peer", text)

    def test_the_shipped_tree_still_earns_the_strong_claim(self):
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            data = tomllib.load(fh)
        rows = mod.plane_rows(_ROOT, data)
        open_rows = [r for r in rows if (r[3] and r[4]) or not r[5]]
        self.assertTrue(open_rows, "nothing open -- this test would pass vacuously")
        self.assertEqual(set(r[2] for r in open_rows), {"mini"})

if __name__ == "__main__":
    unittest.main()
