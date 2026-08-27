#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial stress testing harness for Milestone 2 (T-386 Async TCP Framing and T-387 Heartbeat Eviction).
# AI-related: usr/libexec/mios/node/wire.py, usr/libexec/mios/node/discovery.py
# AI-doc: usr/share/doc/mios/manual/node.md
"""Adversarial Stress Test Suite for Milestone 2: 1. Async TCP Framing & Wire Codec (T-386)    - Byte-by-byte (1-byte chunk) stream feeding across 50 multi-opcode frames    - Irregular/randomized chunk slicing across packet boundaries    - High-concurrency async TCP client/server throughput (30 concurrent clients, 300 frames)    - Corrupted CRC32 injection across head, middle, and tail of payload    - Corrupted magic, version, opcode, and underflow rejection    - Oversized payload length header rejection (> 64MB)    - Zero-byte payload valid frame roundtrip (CRC32=0)    - Stream buffer partial frame drainage and resume    - NodeWireDispatcher error response generation for unhandled opcodes  2. Heartbeat Monitor & Dead-Peer Eviction (T-387)    - Mathematical boundary precision (0s, 4.999s, 5.0s, 9.999s, 10.0s, 14.999s, 15.0s)    - Rapid flapping and state churn across 20 peers for 100 timesteps    - Mass simultaneous eviction of 100 peers in a single sweep    - Complete listener notification dispatch on mass eviction    - Clean re-admission after eviction with strike and state reset    - Local node ID self-filtering rejection    - Monotonic time jitter / backward timestamp protection    - Custom threshold configuration lifecycle"""

from __future__ import annotations

import asyncio
import os
import random
import sys
import time
import unittest
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "node"))

import wire
import discovery

