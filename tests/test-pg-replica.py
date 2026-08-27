#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-406 (WS-DURA PostgreSQL streaming replica provisioning and failover).
# AI-related: usr/libexec/mios/db/mios-pg-replica.py, usr/lib/systemd/system/mios-pg-replica.service
"""Automated tests for PostgreSQL replica provisioning, replication lag monitoring, fencing, and promotion."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_REPLICA_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-pg-replica.py")

spec = importlib.util.spec_from_file_location("pg_replica", _REPLICA_PATH)
if spec and spec.loader:
    pg_replica = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pg_replica
    spec.loader.exec_module(pg_replica)
else:
    raise ImportError(f"Could not load pg_replica module from {_REPLICA_PATH}")

class TestPgReplica(unittest.TestCase):
    """Validates replication provisioning, WAL lag calculation, fencing enforcement, and promotion."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-pg-replica-test-")
        self.data_dir = os.path.join(self.tmpdir, "data")
        self.fence_dir = os.path.join(self.tmpdir, "fencing")
        self.manager = pg_replica.PgReplicaManager(
            primary_host="10.0.0.1",
            primary_port=5432,
            replica_host="10.0.0.2",
            replica_port=5432,
            slot_name="test_slot",
            data_dir=self.data_dir,
            fence_dir=self.fence_dir,
            max_lag_ms=50.0,
            mock=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_provision_replica(self):
        res = self.manager.provision_replica()
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["primary_conninfo_written"])
        standby_signal = os.path.join(self.data_dir, "standby.signal")
        auto_conf = os.path.join(self.data_dir, "postgresql.auto.conf")
        self.assertTrue(os.path.isfile(standby_signal))
        self.assertTrue(os.path.isfile(auto_conf))
        with open(auto_conf, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("10.0.0.1", content)
            self.assertIn("test_slot", content)

    def test_replication_status_and_lag(self):
        status = self.manager.get_replication_status()
        self.assertEqual(status["status"], "active")
        self.assertTrue(status["is_healthy"])
        self.assertLessEqual(status["lag_ms"], 50.0)
        self.assertEqual(status["sync_state"], "streaming")

    def test_health_check_within_threshold(self):
        health = self.manager.health_check()
        self.assertTrue(health["healthy"])
        self.assertIn("healthy", health["reason"])

    def test_fencing_primary(self):
        self.assertFalse(self.manager.is_primary_fenced())
        fence_record = self.manager.fence_primary(reason="planned_failover")
        self.assertEqual(fence_record["status"], "fenced")
        self.assertTrue(self.manager.is_primary_fenced())

        # Unfence
        ok = self.manager.unfence_primary()
        self.assertTrue(ok)
        self.assertFalse(self.manager.is_primary_fenced())

    def test_promotion_blocked_when_unfenced(self):
        """Invariant check: Promotion MUST fail if primary is not fenced (split-brain prevention)."""
        self.manager.unfence_primary()
        self.assertFalse(self.manager.is_primary_fenced())

        with self.assertRaises(RuntimeError) as ctx:
            self.manager.promote_replica(force_unfenced=False)
        self.assertIn("Old primary is NOT fenced", str(ctx.exception))

    def test_promotion_succeeds_when_fenced(self):
        self.manager.provision_replica()
        self.manager.fence_primary()
        self.assertTrue(self.manager.is_primary_fenced())

        res = self.manager.promote_replica(force_unfenced=False)
        self.assertEqual(res["status"], "promoted")
        self.assertTrue(res["primary_fenced"])

    def test_promotion_force_unfenced_override(self):
        self.manager.provision_replica()
        self.manager.unfence_primary()
        res = self.manager.promote_replica(force_unfenced=True)
        self.assertEqual(res["status"], "promoted")

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPgReplica)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
