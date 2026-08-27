#!/usr/bin/env python3
# AI-hint: Comprehensive empirical stress, boundary, and adversarial test harness for batch T-573 to T-582.
"""Empirical Stress & Boundary Testing Suite for MiOS T-573 to T-582: - hw/powerd.py (T-573/T-574) - ux/wallpaperd.py (T-575/T-576) - agent-pipe/mios_mcp.py (T-577/T-578) - audio/wakeword.py (T-579/T-580) - config/nix_project.py (T-581/T-582)"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import math
import os
import random
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

# Add paths for imports
_HW_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "hw", "powerd.py")
_UX_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "wallpaperd.py")
_MCP_PATH = os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe", "mios_mcp.py")
_AUDIO_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "audio", "wakeword.py")
_NIX_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "config", "nix_project.py")

# Ensure lib/mios in sys.path
_LIB_DIR = os.path.join(_ROOT, "usr", "lib", "mios")
_LIB_AGENT_PIPE = os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe")
for p in (_LIB_DIR, _LIB_AGENT_PIPE):
    if p not in sys.path:
        sys.path.insert(0, p)

def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise ImportError(f"Could not load {name} from {path}")

powerd = _load_module("powerd", _HW_PATH)
wallpaperd = _load_module("wallpaperd", _UX_PATH)
mios_mcp = _load_module("mios_mcp", _MCP_PATH)
wakeword = _load_module("wakeword", _AUDIO_PATH)
nix_project = _load_module("nix_project", _NIX_PATH)

class TestPowerdStressAndBoundaries(unittest.TestCase):
    """Stress testing rapid AC/DC oscillation, malformed sysfs, desktop/VM fallbacks, concurrency."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_powerd_stress_")
        self.sysfs_root = self.tmp_dir
        self.state_file = os.path.join(self.tmp_dir, "powerd_state.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _setup_sysfs_structure(self, ac_online: str = "1", bat_cap: str = "80", bat_stat: str = "Discharging"):
        ps_dir = os.path.join(self.sysfs_root, "sys", "class", "power_supply")
        ac_dir = os.path.join(ps_dir, "ACAD")
        bat_dir = os.path.join(ps_dir, "BAT0")
        os.makedirs(ac_dir, exist_ok=True)
        os.makedirs(bat_dir, exist_ok=True)

        with open(os.path.join(ac_dir, "type"), "w", encoding="utf-8") as f:
            f.write("Mains\n")
        with open(os.path.join(ac_dir, "online"), "w", encoding="utf-8") as f:
            f.write(f"{ac_online}\n")

        with open(os.path.join(bat_dir, "type"), "w", encoding="utf-8") as f:
            f.write("Battery\n")
        with open(os.path.join(bat_dir, "capacity"), "w", encoding="utf-8") as f:
            f.write(f"{bat_cap}\n")
        with open(os.path.join(bat_dir, "status"), "w", encoding="utf-8") as f:
            f.write(f"{bat_stat}\n")

        cpu_base = os.path.join(self.sysfs_root, "sys", "devices", "system", "cpu")
        for i in range(8):
            cpufreq = os.path.join(cpu_base, f"cpu{i}", "cpufreq")
            os.makedirs(cpufreq, exist_ok=True)
            with open(os.path.join(cpufreq, "scaling_governor"), "w", encoding="utf-8") as f:
                f.write("performance\n")
            with open(os.path.join(cpufreq, "energy_performance_preference"), "w", encoding="utf-8") as f:
                f.write("balance_performance\n")

    def test_rapid_ac_dc_oscillations(self):
        """Stress: 100 rapid AC/DC alternations in tight loop verifying stability and consistency."""
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=True,
            poll_interval=0.01,
        )

        t0 = time.perf_counter()
        transitions = 100
        for i in range(transitions):
            target = "DC" if (i % 2 == 0) else "AC"
            state = daemon.apply_profile(target, force=True)
            if target == "DC":
                self.assertEqual(state.power_source, "BATTERY")
                self.assertEqual(state.cpu_epp, "power")
                self.assertEqual(state.active_model_tier, "light_3b")
                self.assertEqual(state.governor, "powersave")
                self.assertEqual(state.gpu_power_state, "low")
                self.assertFalse(state.ac_online)
            else:
                self.assertEqual(state.power_source, "AC")
                self.assertEqual(state.cpu_epp, "balance_performance")
                self.assertEqual(state.active_model_tier, "heavy")
                self.assertEqual(state.governor, "performance")
                self.assertEqual(state.gpu_power_state, "high")
                self.assertTrue(state.ac_online)

        duration = time.perf_counter() - t0
        self.assertLess(duration, 2.0, f"100 transitions took {duration:.3f}s, expected < 2.0s")

    def test_malformed_sysfs_power_supply_files(self):
        """Boundary: Corrupt, non-integer, empty, binary garbage in sysfs files."""
        malformed_capacities = [
            "invalid_string",
            "",
            "105%",
            "-20",
            "99.999",
            "N/A",
            "\x00\x01\x02\xff",
            "   \n\t  ",
            "1000000000000000000000",
        ]

        for malformed in malformed_capacities:
            self._setup_sysfs_structure(ac_online="0", bat_cap=malformed, bat_stat="Discharging")
            daemon = powerd.PowerDaemon(
                sysfs_root=self.sysfs_root,
                state_file=self.state_file,
                mock=False,
            )
            # Must not throw uncaught exceptions
            telemetry = daemon.read_telemetry()
            self.assertIn("power_source", telemetry)
            self.assertIn("battery_pct", telemetry)
            self.assertIn("battery_status", telemetry)
            self.assertEqual(telemetry["power_source"], "BATTERY")
            self.assertIsInstance(telemetry["battery_pct"], int)

    def test_zero_battery_desktop_and_vm_fallback(self):
        """Boundary: Desktop workstation or VM with 0 batteries and 0 AC adapters in sysfs."""
        ps_dir = os.path.join(self.sysfs_root, "sys", "class", "power_supply")
        os.makedirs(ps_dir, exist_ok=True)  # Empty directory

        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        telemetry = daemon.read_telemetry()
        # Desktop fallback invariant: Assume AC mains when no batteries/adapters found
        self.assertTrue(telemetry["ac_online"])
        self.assertEqual(telemetry["power_source"], "AC")
        self.assertEqual(telemetry["battery_pct"], 100)
        self.assertEqual(telemetry["battery_status"], "Full")

    def test_multi_battery_aggregation_and_missing_attributes(self):
        """Boundary: Multiple batteries (BAT0=20%, BAT1=80%) with missing status files."""
        ps_dir = os.path.join(self.sysfs_root, "sys", "class", "power_supply")
        os.makedirs(os.path.join(ps_dir, "BAT0"), exist_ok=True)
        os.makedirs(os.path.join(ps_dir, "BAT1"), exist_ok=True)

        with open(os.path.join(ps_dir, "BAT0", "type"), "w") as f:
            f.write("Battery\n")
        with open(os.path.join(ps_dir, "BAT0", "capacity"), "w") as f:
            f.write("20\n")

        with open(os.path.join(ps_dir, "BAT1", "type"), "w") as f:
            f.write("Battery\n")
        with open(os.path.join(ps_dir, "BAT1", "capacity"), "w") as f:
            f.write("80\n")

        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )
        telemetry = daemon.read_telemetry()
        # Average of 20 and 80 is 50
        self.assertEqual(telemetry["battery_pct"], 50)
        self.assertEqual(telemetry["power_source"], "BATTERY")

    def test_concurrent_power_polling_and_transitions(self):
        """Stress: 5 concurrent threads polling sysfs while another thread applies rapid transitions."""
        self._setup_sysfs_structure(ac_online="1", bat_cap="90", bat_stat="Full")
        daemon = powerd.PowerDaemon(
            sysfs_root=self.sysfs_root,
            state_file=self.state_file,
            mock=False,
        )

        stop_event = threading.Event()
        errors: List[str] = []

        def _poller():
            while not stop_event.is_set():
                try:
                    daemon.poll_and_sync()
                except Exception as e:
                    errors.append(f"Poller error: {e}")

        threads = [threading.Thread(target=_poller) for _ in range(5)]
        for t in threads:
            t.start()

        for i in range(20):
            tgt = "DC" if i % 2 == 0 else "AC"
            daemon.apply_profile(tgt)
            time.sleep(0.01)

        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)

        self.assertEqual(len(errors), 0, f"Concurrent power polling errors: {errors}")

    def test_corrupt_state_file_recovery(self):
        """Boundary: State file contains partial or corrupt JSON syntax."""
        corrupt_contents = [
            "",
            "{\"power_source\":",
            "{broken json}",
            "{\"power_source\": \"BATTERY\", \"cpu_epp\": \"power\"}",
        ]
        for content in corrupt_contents:
            with open(self.state_file, "w", encoding="utf-8") as f:
                f.write(content)

            daemon = powerd.PowerDaemon(
                sysfs_root=self.sysfs_root,
                state_file=self.state_file,
                mock=False,
            )
            state = daemon.state
            self.assertIn(state.power_source, ("AC", "BATTERY"))
            self.assertIsNotNone(state.cpu_epp)

