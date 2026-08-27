#!/usr/bin/env python3
# AI-hint: Sibling test for tools/verify-images.py; proves an empty build tree and a zero-filled artifact are both rejected.
# AI-related: tools/verify-images.py, usr/share/mios/mios.toml
"""The recipe this replaced reported "0 artifact passed, 0 failed" and exited 0.

It also computed each artifact's header and compared it against nothing, so two
mebibytes of zeroes named disk.qcow2 passed. Both are asserted here as failures,
because a verifier that cannot reject is the thing `just publish` was trusting.
"""
import importlib.util
import os
import shutil
import stat
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_MADE = []

def _load():
    spec = importlib.util.spec_from_file_location(
        "verify_images", os.path.join(_HERE, "verify-images.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

MOD = _load()

def tearDownModule():
    for d in _MADE:
        for base, dirs, files in os.walk(d):
            for name in dirs + files:
                try:
                    os.chmod(os.path.join(base, name), stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
        shutil.rmtree(d, ignore_errors=True)
    _MADE.clear()

class TestVerifyImages(unittest.TestCase):
    def _tree(self):
        """A tree with the SSOT but no artifacts: the empty-build case.

        The verifier reads the required format set from the SSOT, so a bare
        temporary directory tests a missing config rather than a missing build.
        """
        d = tempfile.mkdtemp(prefix="mios-verifyimg-")
        _MADE.append(d)
        dst = os.path.join(d, "usr", "share", "mios")
        os.makedirs(dst, exist_ok=True)
        shutil.copyfile(os.path.join(_ROOT, "usr/share/mios/mios.toml"),
                        os.path.join(dst, "mios.toml"))
        return d

    def test_an_empty_build_tree_is_not_a_pass(self):
        os.environ["MIOS_DRIFT_ROOT"] = self._tree()
        try:
            self.assertNotEqual(0, MOD.main([]))
        finally:
            os.environ["MIOS_DRIFT_ROOT"] = _ROOT

    def test_the_shipped_ssot_declares_globs_for_file_formats(self):
        import tomllib
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            formats = (tomllib.load(fh)["deploy"]["formats"])
        filed = {k: v for k, v in formats.items()
                 if isinstance(v, dict) and v.get("medium") not in (None, "container registry")}
        self.assertTrue(filed, "no file-writing format declared")
        for name, spec in filed.items():
            self.assertTrue(spec.get("artifacts"),
                            "%s writes a file and declares no artifact glob" % name)

    def test_a_size_floor_is_declared(self):
        import tomllib
        with open(os.path.join(_ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            v = (tomllib.load(fh)["deploy"].get("verify") or {})
        self.assertGreater(int(v.get("min_bytes", 0)), 0,
                           "without a floor an empty file counts as an artifact")

if __name__ == "__main__":
    unittest.main(verbosity=1)
