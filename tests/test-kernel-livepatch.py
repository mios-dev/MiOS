#!/usr/bin/env python3
# AI-hint: Automated unit test suite for MOK-signed kernel livepatching, microcode reload, and UKI staging.
# AI-related: usr/libexec/mios/sec/livepatch_mgr.py, usr/share/mios/mios.toml
"""Unit and integration test suite for LivepatchManager and livepatch_mgr CLI (T-546)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "livepatch_mgr.py")

spec = importlib.util.spec_from_file_location("livepatch_mgr", _TARGET_PATH)
if spec and spec.loader:
    livepatch_mgr = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = livepatch_mgr
    spec.loader.exec_module(livepatch_mgr)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestKernelLivepatch(unittest.TestCase):
    """Test suite for LivepatchManager operations, MOK signature checks, and UKI staging."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-test-livepatch-")
        self.state_file = os.path.join(self.tmpdir.name, "livepatch-state.json")
        self.staging_dir = os.path.join(self.tmpdir.name, "uki-staging")
        self.sys_dir = os.path.join(self.tmpdir.name, "sys-livepatch")
        os.makedirs(self.sys_dir, exist_ok=True)
        os.makedirs(self.staging_dir, exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_verify_mok_signature_mock_valid(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        sig = mgr.verify_mok_signature("/lib/modules/kpatch-cve-2026-1001.ko")
        self.assertTrue(sig["valid"])
        self.assertEqual(sig["signer"], "MiOS-MOK-CA-2026")
        self.assertIn("key_id", sig)

    def test_verify_mok_signature_mock_unsigned(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        sig = mgr.verify_mok_signature("/tmp/unsigned_hack_exploit.ko")
        self.assertFalse(sig["valid"])
        self.assertIn("Missing or untrusted", sig["reason"])

    def test_load_patch_success_mock(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        res = mgr.load_patch("/lib/modules/kpatch-cve-2026-1001.ko", "cve_2026_1001")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "loaded")
        self.assertEqual(res["patch_name"], "cve_2026_1001")

        patches = mgr.list_patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0]["patch_name"], "cve_2026_1001")

    def test_load_patch_rejected_unsigned(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        res = mgr.load_patch("/tmp/unsigned_patch.ko")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "signature_rejected")

    def test_unload_patch_mock(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        mgr.load_patch("/lib/modules/kpatch-fix.ko", "kpatch_fix")
        self.assertEqual(len(mgr.list_patches()), 1)

        res = mgr.unload_patch("kpatch_fix")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "unloaded")
        self.assertEqual(len(mgr.list_patches()), 0)

    def test_reload_microcode_mock(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        res = mgr.reload_microcode()
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "microcode_reloaded")
        self.assertEqual(res["new_version"], "0x000000a2")
        self.assertIsNotNone(res["timestamp"])

    def test_stage_uki_update_mock(self):
        mgr = livepatch_mgr.LivepatchManager(
            state_path=self.state_file,
            staging_dir=self.staging_dir,
            mock=True,
        )
        res = mgr.stage_uki_update("/boot/efi/EFI/Linux/mios-6.10.uki")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "uki_staged")
        self.assertIn("sha256", res["staged_uki"])

    def test_status_overview(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=True)
        mgr.load_patch("/lib/modules/kpatch-sec.ko", "sec_patch")
        status = mgr.get_status()
        self.assertEqual(status["active_patches_count"], 1)
        self.assertEqual(status["mok_enforcement"], "strict")
        self.assertEqual(status["uki_model"], "shim -> systemd-boot -> signed UKI")

    def test_file_signature_detection_real_bytes(self):
        mgr = livepatch_mgr.LivepatchManager(state_path=self.state_file, mock=False)
        test_ko = os.path.join(self.tmpdir.name, "signed_test.ko")
        with open(test_ko, "wb") as f:
            f.write(b"\x7fELF" + b"\x00" * 200 + b"~Module signature appended~" + b"\x00" * 40)

        sig = mgr.verify_mok_signature(test_ko)
        self.assertTrue(sig["valid"])
        self.assertIn("Module signature", sig["reason"])

    def test_main_cli_execution_mock(self):
        with patch.object(sys, "argv", ["livepatch_mgr.py", "--mock", "--status", "--json"]):
            code = livepatch_mgr.main()
            self.assertEqual(code, 0)

        with patch.object(sys, "argv", ["livepatch_mgr.py", "--mock", "--reload-microcode", "--json"]):
            code = livepatch_mgr.main()
            self.assertEqual(code, 0)

if __name__ == "__main__":
    unittest.main()
