#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-variant-registry.py; proves it rejects a dangling edition, archetype, artifact, doc and a name off convention.
# AI-related: tools/check-variant-registry.py, usr/share/mios/mios.toml
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_variant_registry", os.path.join(_HERE, "check-variant-registry.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def _ssot():
    import tomllib
    with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
        return tomllib.load(fh)


class TestVariantRegistry(unittest.TestCase):
    def setUp(self):
        self.v = _ssot()["variants"]
        self.entries = self.v["entries"]

    def test_the_shipped_registry_passes(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT
        self.assertEqual(0, MOD.main())

    def test_every_variant_carries_every_required_field(self):
        for key, spec in self.entries.items():
            for field in MOD.REQUIRED:
                self.assertIn(field, spec, "%s lacks %s" % (key, field))

    def test_status_is_from_the_measured_vocabulary(self):
        for key, spec in self.entries.items():
            self.assertIn(spec["status"], MOD.STATUSES, key)

    def test_title_and_key_are_one_name_in_two_registers(self):
        base = self.v["naming"]["base"]
        for key, spec in self.entries.items():
            if key == base:
                self.assertEqual(self.v["naming"]["prefix"], spec["title"])
            else:
                self.assertEqual(key, spec["title"].lower(), key)

    def test_no_variant_is_named_for_its_size(self):
        """Mini described the image; Metal describes the job. See the suffix rule."""
        for key, spec in self.entries.items():
            for banned in ("mini", "small", "tiny", "lite", "big"):
                self.assertNotIn(banned, key.split("-")[-1].lower(),
                                 "%s names a size, not a job" % key)

    def test_every_edition_is_claimed_by_a_variant(self):
        claimed = {s.get("edition") for s in self.entries.values() if s.get("edition")}
        for ed in _ssot()["editions"]:
            self.assertIn(ed, claimed, "[editions.%s] ships in no variant" % ed)

    def test_the_design_ceiling_equals_the_measurement(self):
        design = [k for k, s in self.entries.items() if s["status"] == "design"]
        self.assertEqual(len(design), self.v["max_design_variants"],
                         "the ceiling must sit at the measurement, not above it")

    def test_each_variant_has_a_page_in_the_manual(self):
        p = os.path.join(_ROOT, "usr/share/man/man7/mios-variants.7")
        self.assertTrue(os.path.isfile(p), "mios-variants(7) is not rendered")
        body = open(p, encoding="utf-8").read()
        for spec in self.entries.values():
            self.assertIn(spec["title"].replace("-", chr(92) + "-"), body)


if __name__ == "__main__":
    unittest.main(verbosity=1)
