#!/usr/bin/env python3
# AI-hint: Sibling test for tools/check-deploy-formats.py; proves the format matrix covers every build target and every recipe.
# AI-related: tools/check-deploy-formats.py, Justfile, config/artifacts/
import importlib.util
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_deploy_formats", os.path.join(_HERE, "check-deploy-formats.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


MOD = _load()


def _ssot():
    import tomllib
    with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
        return tomllib.load(fh)


class TestDeployFormats(unittest.TestCase):
    def setUp(self):
        self.formats = {k: v for k, v in _ssot()["deploy"]["formats"].items()
                        if isinstance(v, dict)}

    def test_the_shipped_matrix_passes(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT
        self.assertEqual(0, MOD.main())

    def test_wsl_is_a_supported_format(self):
        """MiOS ships enabled WSL units, so WSL must be a declared format."""
        self.assertIn("wsl2", self.formats)
        self.assertIn("wslg", self.formats["wsl2"]["gui"].lower())

    def test_every_format_target_exists_in_the_justfile(self):
        just = open(os.path.join(_ROOT, "Justfile"), encoding="utf-8").read()
        targets = set(re.findall(r"^([a-z0-9][a-z0-9_-]*):", just, re.M))
        for name, spec in self.formats.items():
            self.assertIn(spec["target"], targets, name)

    def test_every_recipe_file_is_claimed(self):
        claimed = {os.path.basename(s["recipe"]) for s in self.formats.values()
                   if s.get("recipe")}
        claimed.add(os.path.basename(_ssot()["deploy"]["formats"]["shared_recipe"]))
        for fn in os.listdir(os.path.join(_ROOT, "config/artifacts")):
            if fn.endswith(".toml"):
                self.assertIn(fn, claimed, "%s is claimed by no format" % fn)

    def test_every_variant_ships_declared_formats_only(self):
        for vname, vspec in _ssot()["variants"]["entries"].items():
            for art in vspec.get("artifacts", []):
                self.assertIn(art, self.formats, "%s ships %s" % (vname, art))

    def test_the_media_span_metal_vm_removable_and_wsl(self):
        media = " ".join(s["medium"] for s in self.formats.values()).lower()
        for expected in ("disk", "virtual machine", "usb", "wsl"):
            self.assertIn(expected, media)


if __name__ == "__main__":
    unittest.main(verbosity=1)
