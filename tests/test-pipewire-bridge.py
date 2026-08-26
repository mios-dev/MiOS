#!/usr/bin/env python3
# AI-hint: Automated unit test suite for low-latency PipeWire JACK inter-VM audio bridge.
# AI-related: usr/libexec/mios/virt/pipewire_bridge.py, usr/share/doc/mios/manual/ch67-discrete-gpu-vfio-looking-glass-and-displays.md
"""Unit tests for low-latency PipeWire JACK inter-VM audio bridge and Scream IVSHMEM sink."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_PB_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "pipewire_bridge.py")

spec = importlib.util.spec_from_file_location("pipewire_bridge", _PB_PATH)
if spec and spec.loader:
    pipewire_bridge = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pipewire_bridge
    spec.loader.exec_module(pipewire_bridge)
else:
    raise ImportError(f"Could not load pipewire_bridge module from {_PB_PATH}")


class TestPipeWireBridge(unittest.TestCase):
    """Validates low-latency buffer math, SLA thresholds, IVSHMEM XML, and systemd units."""

    def setUp(self) -> None:
        self.manager = pipewire_bridge.PipeWireBridgeManager(
            shm_path="/dev/shm/scream",
            size_mb=2,
            sample_rate=48000,
            quantum=64,
            backend="jack",
            node_name="scream-ivshmem-bridge",
        )

    def test_latency_math_exactness(self) -> None:
        # 64 / 48000 = 1.333 ms
        lat_64_48k = pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(64, 48000)
        self.assertEqual(lat_64_48k, 1.333)

        # 32 / 48000 = 0.667 ms
        lat_32_48k = pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(32, 48000)
        self.assertEqual(lat_32_48k, 0.667)

        # 128 / 96000 = 1.333 ms
        lat_128_96k = pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(128, 96000)
        self.assertEqual(lat_128_96k, 1.333)

        # 128 / 192000 = 0.667 ms
        lat_128_192k = pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(128, 192000)
        self.assertEqual(lat_128_192k, 0.667)

        # 128 / 44100 = 2.902 ms
        lat_128_44k = pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(128, 44100)
        self.assertEqual(lat_128_44k, 2.902)

    def test_latency_math_error_handling(self) -> None:
        with self.assertRaises(ValueError):
            pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(0, 48000)
        with self.assertRaises(ValueError):
            pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(64, 0)
        with self.assertRaises(ValueError):
            pipewire_bridge.PipeWireBridgeManager.calculate_latency_ms(-1, 48000)

    def test_sla_enforcement(self) -> None:
        # 64 / 48000 = 1.333 ms -> <= 5.0ms PASS
        res_pass = self.manager.validate_latency_sla(quantum=64, sample_rate=48000)
        self.assertTrue(res_pass["passed"])
        self.assertEqual(res_pass["status"], "pass")
        self.assertLessEqual(res_pass["latency_ms"], 5.0)

        # 256 / 48000 = 5.333 ms -> > 5.0ms FAIL
        res_fail = self.manager.validate_latency_sla(quantum=256, sample_rate=48000)
        self.assertFalse(res_fail["passed"])
        self.assertEqual(res_fail["status"], "fail")
        self.assertGreater(res_fail["latency_ms"], 5.0)

    def test_pipewire_env_generation(self) -> None:
        env = self.manager.generate_pipewire_env()
        self.assertEqual(env["PIPEWIRE_LATENCY"], "64/48000")
        self.assertEqual(env["PIPEWIRE_QUANTUM"], "64/48000")
        self.assertEqual(env["PIPEWIRE_RATE"], "1/48000")
        self.assertEqual(env["JACK_PROMISCUOUS_SERVER"], "1")
        self.assertEqual(env["PIPEWIRE_NODE_NAME"], "scream-ivshmem-bridge")

    def test_ivshmem_xml_generation(self) -> None:
        xml = self.manager.generate_ivshmem_xml()
        self.assertIn('<shmem name="scream">', xml)
        self.assertIn('<model type="ivshmem-plain"/>', xml)
        self.assertIn('<size unit="M">2</size>', xml)

    def test_systemd_service_generation(self) -> None:
        # System unit
        svc_sys = self.manager.generate_systemd_service(user_unit=False)
        self.assertIn("[Unit]", svc_sys)
        self.assertIn("Description=MiOS Scream IVSHMEM to PipeWire JACK Low-Latency Audio Bridge", svc_sys)
        self.assertIn("After=pipewire.service", svc_sys)
        self.assertIn('Environment="PIPEWIRE_LATENCY=64/48000"', svc_sys)
        self.assertIn("ExecStart=/usr/bin/scream -m /dev/shm/scream -o jack -t 64", svc_sys)
        self.assertIn("WantedBy=multi-user.target", svc_sys)

        # User unit
        svc_user = self.manager.generate_systemd_service(user_unit=True)
        self.assertIn("WantedBy=default.target", svc_user)

    def test_audio_node_mock_validation(self) -> None:
        node_res = self.manager.validate_audio_nodes(mock=True)
        self.assertEqual(node_res["status"], "pass")
        self.assertTrue(node_res["accessible"])

    def test_verify_all(self) -> None:
        res = self.manager.verify_all(mock=True)
        self.assertEqual(res["status"], "pass")
        self.assertTrue(res["sla_passed"])
        self.assertEqual(res["checks"]["latency_sla"], "pass")
        self.assertEqual(res["checks"]["xml_generation"], "pass")
        self.assertEqual(res["checks"]["env_generation"], "pass")
        self.assertEqual(res["checks"]["service_generation"], "pass")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeWireBridge)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
