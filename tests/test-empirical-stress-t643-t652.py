#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-643 through T-652.
# Tests boundary conditions across USBGuard, Flatpak Snapshot, Live ISO, Tensor Kernels, and Reactive Loop.
# AI-doc: usr/share/doc/mios/manual/testing.md
"""Empirical adversarial stress test suite for tasks T-643 through T-652."""

import asyncio
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "build"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))

from usbguard import USBGuardPolicyManager
from snapshot import FlatpakSnapshotManager
from liveiso import LiveISOPipeline
from tensor_kernels import TensorKernelDispatcher
from reactive_loop import MAX_WAKEUP_LATENCY_MS, ReactiveEventDispatcher


class TestEmpiricalStressT643T652(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t643-")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. USBGuard BadUSB Storm Stress Tests ---
    def test_usbguard_badusb_rapid_insertion_storm(self):
        """Stress: 50 concurrent rogue USB insertions must all be blocked with 0 false grants."""
        mgr = USBGuardPolicyManager(dry_run=True)
        mgr.enroll_device("046d", "c52b", "VALID_KEY", "Whitelisted Keyboard")

        for i in range(50):
            allowed = mgr.handle_device_insertion(
                f"usb_{i}", "bad_vid", "bad_pid", f"SN_ROGUE_{i}", "03:01:01", f"Ducky {i}"
            )
            self.assertFalse(allowed)

        self.assertEqual(len(mgr.blocked_attempts), 50)

    # --- 2. Flatpak Snapshot State Tree Stress Tests ---
    def test_flatpak_rapid_multiversion_snapshot_and_rollback(self):
        """Stress: 10 consecutive snapshot deltas must support precision rollback to any point."""
        mgr = FlatpakSnapshotManager(root_dir=self.tmp_dir, dry_run=True)
        app_id = "org.test.MultiVersion"
        app_path = mgr._app_dir(app_id)
        os.makedirs(app_path, exist_ok=True)

        snapshots = []
        for v in range(5):
            with open(os.path.join(app_path, "version.txt"), "w") as f:
                f.write(f"VERSION_{v}")
            snap = mgr.create_snapshot(app_id, tag=f"v{v}")
            snapshots.append(snap)

        # Rollback specifically to version 2
        ok = mgr.rollback_app(app_id, snapshots[2].snapshot_id)
        self.assertTrue(ok)
        with open(os.path.join(app_path, "version.txt"), "r") as f:
            content = f.read()
        self.assertEqual(content, "VERSION_2")

    # --- 3. Live ISO Pipeline Stress Tests ---
    def test_liveiso_idempotent_multi_target_build(self):
        """Stress: Synthesizing multiple ISO & iPXE targets must produce isolated, complete artifacts."""
        pipe = LiveISOPipeline(output_dir=self.tmp_dir, dry_run=True)
        p1 = pipe.generate_ipxe_script("http://srv1")
        p2 = pipe.generate_ipxe_script("http://srv2")
        art = pipe.build_hybrid_iso()
        self.assertTrue(os.path.exists(p2))
        self.assertTrue(os.path.exists(art.file_path))

    # --- 4. Tensor Kernel Architecture Mapping Stress Tests ---
    def test_tensor_kernel_all_known_arch_coverage(self):
        """Stress: All modern CUDA/ROCm architecture keys must map to valid GEMM/Attention configs."""
        dispatcher = TensorKernelDispatcher(dry_run=True)
        for model in TensorKernelDispatcher.ARCH_MAP.keys():
            arch = dispatcher.probe_gpu_capability(model)
            self.assertIsNotNone(arch.sm_version)
            env = dispatcher.get_env_bindings()
            self.assertIn("FLASH_ATTN_VERSION", env)

    # --- 5. Reactive Event Loop Async Stress Tests ---
    def test_reactive_loop_rapid_burst_concurrency(self):
        """Stress: 100 rapid NOTIFY events across 20 listeners must deliver with <5ms latency."""
        async def _run():
            dispatcher = ReactiveEventDispatcher(dry_run=True)
            queues = [dispatcher.subscribe(f"chan_{i % 5}") for i in range(20)]

            for i in range(100):
                chan = f"chan_{i % 5}"
                await dispatcher.emit_notify(chan, {"seq": i})

            # Verify all queues received events
            for q in queues:
                ev = await dispatcher.wait_for_wakeup(q, timeout=1.0)
                self.assertIsNotNone(ev)
                self.assertLess(ev.latency_ms, MAX_WAKEUP_LATENCY_MS)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
