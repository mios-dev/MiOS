#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-401 (WS-DURA pgvector VACUUM and concurrent HNSW reindexing).
# AI-related: usr/libexec/mios/db/mios-pgvector-optimize.py, usr/lib/systemd/system/mios-pgvector-optimize.service
"""Automated tests for pgvector optimization engine and concurrent reindexing."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_OPTIMIZE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-pgvector-optimize.py")

spec = importlib.util.spec_from_file_location("pgvector_optimize", _OPTIMIZE_PATH)
if spec and spec.loader:
    pgvector_optimize = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pgvector_optimize
    spec.loader.exec_module(pgvector_optimize)
else:
    raise ImportError(f"Could not load pgvector_optimize module from {_OPTIMIZE_PATH}")

class TestPgVectorOptimize(unittest.TestCase):
    """Validates dead tuple statistics retrieval, concurrent index reindexing, and full optimization cycle."""

    def setUp(self):
        self.optimizer = pgvector_optimize.PgVectorOptimizer(
            db="mios",
            host="127.0.0.1",
            port=5432,
            user="postgres",
            parallel=4,
            dry_run=False,
            mock=True,
        )

    def test_dead_tuple_discovery(self):
        stats = self.optimizer.get_dead_tuples()
        self.assertIsInstance(stats, list)
        self.assertGreater(len(stats), 0)
        table_names = [s["table_name"] for s in stats]
        self.assertIn("knowledge", table_names)
        self.assertIn("agent_memory", table_names)
        for entry in stats:
            self.assertIn("live_tuples", entry)
            self.assertIn("dead_tuples", entry)
            self.assertIn("dead_tuple_pct", entry)

    def test_vector_index_discovery(self):
        indexes = self.optimizer.get_vector_indexes()
        self.assertIsInstance(indexes, list)
        self.assertGreater(len(indexes), 0)
        index_names = [i["index_name"] for i in indexes]
        self.assertIn("knowledge_emb_hnsw", index_names)
        self.assertIn("agent_memory_emb_hnsw", index_names)
        for idx in indexes:
            self.assertEqual(idx["index_type"], "hnsw")
            self.assertGreater(idx["index_bytes"], 0)

    def test_vacuum_analyze_tables(self):
        results = self.optimizer.vacuum_analyze_tables(["knowledge", "agent_memory"])
        self.assertEqual(len(results), 2)
        for res in results:
            self.assertEqual(res["status"], "success")
            self.assertIn("VACUUM (ANALYZE, PARALLEL 4)", res["command"])
            self.assertIsNone(res["error"])

    def test_concurrent_reindex_invariant(self):
        """Invariant check: Reindex operations MUST be CONCURRENT to avoid blocking read queries."""
        results = self.optimizer.reindex_vector_indexes_concurrently()
        self.assertGreater(len(results), 0)
        for res in results:
            self.assertEqual(res["status"], "success")
            # Enforce REINDEX INDEX CONCURRENTLY
            self.assertTrue(
                res["command"].startswith("REINDEX INDEX CONCURRENTLY "),
                f"Command '{res['command']}' violates non-blocking concurrency invariant!",
            )

    def test_full_optimization_report(self):
        report = self.optimizer.optimize()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["database"], "mios")
        self.assertGreater(report["tables_vacuumed"], 0)
        self.assertGreater(report["indexes_reindexed"], 0)
        self.assertIn("dead_tuple_stats", report)
        self.assertIn("total_elapsed_ms", report)

    def test_dry_run_mode(self):
        dry_optimizer = pgvector_optimize.PgVectorOptimizer(
            db="mios",
            host="127.0.0.1",
            port=5432,
            user="postgres",
            parallel=2,
            dry_run=True,
            mock=True,
        )
        report = dry_optimizer.optimize()
        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["dry_run"])
        for v in report["vacuum_details"]:
            self.assertEqual(v["status"], "dry_run")
        for r in report["reindex_details"]:
            self.assertEqual(r["status"], "dry_run")

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPgVectorOptimize)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
