#!/usr/bin/env python3
# AI-hint: Unit test for audit-version-literals.py -- asserts the repo-wide version-literal scanner runs and returns the (results, counts) shape the audit TSV is built from.
# AI-related: tools/audit-version-literals.py, usr/share/mios/reference/version-literals-audit.tsv
# AI-functions: test_scan_repo_runs

import unittest
import os

import importlib.util
spec = importlib.util.spec_from_file_location("audit_version_literals", os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit-version-literals.py"))
audit_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_mod)
scan_repo = audit_mod.scan_repo

class TestAuditVersionLiterals(unittest.TestCase):
    def test_scan_repo_runs(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tsv = os.path.join(root, "usr", "share", "mios", "reference", "version-literals-audit.tsv")
        if os.path.exists(tsv):
            results, counts = scan_repo(root)
            self.assertIsInstance(results, list)
            self.assertIsInstance(counts, dict)

if __name__ == "__main__":
    unittest.main()
