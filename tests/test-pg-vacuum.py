#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS PostgreSQL autovacuum tuner and pg_cron HNSW reindexer.
# AI-doc: usr/share/doc/mios/manual/database.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "db"))
from pg_vacuum_tuner import PGVacuumTuner

class TestPGVacuumTuner(unittest.TestCase):
    def setUp(self):
        self.tuner = PGVacuumTuner(dry_run=True)

    def test_render_pg_conf(self):
        conf = self.tuner.render_pg_conf()
        self.assertIn("autovacuum = on", conf)
        self.assertIn("autovacuum_vacuum_scale_factor = 0.05", conf)
        self.assertIn("wal_compression = 'zstd'", conf)
        self.assertIn("max_parallel_maintenance_workers = 4", conf)

    def test_render_pg_cron_reindex_sql(self):
        sql = self.tuner.render_pg_cron_reindex_sql()
        self.assertIn("REINDEX TABLE CONCURRENTLY", sql)
        self.assertIn("system_logs_rag", sql)
        self.assertIn("agent_memories", sql)
        self.assertIn("0 3 * * *", sql)

if __name__ == "__main__":
    unittest.main()
