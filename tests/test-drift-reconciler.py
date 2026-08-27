#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS configuration drift auditor and 3-way overlay reconciler.
# AI-doc: usr/share/doc/mios/manual/architecture.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "cfg"))
from drift_reconciler import ConfigDriftReconciler

class TestConfigDriftReconciler(unittest.TestCase):
    def setUp(self):
        self.reconciler = ConfigDriftReconciler(dry_run=True)

    def test_audit_layer_drift_mock(self):
        res = self.reconciler.audit_layer_drift()
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["synced"])
        self.assertEqual(len(res["conflicts"]), 0)

    def test_reconcile_state_mock(self):
        res = self.reconciler.reconcile_state()
        self.assertEqual(res["status"], "reconciled")
        self.assertEqual(res["state"], "consistent")

if __name__ == "__main__":
    unittest.main()
