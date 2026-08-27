#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-633 through T-642.
# Tests boundary conditions across Energy Capping, Prompt Cache, PagedAttention, S.M.A.R.T. Evacuation, and Crash Triage.
# AI-doc: usr/share/doc/mios/manual/testing.md
"""Empirical adversarial stress test suite for tasks T-633 through T-642."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "kernel"))

from energyd import EnergyCapManager
from prompt_cache import RadixPromptCacheManager, TTFT_TARGET_MS, MATCH_LATENCY_MAX_MS
from paged_attn import PagedAttentionBlockManager
from disk_health import SmartHealthMonitor
from crash_triage import KernelCrashTriageEngine

class TestEmpiricalStressT633T642(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t633-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. Energy Capping Stress Tests ---
    def test_energy_rapid_power_spike_modulation(self):
        """Stress: Sustained power spikes must continuously damp GPU wattage without crashing."""
        mgr = EnergyCapManager(chassis_cap_watts=450.0, dry_run=True)
        for i in range(25):
            spike_cpu = 180.0 + (i % 5) * 40.0
            spike_gpu = 350.0 + (i % 4) * 30.0
            m = mgr.evaluate_and_enforce_cap(mock_cpu_w=spike_cpu, mock_gpu_w=spike_gpu)
            self.assertTrue(m.is_throttled)
            self.assertLessEqual(m.applied_gpu_cap_watts, 450.0)
            self.assertGreaterEqual(m.applied_gpu_cap_watts, 150.0)

    def test_energy_thermal_power_compound_stress(self):
        """Stress: Simultaneous severe thermal runaway and electrical overload."""
        mgr = EnergyCapManager(chassis_cap_watts=400.0, thermal_limit_c=80.0, dry_run=True)
        m = mgr.evaluate_and_enforce_cap(
            mock_cpu_w=300.0, mock_gpu_w=400.0, mock_cpu_temp=92.0, mock_gpu_temp=95.0
        )
        self.assertTrue(m.is_throttled)
        self.assertIn("power_cap_exceeded", m.throttle_reason)
        self.assertIn("thermal_throttle", m.throttle_reason)
        self.assertEqual(m.applied_gpu_cap_watts, 150.0)

    # --- 2. Radix Prompt Cache Stress Tests ---
    def test_prompt_cache_hash_collision_resilience(self):
        """Stress: Similar token prefixes must generate distinct hashes and maintain sub-10ms match latency."""
        cache = RadixPromptCacheManager(dry_run=True)
        tokens_a = list(range(10, 50))
        tokens_b = list(range(10, 49)) + [999]  # 1 token diff

        h_a = cache.insert_prefix(tokens_a)
        h_b = cache.insert_prefix(tokens_b)
        self.assertNotEqual(h_a, h_b)

        hit_a, _, ttft_a = cache.match_prefix(tokens_a, min_prefix_len=16)
        hit_b, _, ttft_b = cache.match_prefix(tokens_b, min_prefix_len=16)
        self.assertTrue(hit_a)
        self.assertTrue(hit_b)
        self.assertLess(ttft_a, MATCH_LATENCY_MAX_MS)
        self.assertLess(ttft_b, MATCH_LATENCY_MAX_MS)

    def test_prompt_cache_massive_branching(self):
        """Stress: 100 deep branches off common system prompt must all resolve with 0 token loss."""
        cache = RadixPromptCacheManager(max_cache_mb=100.0, dry_run=True)
        common_sys = list(range(1, 40))
        cache.insert_prefix(common_sys)

        for b in range(100):
            branch_tokens = common_sys + [b * 10, b * 10 + 1, b * 10 + 2]
            cache.insert_prefix(branch_tokens)

        # Verify all branches hit correctly
        for b in range(100):
            query = common_sys + [b * 10, b * 10 + 1, b * 10 + 2, 9999]
            hit, node, latency = cache.match_prefix(query, min_prefix_len=16)
            self.assertTrue(hit)
            self.assertEqual(node.tokens, common_sys + [b * 10, b * 10 + 1, b * 10 + 2])
            self.assertLess(latency, MATCH_LATENCY_MAX_MS)

    # --- 3. PagedAttention Stress Tests ---
    def test_paged_attention_vram_saturation_recovery(self):
        """Stress: Allocating beyond capacity without eviction must return False gracefully and recover on free."""
        mgr = PagedAttentionBlockManager(total_blocks=10, block_size=32, dry_run=True)
        ok1 = mgr.allocate_tokens("sess_large", 320)  # Consumes all 10 blocks
        self.assertTrue(ok1)

        ok2 = mgr.allocate_tokens("sess_overflow", 32, allow_eviction=False)
        self.assertFalse(ok2)
        self.assertIn("sess_large", mgr.sessions)

        mgr.free_session("sess_large")
        ok3 = mgr.allocate_tokens("sess_overflow", 32)
        self.assertTrue(ok3)

    def test_paged_attention_50_cow_branches(self):
        """Stress: Forking 50 speculative branches off a shared parent and mutating independently."""
        mgr = PagedAttentionBlockManager(total_blocks=500, block_size=32, dry_run=True)
        mgr.allocate_tokens("root_sess", 128)  # 4 blocks

        for i in range(50):
            child_id = f"spec_branch_{i}"
            mgr.branch_session("root_sess", child_id)
            mgr.append_tokens_cow(child_id, (i + 1) * 5)

        self.assertEqual(len(mgr.sessions), 51)
        self.assertGreater(mgr.cow_splits, 0)
        # Free all children
        for i in range(50):
            mgr.free_session(f"spec_branch_{i}")
        self.assertEqual(len(mgr.sessions), 1)

    # --- 4. S.M.A.R.T. Drive Health Stress Tests ---
    def test_smart_multiple_drive_failure_isolation(self):
        """Stress: Multiple simultaneous degraded drives must all trigger unique Ceph OSD drains."""
        monitor = SmartHealthMonitor(dry_run=True)
        drives = ["/dev/nvme0n1", "/dev/nvme1n1", "/dev/sda", "/dev/sdb"]
        for d in drives:
            h = monitor.evaluate_drive_health(d, {"percentage_used": 99.0, "available_spare": 2.0})
            self.assertTrue(h.is_degraded)
            self.assertEqual(h.risk_level, "CRITICAL")
        self.assertEqual(len(monitor.evacuated_osds), 4)

    def test_smart_malformed_json_fallback(self):
        """Stress: Corrupted or incomplete JSON input must not crash health evaluator."""
        monitor = SmartHealthMonitor(dry_run=True)
        h = monitor.evaluate_drive_health("/dev/nvme99n1", {"garbage_field": True})
        self.assertFalse(h.is_degraded)
        self.assertEqual(h.action_taken, "none")

    # --- 5. Kernel Crash Triage Stress Tests ---
    def test_crash_triage_empty_vmcore_safety(self):
        """Stress: Non-existent or empty vmcore must produce sanitized fallback crash ticket."""
        engine = KernelCrashTriageEngine(dry_run=True)
        rep = engine.triage_vmcore("/nonexistent/vmcore.zst")
        self.assertIsNotNone(rep.ticket_id)
        self.assertIn("bcachefs", rep.faulting_module)

    def test_crash_triage_deep_callstack_and_unicode_handling(self):
        """Stress: Deep recursive stack trace (100 frames) with unicode panic message."""
        engine = KernelCrashTriageEngine(dry_run=True)
        deep_oops = "BUG: kernel NULL pointer dereference in \u00fcber_module\n"
        deep_oops += "RIP: 0010:_ZN11uber_module4core4calcE+0x10/0x20\n"
        deep_oops += "Call Trace:\n"
        for i in range(100):
            deep_oops += f" frame_{i}+0x{i:x}/0x100\n"

        rep = engine.parse_dmesg_oops(deep_oops)
        self.assertIsNotNone(rep.ticket_id)
        self.assertGreaterEqual(len(rep.callstack), 50)
        ticket = engine.generate_postgres_ticket(rep)
        self.assertEqual(ticket["status"], "OPEN")

if __name__ == "__main__":
    unittest.main()
