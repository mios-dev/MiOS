#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS VPN Kill-Switch and fwmark split-tunnel manager.
# AI-doc: usr/share/doc/mios/manual/networking.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "net"))
from vpn_killswitch import VPNKillSwitchManager, DEFAULT_VPN_TABLE, DEFAULT_FWMARK


class TestVPNKillSwitchManager(unittest.TestCase):
    def setUp(self):
        self.mgr = VPNKillSwitchManager(
            vpn_interface="wg0",
            local_cidrs=["10.0.0.0/8", "192.168.1.0/24", "::1/128"],
            dns_server="127.0.0.1",
            dns_port=53,
            fwmark="0x100",
            dry_run=True,
        )

    def test_render_rules_table_and_sets(self):
        rules = self.mgr.render_nftables_rules(vpn_peer_endpoints=["198.51.100.1:51820"])
        self.assertIn(f"table {DEFAULT_VPN_TABLE}", rules)
        self.assertIn("set local_ipv4", rules)
        self.assertIn("10.0.0.0/8, 192.168.1.0/24", rules)
        self.assertIn("set local_ipv6", rules)
        self.assertIn("::1/128", rules)

    def test_render_rules_split_tunnel_fwmark(self):
        rules = self.mgr.render_nftables_rules()
        self.assertIn("chain output_mangle", rules)
        self.assertIn("meta mark set 0x100 accept", rules)
        self.assertIn("chain output_filter", rules)
        self.assertIn("policy drop;", rules)
        self.assertIn("meta mark 0x100 accept", rules)

    def test_render_rules_dns_and_peer_whitelist(self):
        rules = self.mgr.render_nftables_rules(vpn_peer_endpoints=["203.0.113.50:51820"])
        self.assertIn("ip daddr 127.0.0.1 udp dport 53 accept", rules)
        self.assertIn("ip daddr 127.0.0.1 tcp dport 53 accept", rules)
        self.assertIn("ip daddr 203.0.113.50 udp dport 51820 accept", rules)

    def test_dry_run_apply_and_flush(self):
        rules = self.mgr.render_nftables_rules()
        res_apply = self.mgr.apply_rules(rules)
        self.assertEqual(res_apply["status"], "dry_run")
        self.assertFalse(res_apply["applied"])

        res_flush = self.mgr.flush_rules()
        self.assertEqual(res_flush["status"], "dry_run")
        self.assertFalse(res_flush["flushed"])


if __name__ == "__main__":
    unittest.main()
