#!/usr/bin/env python3
# AI-hint: Unit and integration tests for first-boot interactive & headless OOBE wizard.
# AI-related: usr/libexec/mios/ux/firstboot_wizard.py, usr/share/mios/mios.toml, usr/libexec/mios/net/nm_preseed.py
"""Unit and integration test suite for FirstBootWizardEngine and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "firstboot_wizard.py")

spec = importlib.util.spec_from_file_location("firstboot_wizard", _TARGET_PATH)
if spec and spec.loader:
    firstboot_wizard = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = firstboot_wizard
    spec.loader.exec_module(firstboot_wizard)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestFirstbootWizard(unittest.TestCase):
    """Test suite for firstboot state machine, credential hashing, profile.toml materialization, and CLI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-wizard-")
        self.config_out = os.path.join(self.temp_dir.name, "profile.toml")
        self.sentinel_path = os.path.join(self.temp_dir.name, ".firstboot_done")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_state_machine_transitions(self):
        engine = firstboot_wizard.FirstBootWizardEngine(
            config_out=self.config_out,
            sentinel_path=self.sentinel_path,
            mock=False,
        )
        self.assertEqual(engine.state, firstboot_wizard.WizardState.INIT)

        # Step 1: Welcome
        engine.step_welcome()
        self.assertEqual(engine.state, firstboot_wizard.WizardState.WELCOME)

        # Step 2: Auth
        engine.step_identity_auth(username="mios", password="SecretPassword123")
        self.assertEqual(engine.state, firstboot_wizard.WizardState.IDENTITY_AUTH)
        self.assertTrue(engine.config.password_hash.startswith("$6$"))

        # Step 3: Network
        engine.step_network(ssid="MiOS-Lab", psk="LabPassphrase", sec="wpa-psk")
        self.assertEqual(engine.state, firstboot_wizard.WizardState.NETWORK)

        # Step 4: AI Brain
        engine.step_ai_brain(lane="mios-llm-light", model="Qwen2.5-Coder-7B-Instruct-GGUF", vram_mb=8192)
        self.assertEqual(engine.state, firstboot_wizard.WizardState.AI_BRAIN)

        # Step 5: Finalize
        res = engine.step_finalize()
        self.assertEqual(engine.state, firstboot_wizard.WizardState.COMPLETED)
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(self.config_out))
        self.assertTrue(os.path.exists(self.sentinel_path))

    def test_run_mock_preseed(self):
        engine = firstboot_wizard.FirstBootWizardEngine(
            config_out=self.config_out,
            sentinel_path=self.sentinel_path,
            mock=True,
        )
        res = engine.run()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["config"]["username"], "mios")
        self.assertEqual(res["config"]["ai_lane"], "mios-llm-light")
        self.assertGreaterEqual(len(res["transitions"]), 4)

    def test_cli_execution_mock_json(self):
        test_args = [
            "firstboot_wizard.py",
            "--config-out", self.config_out,
            "--sentinel-path", self.sentinel_path,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = firstboot_wizard.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFirstbootWizard)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
