#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-CAT tri-launcher hardening and staging separation.
# AI-related: usr/libexec/mios/cat/launcher.py, usr/share/doc/mios/manual/ch02-installation-and-deployment.md
"""Automated tests for WS-CAT tri-launcher modes, read-only repo mounts, and data staging."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_CAT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "cat", "launcher.py")

spec = importlib.util.spec_from_file_location("cat_launcher", _CAT_PATH)
if spec and spec.loader:
    cat_launcher = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cat_launcher
    spec.loader.exec_module(cat_launcher)
else:
    raise ImportError(f"Could not load cat/launcher module from {_CAT_PATH}")


class TestCatLauncher(unittest.TestCase):
    """Validates dev/staging/prod launcher mode isolation and read-only repo bind mounts."""

    def test_tri_launcher_modes_and_mounts(self):
        # Dev mode
        dev_launch = cat_launcher.CatLauncher(mode="dev", repo_root="/test/repo", data_root="/test/data")
        dev_mounts = dev_launch.get_mount_configuration()
        self.assertEqual(dev_mounts[0]["options"], "ro")
        self.assertEqual(dev_mounts[1]["options"], "rw")

        # Staging mode
        staging_launch = cat_launcher.CatLauncher(mode="staging", repo_root="/test/repo", data_root="/test/data")
        staging_mounts = staging_launch.get_mount_configuration()
        self.assertEqual(len(staging_mounts), 3)

        # Invalid mode rejection
        with self.assertRaises(ValueError):
            cat_launcher.CatLauncher(mode="invalid_mode")

    def test_staging_paths_resolution(self):
        prod_launch = cat_launcher.CatLauncher(mode="prod", repo_root="/opt/mios", data_root="/var/data")
        paths = prod_launch.resolve_staging_paths()
        self.assertEqual(paths["mode"], "prod")
        self.assertEqual(paths["repo_dir"], "/opt/mios")
        self.assertEqual(paths["data_dir"], os.path.join("/var/data", "prod"))


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCatLauncher)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
