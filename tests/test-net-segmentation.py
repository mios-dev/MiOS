#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Zero-Trust nftables container network segmentation.
# AI-related: usr/libexec/mios/sec/net_segmentation.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for NetSegmentationManager and CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "net_segmentation.py")

spec = importlib.util.spec_from_file_location("net_segmentation", _TARGET_PATH)
if spec and spec.loader:
    net_segmentation = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = net_segmentation
    spec.loader.exec_module(net_segmentation)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestNetSegmentation(unittest.TestCase):
    """Test suite for nftables isolation ruleset generation, pairing matrix validation, and apply/flush."""

    def test_generate_nftables_rules_structure(self):
        mgr = net_segmentation.NetSegmentationManager(mock=True)
        rules = mgr.generate_nftables_rules(subnet="10.88.0.0/16")
        self.assertIn("table inet mios_isolation", rules)
        self.assertIn("chain forward_containers", rules)
        self.assertIn("policy drop", rules)
        self.assertIn("dport 8642", rules)  # hermes
        self.assertIn("dport 5432", rules)  # pgvector
        self.assertIn("dport 11450", rules)  # llm-light
        self.assertIn("log prefix \"MIOS-NET-DROP: \"", rules)

    def test_validate_pairing_matrix_valid_default(self):
        mgr = net_segmentation.NetSegmentationManager(mock=True)
        valid, violations = mgr.validate_pairing_matrix(mgr.DEFAULT_ALLOWED_PAIRINGS)
        self.assertTrue(valid)
        self.assertEqual(len(violations), 0)

    def test_validate_pairing_matrix_rejects_forbidden_pairings(self):
        mgr = net_segmentation.NetSegmentationManager(mock=True)
        bad_pairings = [
            {"src": "open-webui", "dst": "pgvector", "port": 5432},
            {"src": "open-webui", "dst": "llm-heavy", "port": 11441},
        ]
        valid, violations = mgr.validate_pairing_matrix(bad_pairings)
        self.assertFalse(valid)
        self.assertGreaterEqual(len(violations), 2)
        self.assertTrue(any("Direct UI-to-DB" in v for v in violations))

    def test_apply_and_flush_rules_mock(self):
        mgr = net_segmentation.NetSegmentationManager(mock=True)
        rules = mgr.generate_nftables_rules()
        self.assertTrue(mgr.apply_rules(rules))
        self.assertTrue(mgr.flush_isolation())

    def test_cli_execution_generate(self):
        test_args = [
            "net_segmentation.py",
            "--generate",
            "--subnet", "10.88.0.0/16",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = net_segmentation.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_validate_matrix(self):
        test_args = [
            "net_segmentation.py",
            "--validate-matrix",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = net_segmentation.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_apply(self):
        test_args = [
            "net_segmentation.py",
            "--apply",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = net_segmentation.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNetSegmentation)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