class TestAsyncFramingAdversarial(unittest.IsolatedAsyncioTestCase):
    """Adversarial stress testing for T-386 Async Tokio / Asyncio TCP Framing."""

    def test_byte_by_byte_stream_chunking_multi_frames(self):
        """Stress: Stream 50 multi-opcode, variable-length frames 1 byte at a time."""
        buf = wire.AsyncFrameBuffer()
        opcodes = [
            wire.Opcode.HEARTBEAT,
            wire.Opcode.NODE_ANNOUNCE,
            wire.Opcode.TASK_OFFLOAD,
            wire.Opcode.TASK_RESULT,
            wire.Opcode.STATE_SYNC,
            wire.Opcode.STATE_ACK,
            wire.Opcode.ERROR,
        ]

        expected_frames = []
        raw_stream = bytearray()

        rng = random.Random(42)
        for i in range(50):
            op = opcodes[i % len(opcodes)]
            node_id = 1000 + i
            payload_len = rng.randint(0, 1024)
            payload = rng.randbytes(payload_len) if hasattr(rng, "randbytes") else bytes(rng.getrandbits(8) for _ in range(payload_len))
            frame = wire.Frame.create(op, node_id, payload)
            expected_frames.append(frame)
            raw_stream.extend(frame.encode())

        # Feed byte-by-byte
        extracted_frames = []
        for b in raw_stream:
            buf.feed(bytes([b]))
            while True:
                f = buf.try_pop_frame()
                if f is None:
                    break
                extracted_frames.append(f)

        self.assertEqual(len(extracted_frames), 50)
        for i in range(50):
            self.assertEqual(extracted_frames[i].header.opcode, expected_frames[i].header.opcode)
            self.assertEqual(extracted_frames[i].header.node_id, expected_frames[i].header.node_id)
            self.assertEqual(extracted_frames[i].header.payload_len, expected_frames[i].header.payload_len)
            self.assertEqual(extracted_frames[i].header.checksum, expected_frames[i].header.checksum)
            self.assertEqual(extracted_frames[i].payload, expected_frames[i].payload)

    def test_random_irregular_chunk_slicing(self):
        """Stress: Random chunk sizes (1 to 37 bytes) slicing across frame headers and payloads."""
        buf = wire.AsyncFrameBuffer()
        rng = random.Random(1337)

        frames = [
            wire.Frame.create(wire.Opcode.TASK_OFFLOAD, 10, b"Alpha" * 20),
            wire.Frame.create(wire.Opcode.TASK_RESULT, 20, b"Beta" * 40),
            wire.Frame.create(wire.Opcode.STATE_SYNC, 30, b"Gamma" * 60),
            wire.Frame.create(wire.Opcode.HEARTBEAT, 40, b"Delta" * 10),
            wire.Frame.create(wire.Opcode.ERROR, 50, b"Epsilon" * 5),
        ]

        full_stream = b"".join(f.encode() for f in frames)
        offset = 0
        extracted = []

        while offset < len(full_stream):
            chunk_size = rng.randint(1, 37)
            chunk = full_stream[offset : offset + chunk_size]
            offset += len(chunk)
            buf.feed(chunk)
            while True:
                f = buf.try_pop_frame()
                if f is None:
                    break
                extracted.append(f)

        self.assertEqual(len(extracted), 5)
        for expected, actual in zip(frames, extracted):
            self.assertEqual(expected.header.opcode, actual.header.opcode)
            self.assertEqual(expected.header.node_id, actual.header.node_id)
            self.assertEqual(expected.payload, actual.payload)

    async def test_high_concurrency_tcp_throughput(self):
        """Stress: 30 concurrent async TCP clients blasting 10 frames each to the server."""
        received_frames_map = {}
        lock = asyncio.Lock()

        def server_handler(frame: wire.Frame, writer: asyncio.StreamWriter) -> wire.Frame:
            # Echo back with STATE_ACK
            return wire.Frame.create(
                wire.Opcode.STATE_ACK,
                node_id=frame.header.node_id,
                payload=b"ACK:" + frame.payload,
            )

        server = wire.AsyncTcpFrameServer(node_id=1, host="127.0.0.1", port=0, handler=server_handler)
        port = await server.start()

        num_clients = 30
        frames_per_client = 10

        async def client_worker(client_id: int):
            client = wire.AsyncTcpFrameClient("127.0.0.1", port)
            await client.connect()
            try:
                for seq in range(frames_per_client):
                    payload = f"node_{client_id}_seq_{seq}".encode("utf-8")
                    req = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=client_id, payload=payload)
                    await client.send_frame(req)
                    resp = await asyncio.wait_for(client.recv_frame(), timeout=5.0)
                    self.assertEqual(resp.header.opcode, wire.Opcode.STATE_ACK)
                    self.assertEqual(resp.payload, b"ACK:" + payload)
            finally:
                await client.close()

        tasks = [client_worker(i) for i in range(100, 100 + num_clients)]
        await asyncio.gather(*tasks)

        await server.stop()

    def test_crc32_tamper_fault_injection(self):
        """Fault injection: Single-byte corruptions at head, middle, and tail of payload."""
        payload = b"AUTHENTIC_PAYLOAD_FOR_CORRUPTION_TESTING_1234567890"
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, 999, payload)
        encoded = frame.encode()

        # Head corruption (byte index 16 is first payload byte)
        head_corrupt = bytearray(encoded)
        head_corrupt[16] ^= 0x01
        with self.assertRaises(ValueError) as ctx:
            wire.Frame.decode(bytes(head_corrupt))
        self.assertIn("CRC32 mismatch", str(ctx.exception))

        # Middle corruption
        mid_corrupt = bytearray(encoded)
        mid_corrupt[16 + len(payload) // 2] ^= 0x80
        with self.assertRaises(ValueError) as ctx:
            wire.Frame.decode(bytes(mid_corrupt))
        self.assertIn("CRC32 mismatch", str(ctx.exception))

        # Tail corruption
        tail_corrupt = bytearray(encoded)
        tail_corrupt[-1] ^= 0xFF
        with self.assertRaises(ValueError) as ctx:
            wire.Frame.decode(bytes(tail_corrupt))
        self.assertIn("CRC32 mismatch", str(ctx.exception))

    def test_malformed_headers_rejection(self):
        """Adversarial: Invalid magic, unsupported version, unknown opcode, buffer underflow."""
        # 1. Invalid magic
        bad_magic = bytearray(16)
        bad_magic[0] = 0x58
        bad_magic[1] = 0x58
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(bytes(bad_magic))
        self.assertIn("Invalid MiOS magic", str(ctx.exception))

        # 2. Unsupported version
        bad_version = bytearray(wire.Header(opcode=wire.Opcode.HEARTBEAT).encode())
        bad_version[2] = 0x09
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(bytes(bad_version))
        self.assertIn("Unsupported protocol version", str(ctx.exception))

        # 3. Unknown opcode
        bad_op = bytearray(wire.Header().encode())
        bad_op[3] = 0xFE
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(bytes(bad_op))
        self.assertIn("Unknown MiOS message opcode", str(ctx.exception))

        # 4. Buffer underflow
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(b"\x4D\x49\x01")
        self.assertIn("Buffer underflow", str(ctx.exception))

    def test_oversized_payload_ceiling_rejection(self):
        """Security: Header claiming > 64MB payload length is rejected before allocation."""
        bad_len_header = bytearray(wire.Header(opcode=wire.Opcode.TASK_OFFLOAD).encode())
        # Set payload_len to 65 MB (65 * 1024 * 1024)
        bad_len = 65 * 1024 * 1024
        bad_len_header[8:12] = bad_len.to_bytes(4, byteorder="big")

        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(bytes(bad_len_header))
        self.assertIn("exceeds maximum allowed ceiling", str(ctx.exception))

        buf = wire.AsyncFrameBuffer()
        buf.feed(bytes(bad_len_header))
        with self.assertRaises(ValueError) as ctx:
            buf.try_pop_frame()
        self.assertIn("exceeds maximum", str(ctx.exception))

    def test_zero_byte_payload_roundtrip(self):
        """Edge case: Empty payload frame (0 bytes, CRC32=0)."""
        frame = wire.Frame.create(wire.Opcode.STATE_ACK, 77, b"")
        self.assertEqual(frame.header.payload_len, 0)
        self.assertEqual(frame.header.checksum, 0)

        encoded = frame.encode()
        self.assertEqual(len(encoded), 16)

        decoded = wire.Frame.decode(encoded)
        self.assertEqual(decoded.header.opcode, wire.Opcode.STATE_ACK)
        self.assertEqual(decoded.header.node_id, 77)
        self.assertEqual(decoded.payload, b"")

    def test_partial_frame_drain_and_resume(self):
        """Stream integrity: Half-frame in buffer across feeds."""
        buf = wire.AsyncFrameBuffer()
        f1 = wire.Frame.create(wire.Opcode.HEARTBEAT, 1, b"FRAME_ONE")
        f2 = wire.Frame.create(wire.Opcode.HEARTBEAT, 2, b"FRAME_TWO_LONGER_PAYLOAD")

        enc1 = f1.encode()
        enc2 = f2.encode()

        # Feed complete f1 + 8 bytes of f2 header
        buf.feed(enc1 + enc2[:8])
        pop1 = buf.try_pop_frame()
        self.assertIsNotNone(pop1)
        self.assertEqual(pop1.payload, b"FRAME_ONE")

        # Second pop should return None
        self.assertIsNone(buf.try_pop_frame())

        # Feed remainder of f2
        buf.feed(enc2[8:])
        pop2 = buf.try_pop_frame()
        self.assertIsNotNone(pop2)
        self.assertEqual(pop2.payload, b"FRAME_TWO_LONGER_PAYLOAD")

    def test_dispatcher_unhandled_opcode_error_response(self):
        """Dispatcher: Handles registered opcodes and emits structured ERROR frame for unregistered."""
        dispatcher = wire.NodeWireDispatcher(node_id=500)

        def on_heartbeat(f: wire.Frame) -> wire.Frame:
            return wire.Frame.create(wire.Opcode.STATE_ACK, 500, b"PONG")

        dispatcher.register_handler(wire.Opcode.HEARTBEAT, on_heartbeat)

        # 1. Registered opcode
        req1 = wire.Frame.create(wire.Opcode.HEARTBEAT, 10, b"PING")
        resp1 = dispatcher.dispatch(req1)
        self.assertIsNotNone(resp1)
        self.assertEqual(resp1.header.opcode, wire.Opcode.STATE_ACK)
        self.assertEqual(resp1.payload, b"PONG")

        # 2. Unregistered opcode -> ERROR frame
        req2 = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, 10, b"DO_WORK")
        resp2 = dispatcher.dispatch(req2)
        self.assertIsNotNone(resp2)
        self.assertEqual(resp2.header.opcode, wire.Opcode.ERROR)
        self.assertIn(b"Unhandled opcode", resp2.payload)

