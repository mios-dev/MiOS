#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Parquet log archiver and semantic pgvector diagnostic indexer.
# AI-doc: usr/share/doc/mios/manual/telemetry.md
import unittest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "telemetry"))
from log_archiver import LogArchiverManager

class TestLogArchiverManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-test-log-arch-")
        self.archiver = LogArchiverManager(archive_dir=self.tmp_dir, dry_run=False)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_parse_journal_records_and_error_clusters(self):
        raw_lines = [
            json.dumps({"MESSAGE": "System boot completed in 2.1s", "PRIORITY": "6", "_SYSTEMD_UNIT": "systemd"}),
            json.dumps({"MESSAGE": "FATAL: Out of memory in vLLM GPU worker", "PRIORITY": "2", "_SYSTEMD_UNIT": "mios-llm-heavy.service"}),
            json.dumps({"MESSAGE": "Bcachefs scrub reported 0 corrupted blocks", "PRIORITY": "6", "_SYSTEMD_UNIT": "kernel"}),
            json.dumps({"MESSAGE": "Failed to authenticate SSH user from 192.168.1.150", "PRIORITY": "3", "SYSLOG_IDENTIFIER": "sshd"}),
        ]
        records, clusters = self.archiver.parse_journal_records(raw_lines)

        self.assertEqual(len(records), 4)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0]["unit"], "mios-llm-heavy.service")
        self.assertIn("Out of memory", clusters[0]["error_text"])

    def test_write_columnar_parquet_compression(self):
        # Generate 500 synthetic log records
        records = [
            {
                "timestamp_us": 1787830000000000 + i,
                "priority": 6,
                "unit": "mios-agent-pipe.service",
                "message": f"Turn {i}: Router processed request in 18ms with 0 errors and valid traceparent header",
                "pid": "8412",
                "hostname": "mios-node-01",
            }
            for i in range(500)
        ]
        out_file = os.path.join(self.tmp_dir, "test_log.parquet")
        res = self.archiver.write_columnar_parquet(records, out_file)

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["records_count"], 500)
        self.assertLess(res["parquet_bytes"], res["raw_bytes"])
        self.assertTrue(os.path.exists(out_file))

    def test_index_error_clusters_metadata(self):
        clusters = [
            {"timestamp_us": 100, "unit": "test.service", "priority": 3, "error_text": "Kernel fault"}
        ]
        res = self.archiver.index_error_clusters(clusters)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["clusters_indexed"], 1)
        self.assertEqual(res["embedding_model"], "nomic-embed-text")

if __name__ == "__main__":
    unittest.main()
