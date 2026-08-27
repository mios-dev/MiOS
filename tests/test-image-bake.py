#!/usr/bin/env python3
# AI-hint: Automated unit test suite for autonomous background OCI image synthesis service.
# AI-related: usr/libexec/mios/deploy/image_bake.py, usr/share/mios/mios.toml
"""Unit and integration test suite for ImageBakeEngine and image_bake CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "deploy", "image_bake.py")

spec = importlib.util.spec_from_file_location("image_bake", _TARGET_PATH)
if spec and spec.loader:
    image_bake = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = image_bake
    spec.loader.exec_module(image_bake)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestImageBake(unittest.TestCase):
    """Test suite for autonomous OCI image synthesis, commit creation, and bootc staging."""

    def test_load_staged_diffs_mock(self):
        with tempfile.TemporaryDirectory(prefix="mios-bake-staged-") as tmpdir:
            non_existent_staged = os.path.join(tmpdir, "nonexistent.json")
            engine = image_bake.ImageBakeEngine(staged_diffs_path=non_existent_staged, mock=True)
            staged = engine.load_staged_diffs()
            self.assertEqual(staged["total_approved"], 2)
            self.assertTrue(staged["bake_ready"])
            self.assertEqual(len(staged["approved_diffs"]), 2)

    def test_git_stage_and_commit_mock(self):
        engine = image_bake.ImageBakeEngine(mock=True)
        res = engine.git_stage_and_commit(["etc/skel/.bashrc"])
        self.assertEqual(res["status"], "committed")
        self.assertTrue(len(res["commit_sha"]) > 0)
        self.assertIn("chore(bake)", res["commit_msg"])

    def test_execute_build_mock(self):
        engine = image_bake.ImageBakeEngine(mock=True)
        res = engine.execute_build("1a2b3c4d")
        self.assertEqual(res["status"], "build_success")
        self.assertIn("baked-1a2b3c4d", res["image_tag"])

    def test_stage_bootc_switch_mock(self):
        engine = image_bake.ImageBakeEngine(mock=True)
        res = engine.stage_bootc_switch("localhost/mios:baked-1a2b3c4d")
        self.assertEqual(res["status"], "staged_for_next_boot")
        self.assertIn("bootc switch --staged", res["command"])

    def test_run_bake_and_history_recording(self):
        with tempfile.TemporaryDirectory(prefix="mios-bake-test-") as tmpdir:
            hist_file = os.path.join(tmpdir, "history.json")
            staged_file = os.path.join(tmpdir, "staged.json")
            staged_data = {
                "schema_version": "1.0",
                "approved_diffs": [
                    {"path": "var/lib/mios/ai/skills/custom-agent.md", "status": "??"}
                ],
            }
            with open(staged_file, "w", encoding="utf-8") as f:
                json.dump(staged_data, f)

            engine = image_bake.ImageBakeEngine(
                staged_diffs_path=staged_file,
                history_path=hist_file,
                mock=True,
            )
            record = engine.run_bake()
            self.assertEqual(record["status"], "staged_for_next_boot")
            self.assertEqual(record["health_verification"], "pending_firstboot")
            self.assertTrue(os.path.isfile(hist_file))

            history = engine.load_history()
            self.assertEqual(history["total_bakes"], 1)
            self.assertEqual(history["latest_bake"]["bake_id"], record["bake_id"])

    def test_quarantined_diffs_filtering(self):
        with tempfile.TemporaryDirectory(prefix="mios-bake-quarantine-") as tmpdir:
            quarantine_file = os.path.join(tmpdir, "quarantine.json")
            hist_file = os.path.join(tmpdir, "history.json")
            staged_file = os.path.join(tmpdir, "staged.json")

            quarantine_data = {
                "schema_version": "1.0",
                "quarantined_diffs": [
                    {
                        "quarantine_id": "q1",
                        "paths": ["etc/skel/.bashrc"],
                    }
                ],
            }
            with open(quarantine_file, "w", encoding="utf-8") as f:
                json.dump(quarantine_data, f)

            staged_data = {
                "schema_version": "1.0",
                "approved_diffs": [
                    {"path": "var/lib/mios/ai/skills/custom-agent.md"},
                    {"path": "etc/skel/.bashrc"},
                ],
            }
            with open(staged_file, "w", encoding="utf-8") as f:
                json.dump(staged_data, f)

            engine = image_bake.ImageBakeEngine(
                staged_diffs_path=staged_file,
                history_path=hist_file,
                quarantine_path=quarantine_file,
                mock=True,
            )
            record = engine.run_bake()
            self.assertIn("etc/skel/.bashrc", record["skipped_quarantined"])
            self.assertNotIn("etc/skel/.bashrc", record["staged_files"])
            self.assertIn("var/lib/mios/ai/skills/custom-agent.md", record["staged_files"])

    def test_cli_bake_mock(self):
        with tempfile.TemporaryDirectory(prefix="mios-bake-cli-") as tmpdir:
            hist_file = os.path.join(tmpdir, "history.json")
            test_args = ["image_bake.py", "--bake", "--history-file", hist_file, "--mock", "--json"]
            with patch.object(sys, "argv", test_args):
                exit_code = image_bake.main()
                self.assertEqual(exit_code, 0)

    def test_cli_status_mock(self):
        test_args = ["image_bake.py", "--status", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = image_bake.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestImageBake)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