class TestHeartbeatEvictionAdversarial(unittest.TestCase):
    """Adversarial stress testing for T-387 Heartbeat Monitor & Dead-Peer Eviction."""

    def setUp(self):
        self.monitor = discovery.HeartbeatMonitor(
            local_node_id=1000,
            heartbeat_interval=5.0,
            degraded_threshold=10.0,
            eviction_threshold=15.0,
        )

    def test_exact_mathematical_boundary_transitions(self):
        """Precision: Exact timing boundary conditions for strike and health status transitions."""
        # Baseline intervals: interval=5.0, degraded=10.0, eviction=15.0
        test_cases = [
            # (elapsed_secs, expected_status, expected_strikes)
            (0.0, discovery.PeerHealthStatus.HEALTHY, 0),
            (2.5, discovery.PeerHealthStatus.HEALTHY, 0),
            (4.999, discovery.PeerHealthStatus.HEALTHY, 0),
            (5.0, discovery.PeerHealthStatus.HEALTHY, 1),
            (7.5, discovery.PeerHealthStatus.HEALTHY, 1),
            (9.999, discovery.PeerHealthStatus.HEALTHY, 1),
            (10.0, discovery.PeerHealthStatus.DEGRADED, 2),
            (12.5, discovery.PeerHealthStatus.DEGRADED, 2),
            (14.999, discovery.PeerHealthStatus.DEGRADED, 2),
            (15.0, discovery.PeerHealthStatus.DEAD, 3),
            (20.0, discovery.PeerHealthStatus.DEAD, 4),
            (100.0, discovery.PeerHealthStatus.DEAD, 20),
        ]

        for elapsed, exp_status, exp_strikes in test_cases:
            status, strikes = self.monitor.assess_health(elapsed)
            self.assertEqual(
                status, exp_status, f"At {elapsed}s: expected status {exp_status}, got {status}"
            )
            self.assertEqual(
                strikes, exp_strikes, f"At {elapsed}s: expected strikes {exp_strikes}, got {strikes}"
            )

    def test_rapid_peer_flapping_and_state_churn(self):
        """Stress: 20 peers undergoing 100 timesteps of random flapping, eviction, and re-admission."""
        num_peers = 20
        timesteps = 100
        rng = random.Random(999)

        # Initial registration at T=0
        current_time = 0.0
        for i in range(num_peers):
            self.monitor.record_heartbeat(
                node_id=i + 1,
                addr=f"192.168.1.{i+1}",
                port=8000 + i,
                now=current_time,
            )

        self.assertEqual(self.monitor.peer_count, num_peers)

        for step in range(1, timesteps + 1):
            current_time += 2.0  # Advance 2s per step

            # Random subset of peers send heartbeat
            for i in range(num_peers):
                nid = i + 1
                if rng.random() > 0.4:  # 60% chance to send heartbeat
                    self.monitor.record_heartbeat(
                        node_id=nid,
                        addr=f"192.168.1.{nid}",
                        port=8000 + i,
                        uptime_secs=current_time,
                        cpu_load_pct=rng.randint(5, 95),
                        mem_available_kb=1024000,
                        now=current_time,
                    )

            healthy, degraded, evicted = self.monitor.sweep(now=current_time)

            # Invariant checks
            for h in healthy:
                p = self.monitor.get_peer(h)
                self.assertIsNotNone(p)
                self.assertEqual(p.status, discovery.PeerHealthStatus.HEALTHY)
            for d in degraded:
                p = self.monitor.get_peer(d)
                self.assertIsNotNone(p)
                self.assertEqual(p.status, discovery.PeerHealthStatus.DEGRADED)
            for ev in evicted:
                # Evicted peers must be removed immediately
                self.assertIsNone(self.monitor.get_peer(ev.node_id))
                self.assertFalse(self.monitor.is_peer_active(ev.node_id))

    def test_mass_simultaneous_eviction_and_listeners(self):
        """Stress: 100 simultaneous peers expiring at once and firing event listeners."""
        events_collected = []

        def on_evict(evt: discovery.EvictionEvent):
            events_collected.append(evt)

        self.monitor.add_eviction_listener(on_evict)

        t_init = 1000.0
        for i in range(100):
            self.monitor.record_heartbeat(
                node_id=2000 + i,
                addr=f"10.10.1.{i}",
                port=9000,
                now=t_init,
            )

        self.assertEqual(self.monitor.peer_count, 100)

        # Sweep at T=1016 (16s elapsed for all 100 peers)
        healthy, degraded, evicted = self.monitor.sweep(now=t_init + 16.0)

        self.assertEqual(len(healthy), 0)
        self.assertEqual(len(degraded), 0)
        self.assertEqual(len(evicted), 100)
        self.assertEqual(len(events_collected), 100)
        self.assertEqual(self.monitor.peer_count, 0)

        # Verify all event details
        for evt in events_collected:
            self.assertGreaterEqual(evt.elapsed_secs, 15.0)
            self.assertGreaterEqual(evt.missed_strikes, 3)
            self.assertIn("3-strike timeout", evt.reason)

    def test_self_node_filtering(self):
        """Edge case: Monitor rejects recording heartbeats/announcements from local_node_id."""
        res_hb = self.monitor.record_heartbeat(
            node_id=1000,  # Same as local_node_id
            addr="127.0.0.1",
            port=8650,
            now=100.0,
        )
        self.assertIsNone(res_hb)
        self.assertEqual(self.monitor.peer_count, 0)

        res_ann = self.monitor.record_announce(
            node_id=1000,  # Same as local_node_id
            addr="127.0.0.1",
            port=8650,
            now=100.0,
        )
        self.assertIsNone(res_ann)
        self.assertEqual(self.monitor.peer_count, 0)

    def test_backward_timestamp_monotonic_protection(self):
        """Robustness: Clock jitter or backwards time jump does not crash or underflow."""
        self.monitor.record_heartbeat(500, "10.0.0.1", 8000, now=100.0)

        # Sweep with backwards timestamp (e.g. clock correction to 90.0)
        healthy, degraded, evicted = self.monitor.sweep(now=90.0)
        self.assertEqual(healthy, [500])
        peer = self.monitor.get_peer(500)
        self.assertEqual(peer.status, discovery.PeerHealthStatus.HEALTHY)
        self.assertEqual(peer.missed_strikes, 0)

    def test_custom_fast_thresholds(self):
        """Configurability: Fast 1s interval, 2s degraded, 3s eviction thresholds."""
        fast_monitor = discovery.HeartbeatMonitor(
            local_node_id=1,
            heartbeat_interval=1.0,
            degraded_threshold=2.0,
            eviction_threshold=3.0,
        )

        fast_monitor.record_heartbeat(2, "127.0.0.1", 8000, now=10.0)

        # T=11.5 (1.5s elapsed -> 1 strike -> Healthy)
        h, d, e = fast_monitor.sweep(now=11.5)
        self.assertEqual(h, [2])

        # T=12.2 (2.2s elapsed -> 2 strikes -> Degraded)
        h, d, e = fast_monitor.sweep(now=12.2)
        self.assertEqual(d, [2])

        # T=13.1 (3.1s elapsed -> 3 strikes -> Evicted)
        h, d, e = fast_monitor.sweep(now=13.1)
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0].node_id, 2)
        self.assertEqual(fast_monitor.peer_count, 0)

def main() -> int:
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAsyncFramingAdversarial))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHeartbeatEvictionAdversarial))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