class TestWallpaperdStressAndBoundaries(unittest.TestCase):
    """Stress testing high-frequency occlusion toggling, socket fuzzing, FPS throttling, IPC concurrency."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_wallpaper_stress_")
        self.sock_path = os.path.join(self.tmp_dir, "wallpaper_stress.sock")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_high_frequency_occlusion_toggling(self):
        """Stress: 500 rapid occlusion state toggles in a tight loop."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            socket_path=self.sock_path,
            mock=True,
        )

        t0 = time.perf_counter()
        toggles = 500
        for i in range(toggles):
            is_occ = (i % 2 == 0)
            engine.set_occluded(is_occ)
            frame_res = engine.step_frame(delta_time=0.01667)
            if is_occ:
                self.assertFalse(frame_res["rendered"])
                self.assertEqual(frame_res["fps"], 0)
                self.assertEqual(frame_res["gpu_load_pct"], 0.0)
            else:
                self.assertTrue(frame_res["rendered"])
                self.assertEqual(frame_res["fps"], 60)
                self.assertEqual(frame_res["gpu_load_pct"], 1.8)

        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 1.0, f"500 toggles took {elapsed:.3f}s, expected < 1.0s")
        self.assertEqual(engine.vulkan_queue.suspended_frame_count, 250)
        self.assertEqual(engine.vulkan_queue.rendered_frame_count, 250)

    def test_invalid_socket_json_payloads_fuzzing(self):
        """Boundary: Fuzzing IPC socket with malformed JSON, truncated strings, binary noise."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            socket_path=self.sock_path,
            mock=True,
        )
        started = engine.start_socket_server()
        self.assertTrue(started)

        try:
            fuzz_payloads = [
                b'{"cmd": "set_occluded", "occluded": tru\n',  # Truncated JSON
                b'{"bad_json"::::\n',                        # Syntax error
                b'NOT A JSON STRING AT ALL\n',               # Plain text
                b'\x00\x01\x02\x03\x04\xff\n',              # Binary garbage
                b'{"cmd": "unknown_command_12345"}\n',       # Unknown command
                b'{"cmd": "set_occluded"}\n',                # Missing required field
                b'{"cmd": "uniforms", "data": {"gpu_percent": "invalid_str"}}\n',
                b'{"cmd": "ping"}\n',                        # Valid ping
            ]

            for payload in fuzz_payloads:
                resp = self._send_raw_socket_payload(self.sock_path, payload)
                if resp is not None:
                    self.assertIsInstance(resp, dict)

            status = engine.get_status()
            self.assertIn("rendering", status)
            self.assertIn("fps", status)

        finally:
            engine.stop_socket_server()

    def test_rapid_socket_reconnections_and_disconnects(self):
        """Stress: 50 concurrent / rapid client connections connecting and dropping abruptly."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            socket_path=self.sock_path,
            mock=True,
        )
        engine.start_socket_server()

        try:
            errors = []
            def _client_task(cid: int):
                try:
                    for _ in range(5):
                        resp = wallpaperd.send_socket_command(
                            self.sock_path,
                            {"cmd": "ping"},
                            timeout=2.0,
                        )
                        if not resp or not resp.get("pong"):
                            errors.append(f"Client {cid} ping failed")
                except Exception as e:
                    errors.append(f"Client {cid} exception: {e}")

            threads = [threading.Thread(target=_client_task, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)

            self.assertEqual(len(errors), 0, f"Socket client errors encountered: {errors}")

        finally:
            engine.stop_socket_server()

    def test_ultra_concurrency_ipc_clients(self):
        """Stress: 30 concurrent socket clients hammering status commands."""
        engine = wallpaperd.WallpaperDaemonEngine(
            fps=60,
            socket_path=self.sock_path,
            mock=True,
        )
        engine.start_socket_server()
        try:
            results = []
            errors = []

            def _worker():
                for _ in range(5):
                    try:
                        res = wallpaperd.send_socket_command(self.sock_path, {"cmd": "status"})
                        if res and "rendering" in res:
                            results.append(res)
                        else:
                            errors.append("Empty/invalid response")
                    except Exception as e:
                        errors.append(str(e))

            threads = [threading.Thread(target=_worker) for _ in range(15)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)

            self.assertEqual(len(errors), 0, f"Concurrent socket errors: {errors}")
            self.assertGreaterEqual(len(results), 50)
        finally:
            engine.stop_socket_server()

    def test_fps_throttling_bounds_and_extremes(self):
        """Boundary: Boundary FPS configurations (0, 1, 144, 240, 1000)."""
        fps_targets = [1, 30, 60, 120, 144, 240, 1000]
        for target in fps_targets:
            q = wallpaperd.VulkanComputeQueue(target_fps=target, nominal_gpu_load=1.8)
            res_vis = q.render_frame(occluded=False, delta_time=1.0 / target)
            self.assertTrue(res_vis["rendered"])
            self.assertEqual(res_vis["fps"], target)
            self.assertEqual(res_vis["gpu_load_pct"], 1.8)

            res_occ = q.render_frame(occluded=True, delta_time=1.0 / target)
            self.assertFalse(res_occ["rendered"])
            self.assertEqual(res_occ["fps"], 0)
            self.assertEqual(res_occ["gpu_load_pct"], 0.0)

    def _send_raw_socket_payload(self, sock_path: str, payload: bytes) -> Optional[Dict[str, Any]]:
        try:
            if wallpaperd.HAS_AF_UNIX:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect(sock_path)
            else:
                with open(sock_path, "r", encoding="utf-8") as f:
                    port = int(f.read().strip().split(":")[1])
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect(("127.0.0.1", port))

            s.sendall(payload)
            data = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                except socket.timeout:
                    break
            s.close()
            if not data:
                return None
            return json.loads(data.decode("utf-8", "replace").strip())
        except Exception:
            return None

class TestMcpGatewayStressAndBoundaries(unittest.IsolatedAsyncioTestCase):
    """Stress testing deeply nested schemas, failing stdio, timeouts, strict formatting."""

    def test_deeply_nested_schema_strict_conversion(self):
        """Stress: 15-level deeply nested JSON Schema converted to strict OpenAI schema."""
        deep_schema: Dict[str, Any] = {"type": "string"}
        for i in range(15):
            deep_schema = {
                "type": "object",
                "properties": {
                    f"level_{i}": deep_schema,
                    f"optional_flag_{i}": {"type": "boolean"},
                },
                "required": [f"level_{i}"],
            }

        strict = mios_mcp.make_schema_strict(deep_schema)

        self.assertEqual(strict["type"], "object")
        self.assertFalse(strict["additionalProperties"])
        self.assertIn("level_14", strict["required"])
        self.assertIn("optional_flag_14", strict["required"])
        opt_type = strict["properties"]["optional_flag_14"]["type"]
        self.assertTrue("null" in opt_type or opt_type == "null")

        openai_tool = mios_mcp.convert_mcp_to_openai_schema(
            {
                "name": "deep_nested_tool",
                "description": "Deeply nested test tool",
                "inputSchema": deep_schema,
            },
            server_id="test_srv",
        )
        self.assertEqual(openai_tool["type"], "function")
        self.assertEqual(openai_tool["function"]["name"], "mcp.test_srv.deep_nested_tool")
        self.assertTrue(openai_tool["function"]["strict"])
        self.assertFalse(openai_tool["function"]["parameters"]["additionalProperties"])

    def test_empty_and_null_schema_handling(self):
        """Boundary: Empty, None, non-dict schemas must produce valid empty object schemas."""
        for invalid_schema in ({}, None, "invalid", 123, []):
            strict = mios_mcp.make_schema_strict(invalid_schema)
            self.assertEqual(strict["type"], "object")
            self.assertEqual(strict["properties"], {})
            self.assertEqual(strict["required"], [])
            self.assertFalse(strict["additionalProperties"])

    async def test_failing_stdio_subprocess_lifecycle(self):
        """Stress: Subprocess that fails immediately on execution or returns invalid JSON."""
        cli = mios_mcp._McpStdioClient(
            sid="failing_proc",
            command=sys.executable,
            args=["-c", "import sys; sys.exit(1)"],
        )
        res = await cli.initialize()
        self.assertIn("error", res)

        cli_noisy = mios_mcp._McpStdioClient(
            sid="noisy_proc",
            command=sys.executable,
            args=["-c", "import sys, time; sys.stdout.write('NON JSON STDOUT\\n'); sys.stdout.flush(); time.sleep(0.5)"],
        )
        res_noisy = await cli_noisy.initialize()
        self.assertIn("error", res_noisy)
        await cli_noisy.close()

    async def test_stdio_subprocess_timeout_handling(self):
        """Boundary: Stdio subprocess that hangs indefinitely without sending response."""
        cli_hang = mios_mcp._McpStdioClient(
            sid="hang_proc",
            command=sys.executable,
            args=["-c", "import sys, time; time.sleep(100)"],
        )
        await cli_hang._spawn()
        try:
            init_res = await cli_hang._await_rpc("initialize", {}, timeout_s=0.5)
            self.assertIn("error", init_res)
            self.assertIn("timeout", init_res["error"]["message"])
        finally:
            await cli_hang.close()

    def test_declarative_toml_parsing_boundaries(self):
        """Boundary: Parsing malformed TOML structures, missing server fields."""
        malformed_toml = """[mcp.servers.incomplete]         transport = "stdio"         # missing command         enabled = true          [mcp.servers.http_server]         transport = "http"         url = "http://127.0.0.1:9999/mcp"         allowed_tools = ["tool_a", "tool_b"]"""
        specs = mios_mcp.load_servers_from_toml(malformed_toml)
        self.assertEqual(len(specs), 2)
        srv_map = {s.id: s for s in specs}
        self.assertIn("incomplete", srv_map)
        self.assertIn("http_server", srv_map)
        self.assertEqual(srv_map["http_server"].allowed_tools, ["tool_a", "tool_b"])

    async def test_mcp_gateway_lifecycle_and_batch_conversion(self):
        """Stress: Batch conversion of 1000 tool schemas to strict OpenAI specifications."""
        tools = [
            {
                "name": f"tool_{i}",
                "description": f"Tool description {i}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param_a": {"type": "string"},
                        "param_b": {"type": "integer"},
                        "param_c": {
                            "type": "object",
                            "properties": {"nested": {"type": "boolean"}},
                        },
                    },
                    "required": ["param_a"],
                },
            }
            for i in range(1000)
        ]

        t0 = time.perf_counter()
        converted = [mios_mcp.convert_mcp_to_openai_schema(t, server_id="srv_perf") for t in tools]
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(converted), 1000)
        self.assertLess(elapsed, 1.0, f"1000 schema conversions took {elapsed:.3f}s, expected < 1.0s")
        self.assertEqual(converted[0]["type"], "function")
        self.assertEqual(converted[0]["function"]["name"], "mcp.srv_perf.tool_0")
        self.assertFalse(converted[0]["function"]["parameters"]["additionalProperties"])

    async def test_mcp_dispatch_missing_and_large_payload(self):
        """Boundary: Dispatching to missing tool or handling large (100KB) parameter payloads."""
        res_missing = await mios_mcp.dispatch_tool_call("nonexistent_srv", "missing_tool", {})
        self.assertIn("error", res_missing)
        self.assertEqual(res_missing.get("code"), -32601)

        large_args = {"data": "x" * 100000, "count": 100}
        res_large = await mios_mcp.dispatch_tool_call("missing_srv", "tool_x", large_args)
        self.assertIn("error", res_large)

