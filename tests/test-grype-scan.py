#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Grype vulnerability scanner and CVE policy gate.
# AI-related: usr/libexec/mios/sec/grype_scan.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for GrypeScanner and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "grype_scan.py")

spec = importlib.util.spec_from_file_location("grype_scan", _TARGET_PATH)
if spec and spec.loader:
    grype_scan = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = grype_scan
    spec.loader.exec_module(grype_scan)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestGrypeScan(unittest.TestCase):
    """Test suite for Grype vulnerability report parsing, policy evaluation, exemptions, and SARIF export."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-grype-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_scan_mock(self):
        scanner = grype_scan.GrypeScanner(mock=True)
        raw_res = scanner.run_scan("/")
        self.assertIn("matches", raw_res)
        self.assertGreaterEqual(len(raw_res["matches"]), 1)

    def test_parse_vulnerabilities_normalization(self):
        scanner = grype_scan.GrypeScanner(mock=True)
        sample_output = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2026-9999",
                        "severity": "Critical",
                        "description": "Critical remote code execution vulnerability",
                        "fix": {"versions": ["2.0.1"], "state": "fixed"},
                    },
                    "artifact": {
                        "name": "core-daemon",
                        "version": "2.0.0",
                        "type": "rpm",
                    },
                }
            ]
        }
        vulns = scanner.parse_vulnerabilities(sample_output)
        self.assertEqual(len(vulns), 1)
        self.assertEqual(vulns[0]["id"], "CVE-2026-9999")
        self.assertEqual(vulns[0]["severity"], "CRITICAL")
        self.assertEqual(vulns[0]["package"], "core-daemon")
        self.assertEqual(vulns[0]["fix_state"], "fixed")

    def test_evaluate_policy_blocked_on_unexempted_high(self):
        scanner = grype_scan.GrypeScanner(mock=True)
        vulns = [
            {
                "id": "CVE-2026-1001",
                "severity": "HIGH",
                "package": "libssl",
                "version": "3.0.0",
                "fix_state": "fixed",
                "fix_versions": ["3.0.1"],
            }
        ]
        # Without exemption -> blocked
        res_blocked = scanner.evaluate_policy(vulns, max_severity="HIGH", fail_on_fixable=True, exemptions=[])
        self.assertEqual(res_blocked["status"], "fail")
        self.assertTrue(res_blocked["blocked"])
        self.assertEqual(len(res_blocked["actionable_cves"]), 1)

        # With exemption -> passes
        res_exempt = scanner.evaluate_policy(vulns, max_severity="HIGH", fail_on_fixable=True, exemptions=["CVE-2026-1001"])
        self.assertEqual(res_exempt["status"], "pass")
        self.assertFalse(res_exempt["blocked"])
        self.assertIn("CVE-2026-1001", res_exempt["exempted_cves"])

    def test_format_sarif_schema(self):
        scanner = grype_scan.GrypeScanner(mock=True)
        vulns = [
            {
                "id": "CVE-2026-1001",
                "severity": "HIGH",
                "package": "libcrypto",
                "version": "1.0",
                "description": "Buffer overflow",
            }
        ]
        sarif = scanner.format_sarif(vulns)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertIn("runs", sarif)
        self.assertEqual(len(sarif["runs"][0]["results"]), 1)
        self.assertEqual(sarif["runs"][0]["results"][0]["ruleId"], "CVE-2026-1001")

    def test_cli_execution_with_exemptions(self):
        test_args = [
            "grype_scan.py",
            "--target", "/",
            "--severity", "HIGH",
            "--exemptions", "CVE-2026-1001",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = grype_scan.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_sarif_export(self):
        sarif_file = os.path.join(self.temp_dir.name, "report.sarif")
        test_args = [
            "grype_scan.py",
            "--target", "/",
            "--exemptions", "CVE-2026-1001",
            "--sarif-out", sarif_file,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = grype_scan.main()
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.exists(sarif_file))


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGrypeScan)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
