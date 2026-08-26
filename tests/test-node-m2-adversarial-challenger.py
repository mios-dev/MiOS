#!/usr/bin/env python3
# AI-hint: Milestone 2 Empirical Challenger Adversarial & Stress Test Suite (T-392 through T-396).
# AI-related: usr/libexec/mios/node/scheduler.py, usr/libexec/mios/node/buffer_pool.py, usr/libexec/mios/node/capabilities.py, usr/libexec/mios/node/ble.py, usr/libexec/mios/node/overlay.py

import os
import sys
import threading
import time
import unittest

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NODE_DIR = os.path.join(_ROOT_DIR, "usr", "libexec", "mios", "node")
if _NODE_DIR not in sys.path:
    sys.path.insert(0, _NODE_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from scheduler import (
    GlobalInjector,
    ScheduledDecision,
    ScheduledTargetType,
    TaskItem,
    TaskPriority,
    WorkerQueue,
    WorkStealingScheduler,
)
from buffer_pool import BucketTier, BufferPool, PooledBuffer
from capabilities import (
    ActiveTransports,
    CapabilityRegistry,
    EngineTiers,
    HardwareSpecs,
    NodeAnnouncePayload,
    NodeCapabilities,
    VramTelemetry,
)
from ble import (
    BLE_CHAR_ECDH_UUID,
    BLE_CHAR_IDENTITY_UUID,
    BLE_CHAR_PROVISION_UUID,
    BleBootstrapState,
    BleMeshBootstrap,
    MockBleAdapter,
    ProvisioningPayload,
    provision_remote_node,
)
from overlay import (
    HysteresisConfig,
    MultiTransportRouter,
    PeerRoute,
    TransportType,
)
from wire import Frame, MessageType


class TestM2AdversarialChallenger(unittest.TestCase):
    """Exhaustive empirical stress tests and edge case verification for Milestone 2."""

    # -------------------------------------------------------------------------
    # 1. T-392: Stress & Invariant Tests for Work-Stealing Scheduler
    # -------------------------------------------------------------------------
    def test_stress_concurrent_work_stealing_with_pinned_invariants(self):
        scheduler = WorkStealingScheduler(local_node_id=101, num_workers=4)
        num_tasks = 1000

        # Ingest tasks: 33% pinned hardware, 33% pinned to node 101, 33% unpinned
        for i in range(num_tasks):
            prio = TaskPriority(i % 4)
            pinned_hw = (i % 3 == 0)
            pinned_node = 101 if (i % 3 == 1) else (999 if (i % 7 == 0) else None)

            t = TaskItem(
                task_id=i,
                priority=prio,
                pinned_hardware=pinned_hw,
                pinned_node_id=pinned_node,
                code_bytes=b"CODE_PAYLOAD",
            )
            scheduler.submit_task(t, worker_hint=i % 4)

        completed_tasks = []
        lock = threading.Lock()
        stop_signal = threading.Event()

        def worker_loop(w_id: int):
            while not stop_signal.is_set():
                task = scheduler.pop_task(w_id)
                if task:
                    with lock:
                        completed_tasks.append((w_id, task))
                else:
                    time.sleep(0.0001)

        def stealer_loop(requester_id: int):
            while not stop_signal.is_set():
                stolen = scheduler.handle_remote_steal_request(requester_id, max_tasks=3)
                if stolen:
                    for task in stolen:
                        self.assertFalse(
                            task.pinned_hardware,
                            f"Remote peer {requester_id} stole task with pinned_hardware=True",
                        )
                        if task.pinned_node_id is not None:
                            self.assertEqual(
                                task.pinned_node_id,
                                requester_id,
                                f"Remote peer {requester_id} stole task pinned to {task.pinned_node_id}",
                            )
                        with lock:
                            completed_tasks.append((requester_id, task))
                else:
                    time.sleep(0.0001)

        threads = []
        for w_id in range(4):
            threads.append(threading.Thread(target=worker_loop, args=(w_id,)))
        for peer_id in [201, 202]:
            threads.append(threading.Thread(target=stealer_loop, args=(peer_id,)))

        for t in threads:
            t.start()

        # Wait until all tasks are consumed
        start = time.time()
        while len(completed_tasks) < num_tasks and (time.time() - start) < 5.0:
            time.sleep(0.01)

        stop_signal.set()
        for t in threads:
            t.join()

        self.assertEqual(len(completed_tasks), num_tasks)
        stats = scheduler.get_stats()
        self.assertEqual(stats.tasks_ingested, num_tasks)

    def test_scheduler_route_task_boundaries(self):
        scheduler = WorkStealingScheduler(local_node_id=101, num_workers=2)

        # 1. Hardware pinned task must ALWAYS be local
        t_hw = TaskItem(task_id=1, priority=TaskPriority.CRITICAL, pinned_hardware=True)
        decision = scheduler.route_task(t_hw, peer_loads=[(201, 0), (202, 0)])
        self.assertEqual(decision.target_type, ScheduledTargetType.LOCAL)

        # 2. Pinned to remote node 500
        t_remote = TaskItem(task_id=2, priority=TaskPriority.NORMAL, pinned_node_id=500)
        decision = scheduler.route_task(t_remote, peer_loads=[(500, 10)])
        self.assertEqual(decision.target_type, ScheduledTargetType.OFFLOAD)
        self.assertEqual(decision.node_id, 500)

        # 3. Pinned to local node 101
        t_local = TaskItem(task_id=3, priority=TaskPriority.NORMAL, pinned_node_id=101)
        decision = scheduler.route_task(t_local, peer_loads=[(201, 0)])
        self.assertEqual(decision.target_type, ScheduledTargetType.LOCAL)

    # -------------------------------------------------------------------------
    # 2. T-393: Stress & Invariant Tests for Zero-Copy Buffer Pool
    # -------------------------------------------------------------------------
    def test_stress_buffer_pool_multithreaded_leasing_and_slicing(self):
        pool = BufferPool()
        num_threads = 8
        ops_per_thread = 100

        def thread_task(tid: int):
            for i in range(ops_per_thread):
                size = 128 if (i % 2 == 0) else 4096
                with pool.acquire(size) as buf:
                    buf.extend(b"HEADER_16BYTES__DATA_BODY_CHUNK")
                    self.assertEqual(buf.slice(0, 16), memoryview(b"HEADER_16BYTES__"))
                    pref = buf.split_prefix(16)
                    self.assertEqual(pref, b"HEADER_16BYTES__")
                    self.assertEqual(buf.as_bytes(), b"DATA_BODY_CHUNK")

        threads = [threading.Thread(target=thread_task, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = pool.get_stats()
        self.assertEqual(stats.active_leased, 0)
        self.assertEqual(stats.allocations, num_threads * ops_per_thread)

    def test_adversarial_buffer_pool_slicing_edge_cases(self):
        pool = BufferPool()
        buf = pool.acquire(512)
        buf.extend(b"0123456789ABCDEF")

        # 1. Out-of-bounds split prefix
        with self.assertRaises(IndexError):
            buf.split_prefix(100)

        # 2. Double release should be idempotent
        buf.release()
        buf.release()

        # 3. Access after release should raise RuntimeError
        with self.assertRaises(RuntimeError):
            buf.as_bytes()
        with self.assertRaises(RuntimeError):
            buf.write(b"fail")

    # -------------------------------------------------------------------------
    # 3. T-394: Adversarial Capability Probing & Filtering
    # -------------------------------------------------------------------------
    def test_adversarial_capability_registry_extreme_queries(self):
        registry = CapabilityRegistry()

        # Empty registry queries
        self.assertEqual(registry.find_eligible_nodes(min_ram_kb=1000000), [])
        self.assertEqual(registry.active_node_count(), 0)
        self.assertEqual(registry.evict_stale(max_age_secs=60), 0)

        # Add node with extreme caps
        caps = NodeCapabilities(
            hardware=HardwareSpecs(ram_available_kb=32 * 1024 * 1024),
            vram=VramTelemetry(vram_available_mb=16384, has_npu=True),
            has_gpio=True,
            has_i2c=True,
        )
        payload = NodeAnnouncePayload(node_id=42, hostname="super-node", capabilities=caps)
        registry.register_announce(payload, received_at=1000)

        # Eligible queries
        matched = registry.find_eligible_nodes(
            min_ram_kb=16 * 1024 * 1024,
            min_vram_mb=8192,
            require_gpio=True,
            require_i2c=True,
        )
        self.assertEqual(matched, [42])

        # Impossible query
        self.assertEqual(registry.find_eligible_nodes(min_ram_kb=999999999), [])

        # Evict stale
        self.assertEqual(registry.evict_stale(max_age_secs=30, now=1050), 1)
        self.assertEqual(registry.active_node_count(), 0)

    # -------------------------------------------------------------------------
    # 4. T-395: Adversarial BLE AEAD Bit-Flip Fuzzing & Invalid Keys
    # -------------------------------------------------------------------------
    def test_adversarial_ble_bit_flip_fuzzing_and_key_validation(self):
        adapter = MockBleAdapter()
        bootstrap = BleMeshBootstrap(node_id=77, adapter=adapter)
        bootstrap.start()

        # 1. Invalid ECDH key lengths
        with self.assertRaises(ValueError):
            bootstrap.handle_ecdh_exchange(b"")
        with self.assertRaises(ValueError):
            bootstrap.handle_ecdh_exchange(b"\x00" * 16)
        with self.assertRaises(ValueError):
            bootstrap.handle_ecdh_exchange(b"\x00" * 33)

        # 2. Premature provisioning write
        with self.assertRaises(RuntimeError):
            bootstrap.handle_provisioning_write(b"\x00" * 32)

        # 3. Perform legitimate handshake
        creds = ProvisioningPayload(
            ssid="FuzzSSID",
            psk="Secret123",
            cluster_token="tok-123",
            coordinator_endpoint="10.0.0.1:8650",
        )
        provision_remote_node(adapter, creds)

        peer_pub = adapter.get_characteristic_value(BLE_CHAR_ECDH_UUID)
        bootstrap.handle_ecdh_exchange(peer_pub)

        valid_encrypted = adapter.get_characteristic_value(BLE_CHAR_PROVISION_UUID)
        self.assertTrue(len(valid_encrypted) > 0)

        # 4. Exhaustive single-byte bit flip fuzzing across all ciphertext bytes
        for i in range(len(valid_encrypted)):
            corrupted = bytearray(valid_encrypted)
            corrupted[i] ^= 0x01
            with self.assertRaises(Exception):
                bootstrap.handle_provisioning_write(bytes(corrupted))

        # 5. Valid write succeeds
        provisioned = bootstrap.handle_provisioning_write(valid_encrypted)
        self.assertEqual(provisioned.ssid, "FuzzSSID")
        self.assertEqual(bootstrap.state, BleBootstrapState.PROVISIONED)

    # -------------------------------------------------------------------------
    # 5. T-396: Stress & Boundary Tests for Multi-Transport Flapping & Hysteresis
    # -------------------------------------------------------------------------
    def test_stress_overlay_flapping_and_hysteresis_boundaries(self):
        config = HysteresisConfig(
            fail_strikes_threshold=3,
            recovery_dwell_ms=10_000,
            recovery_strikes_threshold=3,
        )
        router = MultiTransportRouter(config)

        endpoints = {
            TransportType.LAN_BROADCAST: "192.168.1.50:8650",
            TransportType.WIREGUARD: "10.0.0.50:8650",
            TransportType.TAILSCALE: "100.64.0.50:8650",
            TransportType.DIRECT_TCP: "192.168.1.50:9000",
        }
        router.register_peer(303, endpoints)

        # 1. Rapid alternating 1 miss, 1 hit -> LAN should NEVER failover
        for i in range(100):
            t = i * 100
            if i % 2 == 0:
                router.record_missed_heartbeat(303, TransportType.LAN_BROADCAST, now_ms=t)
            else:
                router.record_heartbeat(303, TransportType.LAN_BROADCAST, latency_ms=1, now_ms=t)
            self.assertEqual(router.select_route(303)[0], TransportType.LAN_BROADCAST)
            self.assertFalse(router.is_peer_partitioned(303))

        # 2. Failover on 3 consecutive misses
        router.record_missed_heartbeat(303, TransportType.LAN_BROADCAST, now_ms=10_000)
        router.record_missed_heartbeat(303, TransportType.LAN_BROADCAST, now_ms=11_000)
        self.assertFalse(router.is_peer_partitioned(303))

        router.record_missed_heartbeat(303, TransportType.LAN_BROADCAST, now_ms=12_000)
        self.assertTrue(router.is_peer_partitioned(303))
        self.assertEqual(router.select_route(303)[0], TransportType.WIREGUARD)

        # 3. Dwell timer testing: 3 hits at t=13_000, 14_000, 15_000 -> dwell = 2000ms < 10000ms
        router.record_heartbeat(303, TransportType.LAN_BROADCAST, latency_ms=1, now_ms=13_000)
        router.record_heartbeat(303, TransportType.LAN_BROADCAST, latency_ms=1, now_ms=14_000)
        router.record_heartbeat(303, TransportType.LAN_BROADCAST, latency_ms=1, now_ms=15_000)
        self.assertEqual(router.select_route(303)[0], TransportType.WIREGUARD)

        # 4. At t=22_999 (dwell = 9999ms < 10000ms) -> Still WireGuard
        router.record_heartbeat(303, TransportType.LAN_BROADCAST, latency_ms=1, now_ms=22_999)
        self.assertEqual(router.select_route(303)[0], TransportType.WIREGUARD)

        # 5. At t=23_000 (dwell = 10000ms >= 10000ms) -> Restores LAN
        router.record_heartbeat(303, TransportType.LAN_BROADCAST, latency_ms=1, now_ms=23_000)
        self.assertEqual(router.select_route(303)[0], TransportType.LAN_BROADCAST)
        self.assertFalse(router.is_peer_partitioned(303))


if __name__ == "__main__":
    unittest.main(verbosity=2)
