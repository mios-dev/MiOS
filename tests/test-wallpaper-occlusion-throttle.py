#!/usr/bin/env python3
# AI-hint: Automated unit and benchmark test suite for living wallpaper occlusion throttling and Vulkan compute pacing.
# AI-related: usr/libexec/mios/ux/wallpaperd.py, usr/lib/systemd/user/mios-wallpaper.service, usr/share/mios/mios.toml
"""
Automated unit, frame pacing benchmark, and IPC telemetry test suite for
the MiOS Living Wallpaper Occlusion Engine (mios-wallpaperd).

Validates:
1. Active rendering at 60 FPS with < 2% GPU load (nominal 1.8%) when desktop is visible.
2. Suspension to 0 FPS with 0.0% GPU load when desktop is occluded by open windows.
3. Low-priority Vulkan compute queue scheduling (VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT).
4. Uniform and telemetry IPC socket listener communication over Unix domain socket.
5. CLI controls (--status, --json, --set-occluded, --mock, --daemon, --socket).
6. Systemd user service unit specification compliance.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

# Load module dynamically
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "wallpaperd.py")
_SERVICE_PATH = os.path.join(_ROOT, "usr", "lib", "systemd", "user", "mios-wallpaper.service")

spec = importlib.util.spec_from_file_location("wallpaperd", _TARGET_PATH)
if spec and spec.loader:
    wallpaperd = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = wallpaperd
    spec.loader.exec_module(wallpaperd)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestWallpaperOcclusionThrottle(unittest.TestCase):
    """Test suite for living wallpaper occlusion throttling, frame pacing, and IPC."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sock_path = os.path.join(self.temp_dir.name, "test-wallpaper.sock")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_visible_state_frame_pacing_and_gpu_load(self):
        """Verify 60 FPS rendering with <2% GPU load (nominal 1.8%) when desktop is visible."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            mode="ambient",
            socket_path=self.sock_path,
            mock=True,
            initial_occluded=False,
        )

        status = engine.get_status()
        self.assertTrue(status["rendering"], "Engine should be actively rendering when visible")
        self.assertEqual(status["fps"], 60, "Framerate should target 60 FPS")
        self.assertAlmostEqual(status["gpu_load_pct"], 1.8, delta=0.2, msg="GPU load should be nominal 1.8%")
        self.assertLess(status["gpu_load_pct"], 2.0, "GPU load must remain < 2.0% for AI inference headroom")
        self.assertFalse(status["occluded"], "Desktop occlusion flag should be False")
        self.assertEqual(status["vulkan_queue_priority"], "VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT")

        # Step 60 frames and verify duty cycle
        for i in range(60):
            res = engine.step_frame(delta_time=0.01667)
            self.assertTrue(res["rendered"])
            self.assertEqual(res["fps"], 60)
            self.assertAlmostEqual(res["gpu_load_pct"], 1.8, delta=0.2)
            self.assertFalse(res["occluded"])

        self.assertEqual(engine.vulkan_queue.rendered_frame_count, 60)
        self.assertEqual(engine.vulkan_queue.suspended_frame_count, 0)
        self.assertGreater(engine.vulkan_queue.total_duty_time_s, 0.0)

    def test_02_occluded_state_throttle_to_zero_fps(self):
        """Verify rendering suspends to 0 FPS and 0.0% GPU load on window occlusion."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            mode="ambient",
            socket_path=self.sock_path,
            mock=True,
            initial_occluded=False,
        )

        # Trigger window occlusion
        updated_status = engine.set_occluded(True)
        self.assertFalse(updated_status["rendering"], "Rendering must be False when occluded")
        self.assertEqual(updated_status["fps"], 0, "Framerate must drop to 0 FPS when occluded")
        self.assertEqual(updated_status["gpu_load_pct"], 0.0, "GPU load must drop to 0.0% when occluded")
        self.assertTrue(updated_status["occluded"], "Occlusion flag must be True")

        # Step 60 ticks in occluded state
        for _ in range(60):
            res = engine.step_frame(delta_time=0.01667)
            self.assertFalse(res["rendered"])
            self.assertEqual(res["fps"], 0)
            self.assertEqual(res["gpu_load_pct"], 0.0)
            self.assertEqual(res["duty_cycle"], 0.0)
            self.assertTrue(res["occluded"])

        self.assertEqual(engine.vulkan_queue.suspended_frame_count, 60)
        self.assertEqual(engine.vulkan_queue.rendered_frame_count, 0)

    def test_03_resume_visible_after_occlusion(self):
        """Verify seamless transition between occluded (0 FPS) and visible (60 FPS)."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            mode="ambient",
            socket_path=self.sock_path,
            mock=True,
            initial_occluded=True,
        )

        # Initial occluded
        st1 = engine.get_status()
        self.assertFalse(st1["rendering"])
        self.assertEqual(st1["fps"], 0)
        self.assertEqual(st1["gpu_load_pct"], 0.0)

        # Transition to visible
        st2 = engine.set_occluded(False)
        self.assertTrue(st2["rendering"])
        self.assertEqual(st2["fps"], 60)
        self.assertAlmostEqual(st2["gpu_load_pct"], 1.8, delta=0.2)

        # Transition back to occluded
        st3 = engine.set_occluded(True)
        self.assertFalse(st3["rendering"])
        self.assertEqual(st3["fps"], 0)
        self.assertEqual(st3["gpu_load_pct"], 0.0)

    def test_04_vulkan_compute_priority_queue(self):
        """Verify Vulkan compute queue priority is low-priority to yield to AI models."""
        queue = wallpaperd.VulkanComputeQueue(
            priority="VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT",
            target_fps=60,
            nominal_gpu_load=1.8,
        )
        self.assertEqual(queue.priority, "VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT")

        # Step frame when visible
        f1 = queue.render_frame(occluded=False, delta_time=0.01667)
        self.assertTrue(f1["rendered"])
        self.assertEqual(f1["queue_priority"], "VK_QUEUE_GLOBAL_PRIORITY_LOW_EXT")

        # Step frame when occluded
        f2 = queue.render_frame(occluded=True, delta_time=0.01667)
        self.assertFalse(f2["rendered"])
        self.assertEqual(f2["fps"], 0)
        self.assertEqual(f2["gpu_load_pct"], 0.0)

    def test_05_telemetry_socket_server_and_ipc_commands(self):
        """Verify Unix domain socket IPC communication, command dispatching, and status retrieval."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            mode="ambient",
            socket_path=self.sock_path,
            mock=True,
        )

        started = engine.start_socket_server()
        self.assertTrue(started, "Socket server should start successfully")

        try:
            # Test ping command
            ping_resp = wallpaperd.send_socket_command(self.sock_path, {"cmd": "ping"})
            self.assertIsNotNone(ping_resp)
            self.assertEqual(ping_resp.get("status"), "ok")
            self.assertTrue(ping_resp.get("pong"))

            # Test status command
            status_resp = wallpaperd.send_socket_command(self.sock_path, {"cmd": "status"})
            self.assertIsNotNone(status_resp)
            self.assertTrue(status_resp.get("rendering"))
            self.assertEqual(status_resp.get("fps"), 60)
            self.assertAlmostEqual(status_resp.get("gpu_load_pct"), 1.8, delta=0.2)
            self.assertFalse(status_resp.get("occluded"))

            # Test set_occluded true over IPC socket
            occ_resp = wallpaperd.send_socket_command(
                self.sock_path,
                {"cmd": "set_occluded", "occluded": True},
            )
            self.assertIsNotNone(occ_resp)
            self.assertFalse(occ_resp.get("rendering"))
            self.assertEqual(occ_resp.get("fps"), 0)
            self.assertEqual(occ_resp.get("gpu_load_pct"), 0.0)
            self.assertTrue(occ_resp.get("occluded"))

            # Test set_occluded false over IPC socket
            vis_resp = wallpaperd.send_socket_command(
                self.sock_path,
                {"cmd": "set_occluded", "occluded": False},
            )
            self.assertIsNotNone(vis_resp)
            self.assertTrue(vis_resp.get("rendering"))
            self.assertEqual(vis_resp.get("fps"), 60)
            self.assertAlmostEqual(vis_resp.get("gpu_load_pct"), 1.8, delta=0.2)
            self.assertFalse(vis_resp.get("occluded"))

            # Test uniform update over IPC socket
            uniform_resp = wallpaperd.send_socket_command(
                self.sock_path,
                {"cmd": "uniforms", "data": {"cpu_percent": 45.0, "ai_inference_tps": 32.1}},
            )
            self.assertIsNotNone(uniform_resp)
            self.assertEqual(uniform_resp.get("status"), "ok")
            self.assertEqual(engine.uniforms.cpu_percent, 45.0)
            self.assertEqual(engine.uniforms.ai_inference_tps, 32.1)
        finally:
            engine.stop_socket_server()

    def test_06_mock_mode_and_telemetry_uniforms(self):
        """Verify telemetry uniform container and mock mode execution."""
        engine = wallpaperd.WallpaperDaemonEngine(mock=True)
        engine.update_uniforms({"cpu_percent": 28.5, "gpu_percent": 1.2, "speed_factor": 1.35})
        self.assertEqual(engine.uniforms.cpu_percent, 28.5)
        self.assertEqual(engine.uniforms.gpu_percent, 1.2)
        self.assertEqual(engine.uniforms.speed_factor, 1.35)

        st = engine.get_status()
        self.assertTrue(st["mock"])
        self.assertEqual(st["mode"], "ambient")

    def test_07_cli_status_json_mock(self):
        """Verify CLI execution of `wallpaperd.py --status --json --mock`."""
        test_args = ["wallpaperd.py", "--status", "--json", "--mock", "--socket", self.sock_path]
        buf = io.StringIO()
        with patch.object(sys, "argv", test_args), patch("sys.stdout", buf):
            exit_code = wallpaperd.main()
            self.assertEqual(exit_code, 0)

        output = buf.getvalue().strip()
        data = json.loads(output)
        self.assertIn("rendering", data)
        self.assertIn("fps", data)
        self.assertIn("gpu_load_pct", data)
        self.assertIn("occluded", data)
        self.assertTrue(data["rendering"])
        self.assertEqual(data["fps"], 60)
        self.assertAlmostEqual(data["gpu_load_pct"], 1.8, delta=0.2)
        self.assertFalse(data["occluded"])

    def test_08_cli_set_occluded_json_mock(self):
        """Verify CLI execution of `wallpaperd.py --set-occluded true|false --json --mock`."""
        # Test occluded true
        test_args_true = [
            "wallpaperd.py",
            "--set-occluded", "true",
            "--json",
            "--mock",
            "--socket", self.sock_path,
        ]
        buf_true = io.StringIO()
        with patch.object(sys, "argv", test_args_true), patch("sys.stdout", buf_true):
            code_true = wallpaperd.main()
            self.assertEqual(code_true, 0)

        data_true = json.loads(buf_true.getvalue().strip())
        self.assertFalse(data_true["rendering"])
        self.assertEqual(data_true["fps"], 0)
        self.assertEqual(data_true["gpu_load_pct"], 0.0)
        self.assertTrue(data_true["occluded"])

        # Test occluded false
        test_args_false = [
            "wallpaperd.py",
            "--set-occluded", "false",
            "--json",
            "--mock",
            "--socket", self.sock_path,
        ]
        buf_false = io.StringIO()
        with patch.object(sys, "argv", test_args_false), patch("sys.stdout", buf_false):
            code_false = wallpaperd.main()
            self.assertEqual(code_false, 0)

        data_false = json.loads(buf_false.getvalue().strip())
        self.assertTrue(data_false["rendering"])
        self.assertEqual(data_false["fps"], 60)
        self.assertAlmostEqual(data_false["gpu_load_pct"], 1.8, delta=0.2)
        self.assertFalse(data_false["occluded"])

    def test_09_cli_daemon_iterations_mock(self):
        """Verify CLI execution of `wallpaperd.py --daemon --mock --iterations 10 --json`."""
        test_args = [
            "wallpaperd.py",
            "--daemon",
            "--mock",
            "--iterations", "10",
            "--json",
            "--socket", self.sock_path,
        ]
        buf = io.StringIO()
        with patch.object(sys, "argv", test_args), patch("sys.stdout", buf):
            code = wallpaperd.main()
            self.assertEqual(code, 0)

        output = buf.getvalue().strip()
        data = json.loads(output)
        self.assertTrue(data.get("daemon_started"))

    def test_10_systemd_user_service_spec(self):
        """Verify systemd user service unit exists and contains required directives."""
        self.assertTrue(os.path.exists(_SERVICE_PATH), f"Service unit {_SERVICE_PATH} must exist")
        with open(_SERVICE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("ExecStart=/usr/libexec/mios/ux/wallpaperd.py --daemon", content)
        self.assertIn("Restart=on-failure", content)
        self.assertIn("[Unit]", content)
        self.assertIn("[Service]", content)
        self.assertIn("[Install]", content)
        self.assertIn("graphical-session.target", content)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWallpaperOcclusionThrottle)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
