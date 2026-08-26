#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE capability advertising and announce frames.
# AI-related: usr/libexec/mios/node/capabilities.py, src/mios-rs/mios-node/src/capabilities.rs
"""Automated tests for WS-NODE capabilities telemetry, Opcode 0x02 NodeAnnounce framing, and registry."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_CAP_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "capabilities.py")

spec = importlib.util.spec_from_file_location("capabilities", _CAP_PATH)
if spec and spec.loader:
    capabilities = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = capabilities
    spec.loader.exec_module(capabilities)
else:
    raise ImportError(f"Could not load capabilities module from {_CAP_PATH}")


class TestNodeCapabilities(unittest.TestCase):
    """Validates hardware capability probing, Opcode 0x02 Announce framing, and candidate registry queries."""

    def test_capability_probing_defaults(self):
        caps = capabilities.probe_node_capabilities()
        self.assertIsNotNone(caps.hardware.cpu_arch)
        self.assertGreater(caps.hardware.cpu_cores, 0)
        self.assertGreater(caps.hardware.ram_total_kb, 0)
        self.assertTrue(caps.engines.wasm_tier)
        self.assertTrue(caps.engines.native_tier)
        self.assertIn("127.0.0.1:8650", caps.transports.endpoints)

    def test_node_announce_frame_roundtrip(self):
        caps = capabilities.NodeCapabilities()
        caps.hardware.ram_total_kb = 16 * 1024 * 1024
        caps.hardware.ram_available_kb = 12 * 1024 * 1024
        caps.vram.gpu_vendor = "NVIDIA"
        caps.vram.gpu_model = "RTX 4090"
        caps.vram.vram_total_mb = 24576
        caps.vram.vram_available_mb = 20480
        caps.has_gpio = True

        announce = capabilities.NodeAnnouncePayload(
            node_id=142,
            hostname="edge-blade-alpha",
            capabilities=caps,
        )

        frame = announce.to_frame()
        self.assertEqual(frame.header.node_id, 142)
        self.assertEqual(frame.header.opcode, capabilities.MessageType.NODE_ANNOUNCE)

        # Wire serialization
        raw_bytes = frame.encode()
        self.assertEqual(len(raw_bytes), 16 + len(frame.payload))

        decoded_frame = capabilities.Frame.decode(raw_bytes)
        restored_announce = capabilities.NodeAnnouncePayload.from_frame(decoded_frame)

        self.assertEqual(restored_announce.node_id, 142)
        self.assertEqual(restored_announce.hostname, "edge-blade-alpha")
        self.assertEqual(restored_announce.capabilities.vram.gpu_vendor, "NVIDIA")
        self.assertEqual(restored_announce.capabilities.vram.vram_total_mb, 24576)
        self.assertTrue(restored_announce.capabilities.has_gpio)

    def test_capability_registry_filtering_and_eviction(self):
        registry = capabilities.CapabilityRegistry()

        # Node 1: IoT Edge blade with GPIO and 2GB RAM, no GPU
        caps1 = capabilities.NodeCapabilities()
        caps1.hardware.ram_available_kb = 2 * 1024 * 1024
        caps1.vram.vram_available_mb = 0
        caps1.has_gpio = True
        caps1.has_i2c = True
        ann1 = capabilities.NodeAnnouncePayload(node_id=101, hostname="iot-blade-1", capabilities=caps1)

        # Node 2: GPU worker with 8GB VRAM and 16GB RAM, no GPIO
        caps2 = capabilities.NodeCapabilities()
        caps2.hardware.ram_available_kb = 16 * 1024 * 1024
        caps2.vram.gpu_vendor = "NVIDIA"
        caps2.vram.vram_available_mb = 8192
        caps2.has_gpio = False
        ann2 = capabilities.NodeAnnouncePayload(node_id=102, hostname="gpu-worker-1", capabilities=caps2)

        # Node 3: Generic edge worker with 4GB RAM, no GPU, no GPIO
        caps3 = capabilities.NodeCapabilities()
        caps3.hardware.ram_available_kb = 4 * 1024 * 1024
        caps3.vram.vram_available_mb = 0
        ann3 = capabilities.NodeAnnouncePayload(node_id=103, hostname="generic-worker", capabilities=caps3)

        registry.register_announce(ann1, received_at=1000.0)
        registry.register_announce(ann2, received_at=1000.0)
        registry.register_announce(ann3, received_at=1000.0)

        self.assertEqual(registry.active_node_count(), 3)

        # 1. Query candidates requiring GPU VRAM >= 4096MB
        gpu_candidates = registry.find_eligible_nodes(min_vram_mb=4096)
        self.assertEqual(gpu_candidates, [102])

        # 2. Query candidates requiring GPIO access
        gpio_candidates = registry.find_eligible_nodes(require_gpio=True)
        self.assertEqual(gpio_candidates, [101])

        # 3. Query candidates requiring RAM >= 3GB
        ram_candidates = registry.find_eligible_nodes(min_ram_kb=3 * 1024 * 1024)
        self.assertEqual(ram_candidates, [102, 103])

        # 4. Stale eviction at t=1050 with max_age=30s
        evicted = registry.evict_stale(max_age_secs=30.0, now=1050.0)
        self.assertEqual(evicted, 3)
        self.assertEqual(registry.active_node_count(), 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeCapabilities)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
