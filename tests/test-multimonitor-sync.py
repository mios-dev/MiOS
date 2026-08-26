#!/usr/bin/env python3
# AI-hint: Automated unit test suite for multi-monitor Looking Glass display geometry and cursor synchronizer.
# AI-related: usr/libexec/mios/display/multimonitor_sync.py, usr/share/doc/mios/manual/ch67-discrete-gpu-vfio-looking-glass-and-displays.md
"""Unit tests for multi-monitor Looking Glass geometry, IVSHMEM sizing, cursor warp, and launchers."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MMS_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "display", "multimonitor_sync.py")

spec = importlib.util.spec_from_file_location("multimonitor_sync", _MMS_PATH)
if spec and spec.loader:
    multimonitor_sync = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = multimonitor_sync
    spec.loader.exec_module(multimonitor_sync)
else:
    raise ImportError(f"Could not load multimonitor_sync module from {_MMS_PATH}")


class TestMultiMonitorSync(unittest.TestCase):
    """Validates multi-head IVSHMEM buffer sizing, monitor parsing, cursor warp math, and launchers."""

    def test_shm_buffer_power_of_two_sizing(self) -> None:
        calc = multimonitor_sync.MultiMonitorSyncManager.compute_shm_size_mb

        # 1080p (1920x1080) -> 32 MB
        self.assertEqual(calc(1920, 1080), 32)

        # 1440p (2560x1440) -> 64 MB
        self.assertEqual(calc(2560, 1440), 64)

        # 4K (3840x2160) -> 128 MB
        self.assertEqual(calc(3840, 2160), 128)

        # Ultrawide (5120x1440) -> 128 MB
        self.assertEqual(calc(5120, 1440), 128)

        # Ultrawide (3440x1440) -> 64 MB
        self.assertEqual(calc(3440, 1440), 64)

        # 8K (7680x4320) -> 512 MB
        self.assertEqual(calc(7680, 4320), 512)

    def test_shm_buffer_size_invalid_inputs(self) -> None:
        calc = multimonitor_sync.MultiMonitorSyncManager.compute_shm_size_mb
        with self.assertRaises(ValueError):
            calc(0, 1080)
        with self.assertRaises(ValueError):
            calc(1920, -100)

    def test_hyprctl_monitor_parsing(self) -> None:
        raw_json = json.dumps([
            {
                "id": 0,
                "name": "DP-1",
                "width": 2560,
                "height": 1440,
                "refreshRate": 165.0,
                "x": 0,
                "y": 0,
                "scale": 1.0,
                "focused": True,
            },
            {
                "id": 1,
                "name": "DP-2",
                "width": 3840,
                "height": 2160,
                "refreshRate": 120.0,
                "x": 2560,
                "y": 0,
                "scale": 1.0,
                "focused": False,
            },
        ])
        parsed = multimonitor_sync.MultiMonitorSyncManager.parse_hyprctl_monitors(raw_json)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "DP-1")
        self.assertEqual(parsed[0]["shm_size_mb"], 64)
        self.assertEqual(parsed[1]["name"], "DP-2")
        self.assertEqual(parsed[1]["shm_size_mb"], 128)

    def test_synthetic_presets_and_detection(self) -> None:
        manager = multimonitor_sync.MultiMonitorSyncManager()

        for preset_name in multimonitor_sync.SYNTHETIC_PRESETS:
            monitors = manager.detect_displays(mock=True, synthetic_preset=preset_name)
            self.assertGreaterEqual(len(monitors), 2)
            self.assertTrue(all(m["shm_size_mb"] >= 32 for m in monitors))

    def test_libvirt_ivshmem_block_generation(self) -> None:
        manager = multimonitor_sync.MultiMonitorSyncManager()
        manager.detect_displays(mock=True, synthetic_preset="dual-1440p")
        xml = manager.generate_libvirt_ivshmem_block()

        self.assertIn('<shmem name="looking-glass-0">', xml)
        self.assertIn('<shmem name="looking-glass-1">', xml)
        self.assertIn('<size unit="M">64</size>', xml)
        self.assertIn('<model type="ivshmem-plain"/>', xml)

    def test_hyprland_multihead_rules(self) -> None:
        manager = multimonitor_sync.MultiMonitorSyncManager()
        manager.detect_displays(mock=True, synthetic_preset="dual-1440p")
        rules = manager.generate_hyprland_multihead_rules()

        self.assertIn("windowrulev2 = monitor DP-1, class:^(looking-glass-head-0)$", rules)
        self.assertIn("windowrulev2 = fullscreen, class:^(looking-glass-head-0)$", rules)
        self.assertIn("windowrulev2 = monitor DP-2, class:^(looking-glass-head-1)$", rules)
        self.assertIn("windowrulev2 = fullscreen, class:^(looking-glass-head-1)$", rules)

    def test_cursor_warp_transitions(self) -> None:
        manager = multimonitor_sync.MultiMonitorSyncManager()
        manager.detect_displays(mock=True, synthetic_preset="dual-1440p")
        # Dual 1440p: Head 0 (DP-1 at 0, 0, w=2560), Head 1 (DP-2 at 2560, 0, w=2560)

        # 1. Inside Head 0 -> No transition
        warp_inside = manager.calculate_cursor_warp(source_head=0, x=1000, y=500)
        self.assertFalse(warp_inside["transition"])
        self.assertEqual(warp_inside["target_head"], 0)
        self.assertEqual(warp_inside["target_coords"], [1000, 500])

        # 2. Cross right border of Head 0 (x=2600 >= 2560) -> Transition to Head 1
        warp_right = manager.calculate_cursor_warp(source_head=0, x=2600, y=500)
        self.assertTrue(warp_right["transition"])
        self.assertEqual(warp_right["direction"], "right")
        self.assertEqual(warp_right["target_head"], 1)
        self.assertEqual(warp_right["target_coords"], [40, 500])

        # 3. Cross left border of Head 1 (x=-50 < 0) -> Transition to Head 0
        warp_left = manager.calculate_cursor_warp(source_head=1, x=-50, y=700)
        self.assertTrue(warp_left["transition"])
        self.assertEqual(warp_left["direction"], "left")
        self.assertEqual(warp_left["target_head"], 0)
        self.assertEqual(warp_left["target_coords"], [2510, 700])

    def test_launch_script_generation(self) -> None:
        manager = multimonitor_sync.MultiMonitorSyncManager()
        manager.detect_displays(mock=True, synthetic_preset="dual-1440p")
        script = manager.generate_launch_scripts()

        self.assertIn("#!/usr/bin/env bash", script)
        self.assertIn("looking-glass-client \\", script)
        self.assertIn("-f /dev/kvmfr0", script)
        self.assertIn('wayland:output="DP-1"', script)
        self.assertIn("-f /dev/kvmfr1", script)
        self.assertIn('wayland:output="DP-2"', script)
        self.assertIn("wait", script)

    def test_verify_all(self) -> None:
        manager = multimonitor_sync.MultiMonitorSyncManager()
        res = manager.verify_all(mock=True)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["checks"]["display_detection"], "pass")
        self.assertEqual(res["checks"]["xml_generation"], "pass")
        self.assertEqual(res["checks"]["hyprland_rules"], "pass")
        self.assertEqual(res["checks"]["launch_script"], "pass")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiMonitorSync)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
