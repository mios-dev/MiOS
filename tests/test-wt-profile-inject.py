#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Windows Terminal settings.json profile injector.
# AI-related: usr/libexec/mios/win/wt_profile_inject.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
"""Unit and integration test suite for WindowsTerminalProfileInjector and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "win", "wt_profile_inject.py")

spec = importlib.util.spec_from_file_location("wt_profile_inject", _TARGET_PATH)
if spec and spec.loader:
    wt_profile_inject = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = wt_profile_inject
    spec.loader.exec_module(wt_profile_inject)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestWtProfileInject(unittest.TestCase):
    """Test suite for non-destructive Windows Terminal settings.json merging, palette injection, and CLI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-wt-")
        self.settings_path = os.path.join(self.temp_dir.name, "settings.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_mios_profiles(self):
        injector = wt_profile_inject.WindowsTerminalProfileInjector(
            ssh_port=2222,
            ssh_user="mios",
            mock=True,
        )
        profiles = injector.build_mios_profiles()
        self.assertEqual(len(profiles), 3)

        guids = [p.guid for p in profiles]
        self.assertIn(wt_profile_inject.WSL_GUID, guids)
        self.assertIn(wt_profile_inject.SSH_GUID, guids)
        self.assertIn(wt_profile_inject.SERIAL_GUID, guids)

    def test_merge_profiles_and_schemes_into_existing(self):
        initial_settings = {
            "$schema": "https://aka.ms/terminal-profiles-schema",
            "defaultProfile": "{initial-guid}",
            "profiles": {
                "list": [
                    {
                        "guid": "{initial-guid}",
                        "name": "PowerShell",
                        "commandline": "powershell.exe",
                    }
                ]
            },
            "schemes": [],
        }
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(initial_settings, f, indent=2)

        injector = wt_profile_inject.WindowsTerminalProfileInjector(
            settings_path=self.settings_path,
            mock=False,
        )
        res = injector.run()

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["profiles_added"], 3)
        self.assertTrue(os.path.exists(self.settings_path))

        with open(self.settings_path, "r", encoding="utf-8") as f:
            updated = json.load(f)

        # Original profile preserved
        self.assertEqual(len(updated["profiles"]["list"]), 4)
        names = [p["name"] for p in updated["profiles"]["list"]]
        self.assertIn("PowerShell", names)
        self.assertIn("MiOS WSL (Development)", names)
        self.assertIn("MiOS Host SSH", names)
        self.assertIn("MiOS Serial Console", names)

        # Scheme injected
        scheme_names = [s["name"] for s in updated["schemes"]]
        self.assertIn("MiOS Dark", scheme_names)

    def test_cli_execution_mock_json(self):
        test_args = [
            "wt_profile_inject.py",
            "--settings-json", self.settings_path,
            "--ssh-port", "2222",
            "--ssh-user", "mios",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = wt_profile_inject.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWtProfileInject)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
