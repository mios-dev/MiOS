#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Jensen-Shannon divergence anomaly alarm and PostgreSQL threat_events vector sink (T-512).
# AI-doc: usr/share/doc/mios/manual/ch06-security.md
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_ANOMALY_BIN = os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe", "mios_net_anomaly.py")
_SCHEMA_SQL = os.path.join(_ROOT, "usr", "share", "mios", "postgres", "schema-init.sql")


class TestNetAnomaly(unittest.TestCase):
    """Validates JSD network anomaly detector and threat_events vector schema."""

    def test_files_exist_and_executable(self):
        self.assertTrue(os.path.isfile(_ANOMALY_BIN), f"Missing {_ANOMALY_BIN}")
        self.assertTrue(os.access(_ANOMALY_BIN, os.X_OK), f"Not executable: {_ANOMALY_BIN}")
        self.assertTrue(os.path.isfile(_SCHEMA_SQL), f"Missing {_SCHEMA_SQL}")

    def test_threat_events_schema_ddl(self):
        with open(_SCHEMA_SQL, "r", encoding="utf-8") as f:
            sql = f.read()

        self.assertIn("CREATE TABLE IF NOT EXISTS threat_events", sql)
        self.assertIn("divergence    double precision NOT NULL", sql)
        self.assertIn("emb           vector(768)", sql)
        self.assertIn("CREATE INDEX IF NOT EXISTS threat_events_emb_hnsw", sql)
        self.assertIn("CREATE INDEX IF NOT EXISTS threat_events_divergence", sql)

    def test_mock_normal_traffic(self):
        res = subprocess.run([_ANOMALY_BIN, "--mock-normal", "--json"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Normal check failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertFalse(data["is_anomaly"])
        self.assertLess(data["divergence"], 0.35)
        self.assertNotIn("threat_event", data)

    def test_mock_anomalous_traffic(self):
        res = subprocess.run([_ANOMALY_BIN, "--mock-anomaly", "--json"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Anomaly check failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertTrue(data["is_anomaly"])
        self.assertGreater(data["divergence"], 0.35)
        self.assertIn("threat_event", data)
        self.assertEqual(data["threat_event"]["emb_dim"], 768)
        self.assertEqual(data["threat_event"]["event_type"], "network_anomaly")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNetAnomaly)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
