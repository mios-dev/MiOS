#!/usr/bin/env python3
# AI-hint: Unit and integration tests for PowerShell execution policy and developer registry configurator.
# AI-related: usr/libexec/mios/win/ps_policy_config.py, usr/share/mios/mios.toml, usr/libexec/mios/win/unattend_gen.py
"""Unit and integration test suite for PowerShellPolicyEngine and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "win", "ps_policy_config.py")

spec = importlib.util.spec_from_file_location("ps_policy_config", _TARGET_PATH)
if spec and spec.loader:
    ps_policy_config = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ps_policy_config
    spec.loader.exec_module(ps_policy_config)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestPsPolicyConfig(unittest.TestCase):
    """Test suite for PowerShell RemoteSigned policy, Developer Mode, Long Paths, and profile scripts."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-ps-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_reg_content(self):
        cfg = ps_policy_config.PolicyConfig(
            execution_policy=ps_policy_config.ExecutionPolicy.REMOTE_SIGNED,
            enable_dev_mode=True,
            enable_long_paths=True,
        )
        engine = ps_policy_config.PowerShellPolicyEngine(cfg, mock=True)
        reg_text = engine.generate_reg_content()

        self.assertIn("Windows Registry Editor Version 5.00", reg_text)
        self.assertIn('"ExecutionPolicy"="RemoteSigned"', reg_text)
        self.assertIn('"AllowDevelopmentWithoutDevLicense"=dword:00000001', reg_text)
        self.assertIn('"LongPathsEnabled"=dword:00000001', reg_text)

    def test_generate_ps1_content(self):
        cfg = ps_policy_config.PolicyConfig(
            execution_policy=ps_policy_config.ExecutionPolicy.REMOTE_SIGNED,
            enable_dev_mode=True,
            enable_long_paths=True,
            setup_profile=True,
            ai_endpoint="http://127.0.0.1:8640/v1",
        )
        engine = ps_policy_config.PowerShellPolicyEngine(cfg, mock=True)
        ps1_text = engine.generate_ps1_content()

        self.assertIn("Set-ExecutionPolicy -Scope LocalMachine -ExecutionPolicy RemoteSigned -Force", ps1_text)
        self.assertIn("AllowDevelopmentWithoutDevLicense", ps1_text)
        self.assertIn("LongPathsEnabled", ps1_text)
        self.assertIn("$env:MIOS_AI_ENDPOINT = 'http://127.0.0.1:8640/v1'", ps1_text)
        self.assertIn("function mios { & wsl.exe -d MiOS-DEV -- mios $args }", ps1_text)

    def test_generate_profile_script(self):
        cfg = ps_policy_config.PolicyConfig(ai_endpoint="http://localhost:8640/v1")
        engine = ps_policy_config.PowerShellPolicyEngine(cfg, mock=True)
        prof_text = engine.generate_profile_script()
        self.assertIn("$OutputEncoding = [System.Text.Encoding]::UTF8", prof_text)
        self.assertIn("$env:MIOS_AI_ENDPOINT = 'http://localhost:8640/v1'", prof_text)

    def test_run_emit_files(self):
        reg_path = os.path.join(self.temp_dir.name, "policy.reg")
        cfg = ps_policy_config.PolicyConfig()
        engine = ps_policy_config.PowerShellPolicyEngine(cfg, mock=False)
        res = engine.run(emit_reg=True, output_path=reg_path)

        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(reg_path))

    def test_cli_execution_mock_json(self):
        test_args = [
            "ps_policy_config.py",
            "--policy", "RemoteSigned",
            "--ai-endpoint", "http://127.0.0.1:8640/v1",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = ps_policy_config.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPsPolicyConfig)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
