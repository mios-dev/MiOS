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
    def test_the_document_states_they_are_one_image(self):
        # Assert the CLAIM, not one phrasing of it -- this test used to pin an
        # exact sentence and went red when the sentence was improved.
        text = mod.render(synthetic())
        self.assertIn("same OCI image", text)
        for denial in ("no MiOS-Mini Containerfile", "no MiOS-Mini tag",
                       "no conditional bake"):
            self.assertIn(denial, text)

    def test_the_document_states_mini_is_never_an_artifact(self):
        # ADR-0016 D9. "Mini" reads like a smaller build and is not one, so the
        # comparison has to say so before anything else.
        text = mod.render(synthetic())
        self.assertIn("never an artifact", text)
        self.assertIn("D9", text)

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


if __name__ == "__main__":
    unittest.main()
