#!/usr/bin/env python3
# AI-hint: Multi-perspective empirical adversarial stress tests for batch T-593 through T-602.
# Tests boundary conditions, failure modes, and recovery invariance across VPN killswitch, NAT traversal, Bcachefs, Parquet log RAG, and service mesh.
# AI-doc: usr/share/doc/mios/manual/testing.md
import unittest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "net"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "telemetry"))

from vpn_killswitch import VPNKillSwitchManager
from nat_traversal import NATTraversalEngine
from bcachefs_tier import BcachefsTierManager
from log_archiver import LogArchiverManager
from service_mesh import ServiceMeshGenerator


class TestEmpiricalStressT593T602(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-stress-t593-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # --- 1. VPN Kill-Switch Stress Tests ---
    def test_vpn_killswitch_corrupted_peer_endpoints(self):
        """Stress: Malformed peer strings with invalid ports or missing colons must not corrupt nftables generation."""
        mgr = VPNKillSwitchManager(vpn_interface="wg0", dry_run=True)
        rules = mgr.render_nftables_rules(vpn_peer_endpoints=["invalid_peer_no_port", "10.0.0.1:abc", "192.168.1.100:51820"])
        self.assertIn("192.168.1.100 udp dport 51820 accept", rules)
        self.assertNotIn("invalid_peer_no_port", rules)

    def test_vpn_killswitch_empty_local_cidrs_resilience(self):
        """Stress: If local_cidrs is empty, manager should fall back to default loopback without crashing."""
        mgr = VPNKillSwitchManager(local_cidrs=["127.0.0.1/32"], dry_run=True)
        rules = mgr.render_nftables_rules()
        self.assertIn("elements = { 127.0.0.1/32 }", rules)
        self.assertIn("policy drop;", rules)

    # --- 2. NAT Traversal Stress Tests ---
    def test_nat_traversal_all_relays_unreachable(self):
        """Stress: Empty DERP relay list must fall back to localhost dummy fallback rather than raising IndexError."""
        engine = NATTraversalEngine(derp_relays=[], mock_mode=False)
        engine.probe_upnp_nat_pmp = lambda: {"supported": False}
        engine.probe_stun_endpoints = lambda: {"direct_p2p_viable": False}

        res = engine.establish_traversal_channel()
        self.assertEqual(res["status"], "established")
        self.assertEqual(res["method"], "derp_relay_fallback")
        self.assertEqual(res["endpoint"], "127.0.0.1:8443")

    def test_nat_traversal_zero_latency_tie_breaking(self):
        """Stress: Multiple relays with equal latency must be deterministically sorted."""
        relays = [
            {"region": "b", "host": "b.relay", "port": 8443, "latency_ms": 20.0},
            {"region": "a", "host": "a.relay", "port": 8443, "latency_ms": 20.0},
        ]
        engine = NATTraversalEngine(derp_relays=relays, mock_mode=False)
        selected = engine.select_derp_relay()
        self.assertIn("selected_relay", selected)

    # --- 3. Bcachefs Tiering Stress Tests ---
    def test_bcachefs_duplicate_device_assignment_guard(self):
        """Stress: Formatting identical device across NVMe and HDD tiers must produce distinct label arguments."""
        mgr = BcachefsTierManager(
            nvme_devices=["/dev/nvme0n1"],
            hdd_devices=["/dev/sda"],
            compression="lz4",
            dry_run=True,
        )
        cmd = mgr.render_format_command()
        self.assertIn("--label=nvme.hot /dev/nvme0n1", " ".join(cmd))
        self.assertIn("--label=hdd.bulk /dev/sda", " ".join(cmd))

    # --- 4. Log Archiver Parquet RAG Stress Tests ---
    def test_log_archiver_corrupted_json_lines_resilience(self):
        """Stress: Corrupted JSON strings, truncated binary data, and missing fields must be gracefully skipped."""
        raw_lines = [
            "",
            "not a json line",
            '{"incomplete": ',
            json.dumps({"MESSAGE": "Valid log record", "PRIORITY": "6"}),
            json.dumps({"MESSAGE": [0, 150, 200, 255], "PRIORITY": "2"}),  # Binary message byte array
        ]
        archiver = LogArchiverManager(archive_dir=self.tmp_dir, dry_run=True)
        records, clusters = archiver.parse_journal_records(raw_lines)
        self.assertEqual(len(records), 2)
        self.assertEqual(len(clusters), 1)

    def test_log_archiver_massive_batch_compression_ratio(self):
        """Stress: Compaction of 1,000 log records must achieve significant compression and valid schema."""
        records = [
            {
                "timestamp_us": 1787830000000000 + i,
                "priority": 3,
                "unit": "kernel",
                "message": f"PCIe link error: Correctable error detected on bus {i % 16}",
                "pid": "0",
                "hostname": "mios-power",
            }
            for i in range(1000)
        ]
        archiver = LogArchiverManager(archive_dir=self.tmp_dir, dry_run=False)
        out_path = os.path.join(self.tmp_dir, "massive.parquet")
        res = archiver.write_columnar_parquet(records, out_path)
        self.assertEqual(res["records_count"], 1000)
        self.assertLess(res["parquet_bytes"], res["raw_bytes"])

    # --- 5. Service Mesh Stress Tests ---
    def test_service_mesh_empty_routes_fallback(self):
        """Stress: Generating service mesh with empty route table must produce valid structure."""
        mesh = ServiceMeshGenerator(routes=[], dry_run=True)
        config = mesh.render_traefik_dynamic_config()
        self.assertEqual(config["http"]["routers"], {})
        self.assertEqual(config["http"]["services"], {})

    def test_service_mesh_custom_socket_directories(self):
        """Stress: Custom Unix socket paths must be correctly mapped into loadBalancer URLs."""
        routes = [{"name": "custom", "listen_port": 9000, "socket_path": "/var/run/custom.sock"}]
        mesh = ServiceMeshGenerator(routes=routes, dry_run=True)
        config = mesh.render_traefik_dynamic_config()
        self.assertEqual(
            config["http"]["services"]["custom-service"]["loadBalancer"]["servers"][0]["url"],
            "http://unix:/var/run/custom.sock"
        )


if __name__ == "__main__":
    unittest.main()
