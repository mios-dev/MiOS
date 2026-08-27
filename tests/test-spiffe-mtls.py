#!/usr/bin/env python3
# AI-hint: Automated unit test suite for SPIFFE/SPIRE workload identity, mTLS validation, and cert rotation.
# AI-related: usr/libexec/mios/sec/spiffe_identity.py, usr/share/mios/mios.toml
"""Unit and integration test suite for SpiffeIdentityAgent and spiffe_identity CLI (T-568)."""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "spiffe_identity.py")

spec = importlib.util.spec_from_file_location("spiffe_identity", _TARGET_PATH)
if spec and spec.loader:
    spiffe_identity = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = spiffe_identity
    spec.loader.exec_module(spiffe_identity)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestSpiffeIdentityMtls(unittest.TestCase):
    """Test suite for SPIFFE ID parsing, SVID issuance, trust domain validation, and rotation."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-test-spiffe-")
        self.cache_file = os.path.join(self.tmpdir.name, "spiffe-cache.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_spiffe_id_formatting_and_parsing(self):
        uri = spiffe_identity.format_spiffe_id("mios.cluster", "node-alpha", "agent-pipe")
        self.assertEqual(uri, "spiffe://mios.cluster/node/node-alpha/workload/agent-pipe")

        parsed = spiffe_identity.parse_spiffe_id(uri)
        self.assertEqual(parsed["trust_domain"], "mios.cluster")
        self.assertEqual(parsed["node_id"], "node-alpha")
        self.assertEqual(parsed["workload"], "agent-pipe")

    def test_spiffe_id_parse_invalid_scheme(self):
        with self.assertRaises(ValueError):
            spiffe_identity.parse_spiffe_id("https://mios.cluster/node/node-01/workload/app")

    def test_issue_svid_mock(self):
        agent = spiffe_identity.SpiffeIdentityAgent(
            trust_domain="mios.cluster",
            node_id="node-01",
            cache_path=self.cache_file,
            mock=True,
        )
        res = agent.issue_svid("mios-llm-light", validity_hours=24)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "issued")
        self.assertEqual(
            res["spiffe_id"],
            "spiffe://mios.cluster/node/node-01/workload/mios-llm-light",
        )
        self.assertIn("cert_pem", res["svid"])
        self.assertIn("key_pem", res["svid"])

    def test_validate_svid_valid(self):
        agent = spiffe_identity.SpiffeIdentityAgent(mock=True)
        res = agent.issue_svid("hermes-gateway")
        val = agent.validate_svid(res["svid"])
        self.assertTrue(val["valid"])
        self.assertEqual(val["status"], "valid")
        self.assertEqual(val["workload"], "hermes-gateway")

    def test_validate_svid_expired(self):
        agent = spiffe_identity.SpiffeIdentityAgent(mock=True)
        expired_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
        bad_svid = {
            "spiffe_id": "spiffe://mios.cluster/node/node-01/workload/old-task",
            "expires_at": expired_time,
        }
        val = agent.validate_svid(bad_svid)
        self.assertFalse(val["valid"])
        self.assertEqual(val["status"], "expired")

    def test_validate_svid_trust_domain_mismatch(self):
        agent = spiffe_identity.SpiffeIdentityAgent(trust_domain="mios.cluster", mock=True)
        foreign_svid = {
            "spiffe_id": "spiffe://alien.cluster/node/node-01/workload/infiltrator",
            "expires_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)).isoformat(),
        }
        val = agent.validate_svid(foreign_svid)
        self.assertFalse(val["valid"])
        self.assertEqual(val["status"], "trust_domain_mismatch")

    def test_rotate_svids_dynamic_in_memory(self):
        agent = spiffe_identity.SpiffeIdentityAgent(cache_path=self.cache_file, mock=True)
        # Issue one long-lived (24h) and one near-expiry (1h) SVID
        agent.issue_svid("service-fresh", validity_hours=24)
        agent.issue_svid("service-expiring", validity_hours=1)

        cache = agent.load_cache()
        old_expiring_fp = cache["svids"]["service-expiring"]["fingerprint"]

        # Run rotation with min_ttl_hours=4.0 -> service-expiring should rotate, service-fresh should not
        rot_res = agent.rotate_svids(force=False, min_ttl_hours=4.0)
        self.assertTrue(rot_res["success"])
        self.assertIn("service-expiring", rot_res["rotated_workloads"])
        self.assertIn("service-fresh", rot_res["unchanged_workloads"])

        new_cache = agent.load_cache()
        new_expiring_fp = new_cache["svids"]["service-expiring"]["fingerprint"]
        self.assertNotEqual(old_expiring_fp, new_expiring_fp)

    def test_force_rotate_all_svids(self):
        agent = spiffe_identity.SpiffeIdentityAgent(cache_path=self.cache_file, mock=True)
        agent.issue_svid("wl-1", validity_hours=24)
        agent.issue_svid("wl-2", validity_hours=24)

        rot_res = agent.rotate_svids(force=True)
        self.assertEqual(rot_res["total_rotated"], 2)
        self.assertIn("wl-1", rot_res["rotated_workloads"])
        self.assertIn("wl-2", rot_res["rotated_workloads"])

    def test_status_output(self):
        agent = spiffe_identity.SpiffeIdentityAgent(cache_path=self.cache_file, mock=True)
        agent.issue_svid("db-pgvector", validity_hours=24)
        status = agent.get_status()
        self.assertEqual(status["active_svids_count"], 1)
        self.assertEqual(status["trust_domain"], "mios.cluster")
        self.assertEqual(status["svids"][0]["workload"], "db-pgvector")

    def test_cli_execution_mock(self):
        with patch.object(sys, "argv", ["spiffe_identity.py", "--mock", "--issue", "--workload", "cli-test", "--json"]):
            code = spiffe_identity.main()
            self.assertEqual(code, 0)

        with patch.object(sys, "argv", ["spiffe_identity.py", "--mock", "--status", "--json"]):
            code = spiffe_identity.main()
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
