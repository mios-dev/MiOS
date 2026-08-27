#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-663 through T-672.
# Tests boundary conditions across GPU Heatmap, Systemd Harden, OOMD PSI, Elastic Training, and Multi-modal WS.
# AI-doc: usr/share/doc/mios/manual/testing.md
"""Empirical adversarial stress test suite for tasks T-663 through T-672."""

import asyncio
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "kernel"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))

from gpu_heatd import GPUInterconnectProfiler
from systemd_harden import SystemdHardeningManager
from oomd_psi import OOMDPressureManager
from train_elastic import ElasticTrainingManager
from multimodal_ws import MAX_VOICE_LATENCY_MS, MultiModalStreamingPipeline

class TestEmpiricalStressT663T672(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t663-")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. GPU Interconnect Topology Stress Tests ---
    def test_gpu_heat_massive_8way_matrix(self):
        """Stress: 8-way GPU interconnect sampling computes complete 64-element matrix with 0 errors."""
        profiler = GPUInterconnectProfiler(dry_run=True)
        mat = profiler.sample_interconnect_matrix(gpu_count=8, mock_bandwidth_gbps=900.0)
        self.assertEqual(len(mat.bandwidth_gbps_matrix), 8)
        self.assertEqual(len(mat.bandwidth_gbps_matrix[0]), 8)
        rendered = profiler.render_ascii_heatmap(mat)
        self.assertIn("GPU7", rendered)

    # --- 2. Systemd Hardening Exposure Audit Stress Tests ---
    def test_systemd_harden_all_quadlet_services(self):
        """Stress: Hardening 20 systemd services produces exposure scores < 3.0 on all units."""
        mgr = SystemdHardeningManager(dry_run=True)
        for i in range(20):
            audit = mgr.audit_unit_exposure(f"mios-quadlet-{i}.service", has_hardening_dropin=True)
            self.assertTrue(audit.is_safe)
            self.assertLess(audit.exposure_score, 3.0)

    # --- 3. OOMD PSI Pressure Spike Stress Tests ---
    def test_oomd_psi_extreme_100pct_memory_thrash(self):
        """Stress: Extreme 100% PSI stall pressure kills background victim while preserving database."""
        mgr = OOMDPressureManager(psi_kill_threshold_pct=50.0, dry_run=True)
        act = mgr.evaluate_pressure_stall(
            "system.slice", 100.0, ["mios-pgvector.service", "gnome-shell.service", "rogue-allocator.service"]
        )
        self.assertEqual(act.action_taken, "kill")
        self.assertEqual(act.victim_unit, "rogue-allocator.service")

    # --- 4. Elastic Training Rapid Preemption Stress Tests ---
    def test_elastic_training_frequent_preemption_cycles(self):
        """Stress: 5 consecutive preemption and resumption cycles preserve training step continuity."""
        mgr = ElasticTrainingManager(checkpoint_dir=self.tmp_dir, dry_run=True)
        for step in [100, 200, 300, 400, 500]:
            mgr.handle_preemption_signal(current_step=step, loss=1.0 / (step // 100))
            resumed = mgr.resume_from_latest_checkpoint()
            self.assertIsNotNone(resumed)
            self.assertEqual(resumed.step, step)

    # --- 5. Multi-modal WebSocket High-Concurrency Stress Tests ---
    def test_multimodal_ws_concurrent_streams(self):
        """Stress: 10 concurrent multi-modal streaming turns all maintain <100ms conversational latency."""
        async def _run():
            pipe = MultiModalStreamingPipeline(dry_run=True)
            tasks = [
                pipe.process_multimodal_turn(f"stream_{i}", audio_frames=5, video_frames=2)
                for i in range(10)
            ]
            turns = await asyncio.gather(*tasks)
            for t in turns:
                self.assertLess(t.voice_latency_ms, MAX_VOICE_LATENCY_MS)

        asyncio.run(_run())

if __name__ == "__main__":
    unittest.main()