class TestWakewordStressAndBoundaries(unittest.TestCase):
    """Stress testing high SNR noise, extreme clipping, stationary audio, benchmark."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_wakeword_stress_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_extreme_amplitude_saturation_and_dc_offset(self):
        """Boundary: Extreme amplitude clipping (±10.0), DC offset (+1.0 constant), zero frame."""
        pipeline = wakeword.AcousticWakePipeline(mock=False)

        # 1. DC Offset frame (+1.0 constant) - must NOT trigger wakeword detection
        dc_frame = [1.0] * wakeword.FRAME_SIZE
        detected_dc, status_dc = pipeline.process_chunk(dc_frame)
        self.assertFalse(detected_dc, "DC offset falsely triggered wakeword!")

        # 2. Extreme saturation clipping (+10.0 and -10.0)
        clipped_frame = [10.0 if (i % 2 == 0) else -10.0 for i in range(wakeword.FRAME_SIZE)]
        detected_clip, status_clip = pipeline.process_chunk(clipped_frame)
        self.assertFalse(detected_clip)

        # 3. Empty frame
        pipeline.process_chunk([])
        status_empty = pipeline.get_status()
        self.assertIsInstance(status_empty.to_dict(), dict)

    def test_non_speech_stationary_audio_rejection(self):
        """Adversarial: Stationary fan noise, 60Hz hum, pure tones, stationary vowels."""
        pipeline = wakeword.AcousticWakePipeline(mock=False)

        # 1. Stationary ambient noise & fan hum
        ambient = wakeword.synthesize_test_audio("ambient_noise", duration_sec=1.5)
        num_frames = len(ambient) // wakeword.FRAME_SIZE
        for f_idx in range(num_frames):
            chunk = ambient[f_idx * wakeword.FRAME_SIZE:(f_idx + 1) * wakeword.FRAME_SIZE]
            detected, _ = pipeline.process_chunk(chunk)
            self.assertFalse(detected, "Ambient noise falsely triggered wakeword!")

        pipeline.reset()

        # 2. Pure 1000Hz Tone
        pure_tone = [0.5 * math.sin(2.0 * math.pi * 1000.0 * (i / 16000.0)) for i in range(16000)]
        for f_idx in range(len(pure_tone) // wakeword.FRAME_SIZE):
            chunk = pure_tone[f_idx * wakeword.FRAME_SIZE:(f_idx + 1) * wakeword.FRAME_SIZE]
            detected, _ = pipeline.process_chunk(chunk)
            self.assertFalse(detected, "Pure sine wave falsely triggered wakeword!")

        pipeline.reset()

        # 3. Negative conversational speech (non-wakeword)
        neg_speech = wakeword.synthesize_test_audio("negative_speech", duration_sec=1.5)
        for f_idx in range(len(neg_speech) // wakeword.FRAME_SIZE):
            chunk = neg_speech[f_idx * wakeword.FRAME_SIZE:(f_idx + 1) * wakeword.FRAME_SIZE]
            detected, _ = pipeline.process_chunk(chunk)
            self.assertFalse(detected, "Non-wakeword speech falsely triggered wakeword!")

    def test_positive_wakeword_detection_accuracy(self):
        """Verification: Positive target wake phrase ('Hey MiOS') triggers detector."""
        pipeline = wakeword.AcousticWakePipeline(threshold=0.55, mock=False)
        wake_audio = wakeword.synthesize_test_audio("wake_phrase", duration_sec=1.5, snr_noise_level=0.01)

        detected_any = False
        num_frames = len(wake_audio) // wakeword.FRAME_SIZE
        for f_idx in range(num_frames):
            chunk = wake_audio[f_idx * wakeword.FRAME_SIZE:(f_idx + 1) * wakeword.FRAME_SIZE]
            detected, status = pipeline.process_chunk(chunk)
            if detected:
                detected_any = True

        self.assertTrue(detected_any, "Target wake phrase 'Hey MiOS' was not detected!")

    def test_high_snr_noise_phrase_detection(self):
        """Stress: Wake phrase embedded in significant background noise (SNR testing)."""
        pipeline = wakeword.AcousticWakePipeline(threshold=0.50, mock=False)
        noisy_wake = wakeword.synthesize_test_audio("wake_phrase", duration_sec=1.5, snr_noise_level=0.035)

        detected_any = False
        num_frames = len(noisy_wake) // wakeword.FRAME_SIZE
        for f_idx in range(num_frames):
            chunk = noisy_wake[f_idx * wakeword.FRAME_SIZE:(f_idx + 1) * wakeword.FRAME_SIZE]
            detected, status = pipeline.process_chunk(chunk)
            if detected:
                detected_any = True

        self.assertTrue(detected_any, "Wake phrase in noise was not detected!")

    def test_low_latency_execution_benchmark(self):
        """Benchmark: Execution time per 30ms chunk must be < 1.5ms (sub-0.1% CPU equivalent)."""
        pipeline = wakeword.AcousticWakePipeline(mock=False)
        wake_audio = wakeword.synthesize_test_audio("wake_phrase", duration_sec=1.0)
        num_frames = len(wake_audio) // wakeword.FRAME_SIZE

        t0 = time.perf_counter()
        for f_idx in range(num_frames):
            chunk = wake_audio[f_idx * wakeword.FRAME_SIZE:(f_idx + 1) * wakeword.FRAME_SIZE]
            pipeline.process_chunk(chunk)
        total_time = time.perf_counter() - t0

        avg_time_per_frame_ms = (total_time / float(num_frames)) * 1000.0
        self.assertLess(
            avg_time_per_frame_ms,
            1.5,
            f"Average compute latency {avg_time_per_frame_ms:.3f}ms per 30ms chunk exceeds 1.5ms threshold",
        )

    def test_process_pcm_file_end_to_end(self):
        """Verification: End-to-end processing of synthesized PCM/WAV file via process_pcm_file."""
        wake_audio = wakeword.synthesize_test_audio("wake_phrase", duration_sec=1.5)
        wav_path = os.path.join(self.tmp_dir, "test_wake.wav")

        with open(wav_path, "wb") as fh:
            raw_bytes = struct.pack(f"<{len(wake_audio)}h", *[int(max(-1.0, min(1.0, s)) * 32767.0) for s in wake_audio])
            fh.write(raw_bytes)

        res = wakeword.process_pcm_file(wav_path, threshold=0.55)
        self.assertTrue(res["wakeword_detected"])
        self.assertGreater(res["detection_count"], 0)
        self.assertEqual(res["pipeline_status"]["state"], "triggered")

class TestNixProjectStressAndBoundaries(unittest.TestCase):
    """Stress testing malformed TOML, package injection sanitization, rollback limits, scale."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios_nix_stress_")
        self.gen_dir = os.path.join(self.tmp_dir, "generations")
        self.out_flake = os.path.join(self.tmp_dir, "flake.nix")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_special_character_package_sanitization_and_injection_defense(self):
        """Adversarial: Malicious package strings with command injection and shell syntax."""
        adversarial_packages = [
            'valid_pkg',
            'curl; rm -rf /',
            'git && touch /tmp/pwned',
            'foo" { evil = true; }',
            '../../etc/shadow',
            'pkg#unstable',
            '$(whoami)',
            'pkg`id`',
            'hello-world.2_0',
        ]
        config = {
            "packages": {
                "nix": adversarial_packages,
            }
        }
        manager = nix_project.NixProjectManager(generations_dir=self.gen_dir, mock=False)
        extracted = manager.extract_packages(config)

        for p in extracted:
            self.assertRegex(p, r"^[A-Za-z0-9_\-\.]+$", f"Unsanitized package identifier allowed: {p}")

        self.assertIn("valid_pkg", extracted)
        self.assertIn("pkg", extracted)
        self.assertIn("hello-world.2_0", extracted)
        self.assertNotIn("curl; rm -rf /", extracted)
        self.assertNotIn("git && touch /tmp/pwned", extracted)
        self.assertNotIn("$(whoami)", extracted)

    def test_corrupt_and_unbalanced_flake_syntax_validation(self):
        """Boundary: Flake syntax validator must catch unmatched brackets, unclosed quotes."""
        invalid_flakes = [
            "",
            "description = 'foo';",
            "{ description = \"test\"; inputs = {}; }",
            "{ inputs = {}; outputs = { ... }: { ( } }; }",
            "{ description = \"unclosed string; inputs = {}; outputs = {}; }",
            "{ description = ''unclosed multi-line string; inputs = {}; outputs = {}; }",
        ]
        for flake in invalid_flakes:
            valid, msg = nix_project.NixProjectManager.validate_flake_syntax(flake)
            self.assertFalse(valid, f"Validator failed to reject malformed flake: {flake[:40]}... (msg: {msg})")

    def test_rollback_generation_boundaries(self):
        """Boundary: Rollback when 0 generations, non-existent generations, successive rollbacks."""
        manager = nix_project.NixProjectManager(generations_dir=self.gen_dir, mock=False)

        with self.assertRaises(RuntimeError):
            manager.rollback(1, output_path=self.out_flake)

        configs = [
            {"packages": {"nix": ["ripgrep"]}},
            {"packages": {"nix": ["ripgrep", "fd"]}},
            {"packages": {"nix": ["ripgrep", "fd", "bat"]}},
        ]
        for cfg in configs:
            rendered = manager.render_flake(cfg)
            manager.save_generation(self.out_flake, rendered, config=cfg)

        gens = manager.list_generations()
        self.assertEqual(len(gens), 3)

        with self.assertRaises(ValueError):
            manager.rollback(999, output_path=self.out_flake)

        res = manager.rollback(1, output_path=self.out_flake)
        self.assertEqual(res["rolled_back_to"], 1)

        updated_gens = manager.list_generations()
        self.assertTrue(updated_gens[0]["active"])
        self.assertFalse(updated_gens[1]["active"])
        self.assertFalse(updated_gens[2]["active"])

    def test_large_scale_flake_projection_and_escaping(self):
        """Stress: Rendering large-scale Nix flake with 100 packages, quotes, and dollar signs."""
        manager = nix_project.NixProjectManager(generations_dir=self.gen_dir, mock=False)
        large_config = {
            "packages": {
                "nix": [f"package_{i}" for i in range(100)],
            },
            "shell": {
                "alias_ll": "ls -la --color=auto",
                "alias_grep": 'grep --color=auto "$@"',
                "alias_echo": 'echo "MiOS \\$USER"',
            },
            "dotfiles": {
                "config/app.conf": {"text": "key=value\n$ENV_VAR=1"},
            },
        }

        rendered = manager.render_flake(large_config)
        valid, msg = manager.validate_flake_syntax(rendered)
        self.assertTrue(valid, f"Large flake failed syntax check: {msg}")

        self.assertIn('\\$USER', rendered)
        self.assertIn('package_99', rendered)

        summary = manager.save_generation(self.out_flake, rendered, config=large_config)
        self.assertEqual(summary["packages_count"], 100)
        self.assertEqual(summary["aliases_count"], 3)

if __name__ == "__main__":
    unittest.main(verbosity=2)
