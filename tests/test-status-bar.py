#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Quickshell/QML system status bar AI telemetry component.
# AI-related: usr/libexec/mios/ux/status_bar.py, usr/share/mios/mios.toml
"""Unit and integration test suite for StatusBarEngine and status_bar CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "status_bar.py")

spec = importlib.util.spec_from_file_location("status_bar", _TARGET_PATH)
if spec and spec.loader:
    status_bar = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = status_bar
    spec.loader.exec_module(status_bar)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestStatusBar(unittest.TestCase):
    """Test suite for AI brain status bar streaming and QML component generation."""

    def test_status_bar_state_dataclass(self):
        state = status_bar.StatusBarState(
            model_id="Qwen2.5-Coder-7B",
            agent_status="thinking",
            token_rate_tps=42.5,
        )
        self.assertEqual(state.model_id, "Qwen2.5-Coder-7B")
        self.assertEqual(state.agent_status, "thinking")
        self.assertEqual(state.token_rate_tps, 42.5)

    def test_engine_init_and_palette(self):
        engine = status_bar.StatusBarEngine(mock=True)
        self.assertTrue(engine.mock)
        self.assertIn("bg", engine.palette)
        self.assertIn("accent", engine.palette)
        self.assertIn("success", engine.palette)

    def test_fetch_snapshot_mock(self):
        engine = status_bar.StatusBarEngine(mock=True)
        snapshot = engine.fetch_snapshot()
        self.assertEqual(snapshot.model_id, "Qwen2.5-Coder-7B-Instruct-GGUF")
        self.assertEqual(snapshot.agent_status, "deliberating")
        self.assertEqual(snapshot.token_rate_tps, 34.8)
        self.assertEqual(snapshot.vram_used_mb, 5640)
        self.assertEqual(snapshot.vram_total_mb, 16384)
        self.assertTrue(snapshot.endpoint_healthy)

    def test_generate_qml(self):
        engine = status_bar.StatusBarEngine(mock=True)
        qml = engine.generate_qml()
        self.assertIn("import QtQuick 2.15", qml)
        self.assertIn("import QtQuick.Layouts 1.15", qml)
        self.assertIn("Rectangle {", qml)
        self.assertIn("property string modelName:", qml)
        self.assertIn("property string agentStatus:", qml)
        self.assertIn("property real tokenRate:", qml)

    def test_run_stream(self):
        engine = status_bar.StatusBarEngine(mock=True)
        snaps = engine.run_stream(interval_sec=0.01, max_iterations=2)
        self.assertEqual(len(snaps), 2)
        self.assertEqual(snaps[0]["model_id"], "Qwen2.5-Coder-7B-Instruct-GGUF")

    def test_cli_snapshot_mock(self):
        test_args = ["status_bar.py", "--snapshot", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = status_bar.main()
            self.assertEqual(exit_code, 0)

    def test_cli_stream_mock(self):
        test_args = ["status_bar.py", "--stream", "--count", "2", "--interval", "0.01", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = status_bar.main()
            self.assertEqual(exit_code, 0)

    def test_cli_generate_qml_mock(self):
        test_args = ["status_bar.py", "--generate-qml", "AiStatus.qml", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = status_bar.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStatusBar)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
