#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS WirePlumber Bluetooth HD policy and virtual loopback provisioner.
# AI-doc: usr/share/doc/mios/manual/desktop.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "audio"))
from wireplumber_manager import WirePlumberManager

class TestWirePlumberManager(unittest.TestCase):
    def setUp(self):
        self.mgr = WirePlumberManager(dry_run=True)

    def test_render_bluez_config(self):
        conf = self.mgr.render_bluez_config()
        self.assertIn('"bluez5.codecs" = [ "ldac", "aptx_hd", "aptx", "aac", "sbc" ]', conf)
        self.assertIn('"bluez5.ldac.quality" = "hq"', conf)

    def test_render_virtual_loopbacks_config(self):
        conf = self.mgr.render_virtual_loopbacks_config()
        self.assertIn("Virtual-Agent-Mic", conf)
        self.assertIn("Virtual-Agent-Speaker", conf)
        self.assertIn("audio.rate = 48000", conf)

if __name__ == "__main__":
    unittest.main()
