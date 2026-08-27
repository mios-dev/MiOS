#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-623 through T-632.
# Tests boundary conditions across Fan Control, WebRTC Streamer, Secret Enclave, VRAM Swapper, and GPU Priority Scheduler.
# AI-doc: usr/share/doc/mios/manual/testing.md
"""Empirical adversarial stress test suite for tasks T-623 through T-632."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ui"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from fand import MultiZonePIDFanController
from webrtc_stream import LATENCY_TARGET_MS, PipeWireDMABUFStreamer, ScreenCastPortalBridge, StreamConfig
from secret_mem import SecretBuffer, SecretEnclave
from vram_swap import MAX_SWAP_LATENCY_MS, VRAMSwapManager
from gpu_sched import HIGH_PRIO_LATENCY_TARGET_MS, GPUComputeStreamScheduler, StreamPriority

class TestEmpiricalStressT623T632(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t623-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. Multi-zone Fan Controller Stress Tests ---
    def test_fan_rapid_thermal_swing_stress(self):
        """Stress: Rapid oscillating temperature swings must remain rate-limited without violent spikes."""
        controller = MultiZonePIDFanController(
            sysfs_root=self.tmp_dir,
            dry_run=True,
            hysteresis_deg=5.0,
            max_pwm_ramp_per_sec=20.0,
        )

        temperatures = [40.0, 80.0, 45.0, 88.0, 50.0, 92.0, 35.0]
        last_pwm = controller.zones["cpu"].min_pwm

        for temp in temperatures:
            pwm = controller.compute_pid_pwm("cpu", current_temp=temp, dt=1.0)
            if temp < 85.0:  # Below critical temp
                # Delta must not exceed rate limit
                self.assertLessEqual(abs(pwm - last_pwm), 21.0)
            else:
                # Critical temp immediately forces 100% PWM
                self.assertEqual(pwm, 255)
            last_pwm = pwm

    # --- 2. PipeWire WebRTC Streamer Stress Tests ---
    def test_webrtc_session_thrashing_stress(self):
        """Stress: Rapid consecutive session authorization and revocation cycles."""
        portal = ScreenCastPortalBridge(dry_run=True)
        streamer = PipeWireDMABUFStreamer(portal_bridge=portal, dry_run=True)

        for _ in range(50):
            ok, handle = streamer.start_stream()
            self.assertTrue(ok)
            self.assertTrue(streamer.is_streaming())
            metric = streamer.process_frame(dmabuf_fd=42)
            self.assertIsNotNone(metric)
            self.assertLess(metric.total_latency_ms, LATENCY_TARGET_MS)
            streamer.stop_stream()
            self.assertFalse(streamer.is_streaming())

    # --- 3. Secure Secret Enclave Stress Tests ---
    def test_secret_enclave_concurrency_and_double_wipe(self):
        """Stress: Verify secret buffer zeroization idempotency and isolation under churn."""
        buffers = []
        for i in range(30):
            token = f"secret_key_stream_item_{i:04d}_{'x'*32}"
            buf = SecretEnclave.hold(token)
            self.assertEqual(buf.get_bytes().decode("utf-8"), token)
            buffers.append(buf)

        # Wipe all buffers and assert strict zeroization
        for buf in buffers:
            buf.wipe()
            # Double wipe must be idempotent
            buf.wipe()
            self.assertTrue(buf.is_wiped)
            with self.assertRaises(ValueError):
                buf.get_bytes()

    # --- 4. Dynamic VRAM Swapper Stress Tests ---
    def test_vram_swapper_high_concurrency_kv_eviction(self):
        """Stress: 10 concurrent conversation sessions under extreme VRAM pressure."""
        mgr = VRAMSwapManager(
            total_vram_mb=4096.0,  # Tight 4GB budget
            total_host_ram_mb=32768.0,
            pcie_bandwidth_gbps=32.0,
            vram_watermark_ratio=0.75,
            dry_run=True,
        )
        mgr.register_model("mios-chat", total_layers=16, layer_size_mb=128.0)  # 2048 MB model
        mgr.activate_model("mios-chat")

        # Spawn 10 sessions each with 500MB KV cache
        for i in range(10):
            sess_id = f"stress_session_{i}"
            mgr.allocate_or_update_kv_slot(sess_id, "mios-chat", token_count=1000 * (i + 1), size_mb=500.0)
            if i < 9:
                mgr.unpin_kv_slot(sess_id)

        status = mgr.get_status()
        # VRAM should not exceed budget and multiple slots must have paged to host RAM
        self.assertLessEqual(status["used_vram_mb"], 4096.0)
        self.assertGreater(status["kv_in_host"], 3)

        # Recall an evicted session and verify token count is 100% preserved
        ok, lat = mgr.page_in_kv_slot("stress_session_0")
        self.assertTrue(ok)
        self.assertEqual(mgr.kv_slots["stress_session_0"].token_count, 1000)
        self.assertLess(lat, MAX_SWAP_LATENCY_MS)

    # --- 5. GPU Compute Stream Scheduler Stress Tests ---
    def test_gpu_scheduler_bursty_preemption_churn(self):
        """Stress: Heavy background batch processing interrupted by 10 rapid bursty voice requests."""
        sched = GPUComputeStreamScheduler(dry_run=True)
        bg1 = sched.submit_job("qlora_heavy_1", StreamPriority.LOW, total_steps=500)
        bg2 = sched.submit_job("qlora_heavy_2", StreamPriority.LOW, total_steps=500)

        for i in range(10):
            sched.step_background_job(bg1.job_id, step_count=20)
            sched.step_background_job(bg2.job_id, step_count=20)

            # High priority voice burst
            job, ttft = sched.execute_high_prio_turn(f"voice_burst_{i}", steps=5)
            self.assertTrue(job.is_completed)
            self.assertLess(ttft, HIGH_PRIO_LATENCY_TARGET_MS)

        # Complete background jobs
        sched.step_background_job(bg1.job_id, step_count=300)
        sched.step_background_job(bg2.job_id, step_count=300)

        self.assertTrue(bg1.is_completed)
        self.assertTrue(bg2.is_completed)
        status = sched.get_status()
        self.assertEqual(status["preemption_event_count"], 10)
        self.assertTrue(status["sub_50ms_target_met"])

if __name__ == "__main__":
    unittest.main()
