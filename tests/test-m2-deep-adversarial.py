#!/usr/bin/env python3
# AI-hint: Deep adversarial integration and property fuzzing test suite for Milestone 2 (T-392 through T-396).
# AI-related: usr/libexec/mios/node/scheduler.py, usr/libexec/mios/node/buffer_pool.py, usr/libexec/mios/node/capabilities.py, usr/libexec/mios/node/ble.py, usr/libexec/mios/node/overlay.py

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import importlib.util
import json
import os
import sys
import threading
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_NODE_DIR = os.path.join(_ROOT, "usr", "libexec", "mios", "node")

def _import_module(name: str, filename: str):
    path = os.path.join(_NODE_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise ImportError(f"Could not import {name} from {path}")

scheduler_mod = _import_module("scheduler", "scheduler.py")
buffer_pool_mod = _import_module("buffer_pool", "buffer_pool.py")
capabilities_mod = _import_module("capabilities", "capabilities.py")
ble_mod = _import_module("ble", "ble.py")
overlay_mod = _import_module("overlay", "overlay.py")

class TestM2DeepAdversarial(unittest.TestCase):
    """Deep adversarial challenges and edge case fuzzers for Milestone 2."""

    # ---------------------------------------------------------------------
    # 1. Scheduler (T-392)
    # ---------------------------------------------------------------------
    def test_scheduler_pinning_matrix_and_stealable(self):
        # A. Hardware pinned
        t_hw = scheduler_mod.TaskItem(task_id=1, priority=scheduler_mod.TaskPriority.CRITICAL, pinned_hardware=True)
        self.assertFalse(t_hw.is_stealable(None))
        self.assertFalse(t_hw.is_stealable(101))
        self.assertFalse(t_hw.is_stealable(202))

        # B. Node pinned to 101 only
        t_node = scheduler_mod.TaskItem(task_id=2, priority=scheduler_mod.TaskPriority.HIGH, pinned_node_id=101)
        self.assertFalse(t_node.is_stealable(None))
        self.assertTrue(t_node.is_stealable(101))
        self.assertFalse(t_node.is_stealable(102))

        # C. Both
        t_both = scheduler_mod.TaskItem(task_id=3, priority=scheduler_mod.TaskPriority.NORMAL, pinned_hardware=True, pinned_node_id=101)
        self.assertFalse(t_both.is_stealable(101))

        # D. Unpinned
        t_free = scheduler_mod.TaskItem(task_id=4, priority=scheduler_mod.TaskPriority.LOW)
        self.assertTrue(t_free.is_stealable(None))
        self.assertTrue(t_free.is_stealable(101))
        self.assertTrue(t_free.is_stealable(999))

    def test_scheduler_high_concurrency_race_stress(self):
        sched = scheduler_mod.WorkStealingScheduler(local_node_id=50, num_workers=4)
        total_tasks = 400

        # Enqueue 400 tasks with mixed pinning
        for i in range(total_tasks):
            prio = scheduler_mod.TaskPriority(i % 4)
            is_pinned = (i % 5 == 0)
            pinned_node = 50 if (i % 3 == 0 and not is_pinned) else None
            t = scheduler_mod.TaskItem(
                task_id=i,
                priority=prio,
                pinned_hardware=is_pinned,
                pinned_node_id=pinned_node,
            )
            sched.submit_task(t, worker_hint=(i % 4 if i % 2 == 0 else None))

        executed: list[int] = []
        lock = threading.Lock()

        def worker_loop(wid: int):
            while True:
                task = sched.pop_task(wid)
                if task is None:
                    break
                with lock:
                    executed.append(task.task_id)

        threads = [threading.Thread(target=worker_loop, args=(i,)) for i in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        self.assertEqual(len(executed), total_tasks)
        self.assertEqual(len(set(executed)), total_tasks)
        self.assertEqual(sched.total_queue_depth(), 0)

    # ---------------------------------------------------------------------
    # 2. Buffer Pool (T-393)
    # ---------------------------------------------------------------------
    def test_buffer_pool_boundaries_and_slicing(self):
        pool = buffer_pool_mod.BufferPool()

        # Boundaries
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(0), buffer_pool_mod.BucketTier.SMALL)
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(256), buffer_pool_mod.BucketTier.SMALL)
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(257), buffer_pool_mod.BucketTier.MEDIUM)
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(4096), buffer_pool_mod.BucketTier.MEDIUM)
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(4097), buffer_pool_mod.BucketTier.LARGE)
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(65536), buffer_pool_mod.BucketTier.LARGE)
        self.assertEqual(buffer_pool_mod.BucketTier.from_size(65537), buffer_pool_mod.BucketTier.HUGE)

        # Zero-copy slicing & split
        with pool.acquire(100) as buf:
            buf.extend(b"0123456789ABCDEF")
            self.assertEqual(bytes(buf.slice(0, 4)), b"0123")
            self.assertEqual(bytes(buf.slice(4, 16)), b"456789ABCDEF")

            # Out of bounds
            p_full = buf.slice(0, 16)
            self.assertEqual(bytes(p_full), b"0123456789ABCDEF")

            # Split prefix
            p1 = buf.split_prefix(4)
            self.assertEqual(p1, b"0123")
            self.assertEqual(bytes(buf.as_bytes()), b"456789ABCDEF")

            with self.assertRaises(IndexError):
                buf.split_prefix(100)

    def test_buffer_pool_multithreaded_churn(self):
        pool = buffer_pool_mod.BufferPool()
        num_threads = 8
        iterations = 100

        def churn():
            for i in range(iterations):
                sz = 128 if i % 2 == 0 else 2048
                with pool.acquire(sz) as buf:
                    buf.extend(b"CHURN_DATA")
                    self.assertEqual(bytes(buf.slice(0, 5)), b"CHURN")

        threads = [threading.Thread(target=churn) for _ in range(num_threads)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        stats = pool.get_stats()
        self.assertEqual(stats.active_leased, 0)
        self.assertEqual(stats.allocations, num_threads * iterations)
        self.assertGreater(stats.recycles, 0)

    # ---------------------------------------------------------------------
    # 3. Capabilities (T-394)
    # ---------------------------------------------------------------------
    def test_capabilities_filtering_and_eviction(self):
        registry = capabilities_mod.CapabilityRegistry()

        for i in range(1, 21):
            caps = capabilities_mod.NodeCapabilities(
                hardware=capabilities_mod.HardwareSpecs(ram_available_kb=i * 1024 * 1024),
                vram=capabilities_mod.VramTelemetry(vram_available_mb=(i * 256 if i % 2 == 0 else 0)),
                has_gpio=(i % 2 == 0),
                has_i2c=(i % 3 == 0),
            )
            payload = capabilities_mod.NodeAnnouncePayload(
                node_id=i,
                hostname=f"node-{i}",
                capabilities=caps,
            )
            registry.register_announce(payload, received_at=1000.0 + i * 10.0)

        self.assertEqual(registry.active_node_count(), 20)

        # Match VRAM >= 1024MB AND GPIO = True
        matched = registry.find_eligible_nodes(min_ram_kb=1024, min_vram_mb=1024, require_gpio=True)
        self.assertTrue(len(matched) > 0)
        for nid in matched:
            c = registry.get_capabilities(nid)
            self.assertIsNotNone(c)
            self.assertGreaterEqual(c.vram.vram_available_mb, 1024)
            self.assertTrue(c.has_gpio)

        # Stale eviction at t=1200 with max_age=50
        evicted = registry.evict_stale(max_age_secs=50.0, now=1200.0)
        self.assertGreater(evicted, 0)

    # ---------------------------------------------------------------------
    # 4. BLE Bootstrap (T-395)
    # ---------------------------------------------------------------------
    def test_ble_bootstrap_tamper_rejection(self):
        adapter = ble_mod.MockBleAdapter()
        bootstrap = ble_mod.BleMeshBootstrap(node_id=99, adapter=adapter)
        bootstrap.start()

        self.assertTrue(adapter.is_advertising())
        self.assertEqual(bootstrap.state, ble_mod.BleBootstrapState.UNPROVISIONED)

        # Handshake
        client_priv = x25519.X25519PrivateKey.generate()
        client_pub = client_priv.public_key().public_bytes(
            encoding=ble_mod.serialization.Encoding.Raw,
            format=ble_mod.serialization.PublicFormat.Raw,
        )
        bootstrap.handle_ecdh_exchange(client_pub)
        self.assertEqual(bootstrap.state, ble_mod.BleBootstrapState.HANDSHAKING)

        # Encrypt creds
        creds = ble_mod.ProvisioningPayload(
            ssid="AdvSSID",
            psk="AdvPass123",
            cluster_token="adv-tok",
            coordinator_endpoint="1.2.3.4:8650",
        )
        node_pub = x25519.X25519PublicKey.from_public_bytes(bootstrap.public_bytes)
        shared_secret = client_priv.exchange(node_pub)

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ble_mod.BLE_HKDF_SALT,
            info=ble_mod.BLE_HKDF_INFO,
        )
        session_key = hkdf.derive(shared_secret)

        aead = ChaCha20Poly1305(session_key)
        json_bytes = json.dumps(creds.to_dict()).encode("utf-8")
        ciphertext = bytearray(aead.encrypt(ble_mod.BLE_NONCE, json_bytes, ble_mod.BLE_AEAD_AAD))

        # Tamper ciphertext
        ciphertext[len(ciphertext) // 2] ^= 0xFF
        with self.assertRaises(Exception):
            bootstrap.handle_provisioning_write(bytes(ciphertext))

        self.assertNotEqual(bootstrap.state, ble_mod.BleBootstrapState.PROVISIONED)

        # Untampered write succeeds
        untampered = aead.encrypt(ble_mod.BLE_NONCE, json_bytes, ble_mod.BLE_AEAD_AAD)
        prov = bootstrap.handle_provisioning_write(untampered)
        self.assertEqual(prov.ssid, "AdvSSID")
        self.assertEqual(bootstrap.state, ble_mod.BleBootstrapState.PROVISIONED)
        self.assertFalse(adapter.is_advertising())

    # ---------------------------------------------------------------------
    # 5. Multi-Transport Overlay (T-396)
    # ---------------------------------------------------------------------
    def test_overlay_anti_flap_flapping_stress(self):
        config = overlay_mod.HysteresisConfig(
            fail_strikes_threshold=3,
            recovery_dwell_ms=10_000,
            recovery_strikes_threshold=3,
        )
        router = overlay_mod.MultiTransportRouter(config=config)

        router.register_peer(
            node_id=888,
            endpoints={
                overlay_mod.TransportType.LAN_BROADCAST: "192.168.1.88:8650",
                overlay_mod.TransportType.WIREGUARD: "10.0.0.88:8650",
                overlay_mod.TransportType.TAILSCALE: "100.64.0.88:8650",
            },
        )

        # 1. 3 strikes -> Failover to WireGuard
        for i in range(1, 4):
            router.record_missed_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, now_ms=i * 1000)

        self.assertTrue(router.is_peer_partitioned(888))
        self.assertEqual(router.select_route(888)[0], overlay_mod.TransportType.WIREGUARD)

        # 2. Intermittent probes during dwell
        router.record_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=4000)
        router.record_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=5000)
        router.record_missed_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, now_ms=6000) # Resets strikes

        # 3. 3 probes but dwell not reached
        router.record_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=7000)
        router.record_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=8000)
        router.record_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=9000)
        self.assertEqual(router.select_route(888)[0], overlay_mod.TransportType.WIREGUARD)

        # 4. Clean probe after dwell (t=20000 -> 13000ms elapsed >= 10000ms)
        router.record_heartbeat(888, overlay_mod.TransportType.LAN_BROADCAST, latency_ms=1, now_ms=20000)
        self.assertEqual(router.select_route(888)[0], overlay_mod.TransportType.LAN_BROADCAST)
        self.assertFalse(router.is_peer_partitioned(888))

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestM2DeepAdversarial)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
