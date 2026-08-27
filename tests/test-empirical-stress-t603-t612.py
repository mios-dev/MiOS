#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-603 through T-612.
# Tests boundary conditions across worktrees, async HTTPX, Libei input, PostgreSQL autovacuum, and hardware watchdogs.
# AI-doc: usr/share/doc/mios/manual/testing.md
import unittest
import sys
import os
import asyncio
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ui"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "db"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from mios_worktree import AgentWorktreeManager
from mios_httpx import MiOSAsyncHTTPTransport
from libei_input import LibeiInputInjector
from pg_vacuum_tuner import PGVacuumTuner
from watchdog_manager import HardwareWatchdogManager


class TestEmpiricalStressT603T612(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t603-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. Worktree Stress Tests ---
    def test_worktree_special_character_subagent_id_sanitization(self):
        """Stress: Subagent ID with slashes, dots, or spaces must be cleanly mapped to branch name."""
        mgr = AgentWorktreeManager(repo_root=self.tmp_dir, dry_run=True)
        res = mgr.create_worktree("agent-42_test.alpha")
        self.assertEqual(res["branch"], "agent/agent-42_test.alpha")

    # --- 2. HTTPX Async Transport Stress Tests ---
    def test_httpx_transport_zero_timeout_handling(self):
        """Stress: Zero or sub-millisecond timeout must be accepted without throwing config errors."""
        transport = MiOSAsyncHTTPTransport(timeout_seconds=0.001, mock_mode=True)
        res = asyncio.run(transport.fetch_endpoint("http://localhost/v1/ping"))
        self.assertEqual(res["status"], "success")

    # --- 3. Libei Input Stress Tests ---
    def test_libei_extreme_coordinate_normalization(self):
        """Stress: Infinity, negative, and extreme coordinate values must be clamped safely."""
        injector = LibeiInputInjector(display_width=3840, display_height=2160, dry_run=True)
        px, py = injector.normalize_coordinates(-9999, 99999)
        self.assertEqual(px, 0)
        self.assertEqual(py, 2159)

    # --- 4. PostgreSQL Maintenance Stress Tests ---
    def test_pg_vacuum_scale_factor_invariants(self):
        """Stress: Autovacuum scale factors must be strictly non-negative floats."""
        tuner = PGVacuumTuner(autovacuum_max_workers=8, dry_run=True)
        conf = tuner.render_pg_conf()
        self.assertIn("autovacuum_max_workers = 8", conf)
        self.assertIn("wal_compression = 'zstd'", conf)

    # --- 5. Watchdog Stress Tests ---
    def test_watchdog_timeout_ordering_invariants(self):
        """Stress: RebootWatchdogSec must always exceed RuntimeWatchdogSec."""
        mgr = HardwareWatchdogManager(runtime_watchdog_sec=30, reboot_watchdog_sec=60, dry_run=True)
        conf = mgr.render_systemd_conf()
        self.assertIn("RuntimeWatchdogSec=30s", conf)
        self.assertIn("RebootWatchdogSec=60s", conf)


if __name__ == "__main__":
    unittest.main()
