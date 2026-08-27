#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Halfvec HNSW Vector Search & Partitioning (T-725, T-726).
# AI-related: usr/lib/mios/ai/pgvector_hnsw.py, tests/test-pgvector-hnsw.py
"""Automated unit test suite for MiOS PgVector HNSW Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))

from pgvector_hnsw import MAX_KNN_SEARCH_MS, MIN_RECALL_ACCURACY_PCT, PgVectorHNSWManager


class TestPgVectorHNSW(unittest.TestCase):
    def setUp(self):
        self.mgr = PgVectorHNSWManager(dry_run=True)

    def test_schema_sql_specifies_halfvec_and_partitioning(self):
        """Test generated SQL uses halfvec(1536) and partitioned tables."""
        sql = self.mgr.generate_partition_schema_sql()
        self.assertIn("halfvec(1536)", sql)
        self.assertIn("PARTITION BY LIST", sql)
        self.assertIn("USING hnsw", sql)

    def test_sub_5ms_knn_search_latency_and_high_recall(self):
        """Test kNN search executes in <5ms with >98% recall accuracy."""
        res = self.mgr.execute_knn_query("test_vec_01", k=10)
        self.assertLess(res.search_latency_ms, MAX_KNN_SEARCH_MS)
        self.assertGreaterEqual(res.recall_accuracy_pct, MIN_RECALL_ACCURACY_PCT)
        self.assertGreaterEqual(res.memory_reduction_pct, 70.0)


if __name__ == "__main__":
    unittest.main()
