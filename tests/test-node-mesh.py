#!/usr/bin/env python3
# AI-hint: Consolidated unit and integration test suite for WS-NODE edge mesh networking: async TCP framing, Ed25519/X25519/ChaCha20-Poly1305 crypto handshake, heartbeat eviction, and binary wire protocol.
# AI-related: usr/libexec/mios/node/wire.py, usr/libexec/mios/node/crypto.py, usr/libexec/mios/node/discovery.py, usr/libexec/mios/node/mios-node-wire.py
# AI-doc: usr/share/doc/mios/manual/node.md
"""Consolidated Node Mesh Domain Test Suite (WS-NODE Edge Micro-Mesh).

Combines and preserves 100% test coverage across 4 core networking subsystems:
1. Async TCP framing, stream buffer reassembly, CRC32 checks, and channel dispatch (TestAsyncNetFraming)
2. Mutual Ed25519 identity authentication, X25519 ECDH key exchange, HKDF-SHA256 session derivation, ChaCha20-Poly1305 AEAD wire encryption, and tamper/imposter rejection (TestNodeCryptoHandshake)
3. Heartbeat monitor, 5s intervals, 3-strike dead peer detection (15s eviction), degraded transitions, routing table pruning, and eviction event listeners (TestNodeHeartbeatEviction)
4. 16-byte fixed binary wire protocol framing, big-endian header packing/unpacking, CRC32 verification, opcode dispatch, and payload limits (TestNodeWireProtocol)
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_NODE_DIR = os.path.join(_ROOT, "usr", "libexec", "mios", "node")
if _NODE_DIR not in sys.path:
    sys.path.insert(0, _NODE_DIR)

import crypto
import discovery
import wire


# ============================================================================
# Domain 2.1: Async TCP Framing & Stream Buffering
# (Migrated from tests/test-node-async-net.py)
# ============================================================================

class TestAsyncNetFraming(unittest.IsolatedAsyncioTestCase):
    """Asynchronous test cases for Tokio/asyncio TCP frame reader, writer, and buffer."""

    async def test_async_codec_single_frame_roundtrip(self):
        server = wire.AsyncTcpFrameServer(node_id=101, host="127.0.0.1", port=0)
        port = await server.start()

        client = wire.AsyncTcpFrameClient("127.0.0.1", port)
        await client.connect()

        payload = b'{"status":"online","cpu":12}'
        frame = wire.Frame.create(wire.Opcode.HEARTBEAT, node_id=202, payload=payload)

        await client.send_frame(frame)

        received_frame, peer = await asyncio.wait_for(server.incoming_queue.get(), timeout=2.0)
        self.assertEqual(received_frame.header.opcode, wire.Opcode.HEARTBEAT)
        self.assertEqual(received_frame.header.node_id, 202)
        self.assertEqual(received_frame.payload, payload)

        await client.close()
        await server.stop()

    async def test_async_codec_multiple_consecutive_frames(self):
        server = wire.AsyncTcpFrameServer(node_id=101, host="127.0.0.1", port=0)
        port = await server.start()

        client = wire.AsyncTcpFrameClient("127.0.0.1", port)
        await client.connect()

        frames_to_send = [
            wire.Frame.create(wire.Opcode.HEARTBEAT, node_id=1, payload=b"ping"),
            wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=1, payload=b"task_payload_12345"),
            wire.Frame.create(wire.Opcode.STATE_SYNC, node_id=1, payload=b'{"crdt_sync":true}'),
            wire.Frame.create(wire.Opcode.STATE_ACK, node_id=1, payload=b"ack"),
        ]

        for f in frames_to_send:
            await client.send_frame(f)

        for expected in frames_to_send:
            received, _ = await asyncio.wait_for(server.incoming_queue.get(), timeout=2.0)
            self.assertEqual(received.header.opcode, expected.header.opcode)
            self.assertEqual(received.header.node_id, expected.header.node_id)
            self.assertEqual(received.payload, expected.payload)

        await client.close()
        await server.stop()

    def test_stream_buffer_incremental_chunking(self):
        buf = wire.AsyncFrameBuffer()

        f1 = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, 50, b"FRAGMENTED_PAYLOAD_A")
        f2 = wire.Frame.create(wire.Opcode.TASK_RESULT, 50, b"FRAGMENTED_PAYLOAD_B")

        raw_bytes = f1.encode() + f2.encode()

        # Feed in irregular chunks: 1 byte, 7 bytes, 3 bytes, etc.
        chunk_sizes = [1, 7, 3, 2, 8, 4, 15, 1, 1, 5, 20, 10]
        offset = 0
        extracted_frames = []

        for size in chunk_sizes:
            if offset >= len(raw_bytes):
                break
            chunk = raw_bytes[offset : offset + size]
            offset += len(chunk)
            buf.feed(chunk)
            while True:
                popped = buf.try_pop_frame()
                if popped is None:
                    break
                extracted_frames.append(popped)

        # Feed any remaining bytes
        if offset < len(raw_bytes):
            buf.feed(raw_bytes[offset:])
            while True:
                popped = buf.try_pop_frame()
                if popped is None:
                    break
                extracted_frames.append(popped)

        self.assertEqual(len(extracted_frames), 2)
        self.assertEqual(extracted_frames[0].header.opcode, wire.Opcode.TASK_OFFLOAD)
        self.assertEqual(extracted_frames[0].payload, b"FRAGMENTED_PAYLOAD_A")
        self.assertEqual(extracted_frames[1].header.opcode, wire.Opcode.TASK_RESULT)
        self.assertEqual(extracted_frames[1].payload, b"FRAGMENTED_PAYLOAD_B")

    def test_stream_buffer_crc_mismatch(self):
        buf = wire.AsyncFrameBuffer()
        frame = wire.Frame.create(wire.Opcode.HEARTBEAT, 10, b"DATA")
        raw = bytearray(frame.encode())
        raw[-1] ^= 0xFF  # Corrupt payload byte

        buf.feed(bytes(raw))
        with self.assertRaises(ValueError) as ctx:
            buf.try_pop_frame()
        self.assertIn("CRC32 mismatch", str(ctx.exception))

    def test_stream_buffer_invalid_magic(self):
        buf = wire.AsyncFrameBuffer()
        corrupted_header = bytearray(16)
        corrupted_header[0] = 0xDE
        corrupted_header[1] = 0xAD

        buf.feed(bytes(corrupted_header))
        with self.assertRaises(ValueError) as ctx:
            buf.try_pop_frame()
        self.assertIn("Invalid MiOS magic", str(ctx.exception))

    async def test_async_server_multiple_concurrent_clients(self):
        def echo_handler(frame: wire.Frame, writer: asyncio.StreamWriter) -> wire.Frame:
            resp_payload = b"ECHO:" + frame.payload
            return wire.Frame.create(wire.Opcode.STATE_ACK, node_id=frame.header.node_id, payload=resp_payload)

        server = wire.AsyncTcpFrameServer(node_id=1, host="127.0.0.1", port=0, handler=echo_handler)
        port = await server.start()

        async def run_client_task(client_id: int):
            client = wire.AsyncTcpFrameClient("127.0.0.1", port)
            await client.connect()
            msg = f"client_{client_id}_msg".encode("utf-8")
            req = wire.Frame.create(wire.Opcode.HEARTBEAT, node_id=client_id, payload=msg)
            await client.send_frame(req)
            resp = await asyncio.wait_for(client.recv_frame(), timeout=2.0)
            self.assertEqual(resp.header.opcode, wire.Opcode.STATE_ACK)
            self.assertEqual(resp.payload, b"ECHO:" + msg)
            await client.close()

        # Run 5 concurrent clients
        tasks = [run_client_task(i) for i in range(10, 15)]
        await asyncio.gather(*tasks)

        await server.stop()

    async def test_large_payload_handling(self):
        server = wire.AsyncTcpFrameServer(node_id=1, host="127.0.0.1", port=0)
        port = await server.start()

        client = wire.AsyncTcpFrameClient("127.0.0.1", port)
        await client.connect()

        # 256 KB binary payload
        large_payload = os.urandom(256 * 1024)
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=888, payload=large_payload)

        await client.send_frame(frame)
        received, _ = await asyncio.wait_for(server.incoming_queue.get(), timeout=3.0)

        self.assertEqual(received.header.opcode, wire.Opcode.TASK_OFFLOAD)
        self.assertEqual(received.header.node_id, 888)
        self.assertEqual(len(received.payload), 256 * 1024)
        self.assertEqual(received.payload, large_payload)

        await client.close()
        await server.stop()


# ============================================================================
# Domain 2.2: Mutual Ed25519 Authentication, X25519 ECDH, and ChaCha20-Poly1305 AEAD
# (Migrated from tests/test-node-crypto-handshake.py)
# ============================================================================

class TestNodeCryptoHandshake(unittest.TestCase):
    """Validates mutual Ed25519 authentication, X25519 ECDH, HKDF derivation, and AEAD frame encryption."""

    def test_ed25519_identity_keypair_and_signatures(self):
        id_1 = crypto.NodeIdentity.generate(node_id=101)
        self.assertEqual(id_1.node_id, 101)
        self.assertEqual(len(id_1.public_bytes), 32)
        self.assertEqual(len(id_1.private_bytes), 32)

        msg = b"Authentication challenge test payload"
        sig = id_1.sign(msg)
        self.assertEqual(len(sig), 64)

        # Valid signature verification
        self.assertTrue(crypto.NodeIdentity.verify(id_1.public_bytes, msg, sig))

    def test_ed25519_signature_tamper_rejection(self):
        id_1 = crypto.NodeIdentity.generate(node_id=101)
        msg = b"Authentic payload"
        sig = bytearray(id_1.sign(msg))

        # Corrupt 1 byte in signature
        sig[0] ^= 0xFF
        self.assertFalse(crypto.NodeIdentity.verify(id_1.public_bytes, msg, bytes(sig)))

        # Corrupt message
        self.assertFalse(crypto.NodeIdentity.verify(id_1.public_bytes, b"Forged payload", id_1.sign(msg)))

    def test_mutual_handshake_session_establishment(self):
        node_a = crypto.NodeIdentity.generate(node_id=10)
        node_b = crypto.NodeIdentity.generate(node_id=20)

        # 1. Node A creates HandshakeInit
        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        self.assertEqual(init_pkt.sender_node_id, 10)
        self.assertEqual(len(init_pkt.id_pubkey), 32)
        self.assertEqual(len(init_pkt.ephemeral_pubkey), 32)
        self.assertEqual(len(init_pkt.signature), 64)

        # 2. Node B processes HandshakeInit, derives session keys, and responds with HandshakeResp
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        self.assertEqual(resp_pkt.sender_node_id, 20)
        self.assertEqual(session_b.local_node_id, 20)
        self.assertEqual(session_b.remote_node_id, 10)

        # 3. Node A finalizes handshake using HandshakeResp
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)
        self.assertEqual(session_a.local_node_id, 10)
        self.assertEqual(session_a.remote_node_id, 20)

        # Verify key derivation symmetry: A's TX key == B's RX key, A's RX key == B's TX key
        self.assertEqual(session_a.tx_key, session_b.rx_key)
        self.assertEqual(session_a.rx_key, session_b.tx_key)

    def test_bidirectional_payload_encryption_and_decryption(self):
        node_a = crypto.NodeIdentity.generate(node_id=1)
        node_b = crypto.NodeIdentity.generate(node_id=2)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        # Message A -> B
        plain_a = b"Secure payload from node A to node B"
        enc_a = session_a.encrypt_payload(plain_a)
        self.assertNotEqual(enc_a, plain_a)
        self.assertEqual(len(enc_a), len(plain_a) + 16)  # 16-byte Poly1305 auth tag

        dec_b = session_b.decrypt_payload(enc_a)
        self.assertEqual(dec_b, plain_a)

        # Message B -> A
        plain_b = b"Secure acknowledgement from node B to node A"
        enc_b = session_b.encrypt_payload(plain_b)
        dec_a = session_a.decrypt_payload(enc_b)
        self.assertEqual(dec_a, plain_b)

    def test_payload_tamper_detection_mac_failure(self):
        node_a = crypto.NodeIdentity.generate(node_id=1)
        node_b = crypto.NodeIdentity.generate(node_id=2)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        plain = b"Critical financial or cryptographic state data"
        ciphertext = bytearray(session_a.encrypt_payload(plain))

        # Tamper with 1 byte in ciphertext body
        ciphertext[5] ^= 0x01

        with self.assertRaises(ValueError) as ctx:
            session_b.decrypt_payload(bytes(ciphertext))
        self.assertIn("MAC verification failed", str(ctx.exception))

        # Tamper with 1 byte in authentication tag (last 16 bytes)
        ciphertext = bytearray(session_a.encrypt_payload(plain))
        ciphertext[-1] ^= 0x01
        with self.assertRaises(ValueError) as ctx:
            session_b.decrypt_payload(bytes(ciphertext))
        self.assertIn("MAC verification failed", str(ctx.exception))

    def test_imposter_handshake_rejection(self):
        node_a = crypto.NodeIdentity.generate(node_id=10)
        node_b = crypto.NodeIdentity.generate(node_id=20)
        imposter = crypto.NodeIdentity.generate(node_id=99)

        init_pkt, _ = crypto.CryptoHandshake.create_init(node_a)

        # Imposter attempts to sign Node A's ephemeral pubkey with imposter's identity
        forged_sig = imposter.sign(init_pkt.ephemeral_pubkey)
        forged_init = crypto.HandshakeInitPacket(
            sender_node_id=10,
            id_pubkey=node_a.public_bytes,  # Claims to be Node A
            ephemeral_pubkey=init_pkt.ephemeral_pubkey,
            signature=forged_sig,  # Forged signature
        )

        with self.assertRaises(ValueError) as ctx:
            crypto.CryptoHandshake.process_init_and_respond(node_b, forged_init)
        self.assertIn("signature verification failed", str(ctx.exception))

    def test_wire_frame_encryption_roundtrip(self):
        node_a = crypto.NodeIdentity.generate(node_id=100)
        node_b = crypto.NodeIdentity.generate(node_id=200)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        # Original frame
        original_payload = b'{"task_id":9001,"compute":"matrix_multiply"}'
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=100, payload=original_payload)

        # Encrypt frame
        enc_frame = session_a.encrypt_frame(frame)
        self.assertEqual(enc_frame.header.opcode, wire.Opcode.TASK_OFFLOAD)
        self.assertEqual(enc_frame.header.node_id, 100)
        self.assertEqual(len(enc_frame.payload), len(original_payload) + 16)
        self.assertNotEqual(enc_frame.payload, original_payload)

        # Encode and decode over wire
        raw_wire_bytes = enc_frame.encode()
        wire_decoded_frame = wire.Frame.decode(raw_wire_bytes)
        self.assertEqual(wire_decoded_frame.header.payload_len, len(enc_frame.payload))

        # Decrypt frame on receiving node
        dec_frame = session_b.decrypt_frame(wire_decoded_frame)
        self.assertEqual(dec_frame.header.opcode, wire.Opcode.TASK_OFFLOAD)
        self.assertEqual(dec_frame.header.node_id, 100)
        self.assertEqual(dec_frame.payload, original_payload)

    def test_nonce_increment_progression(self):
        node_a = crypto.NodeIdentity.generate(node_id=1)
        node_b = crypto.NodeIdentity.generate(node_id=2)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        self.assertEqual(session_a.tx_nonce, 0)
        self.assertEqual(session_b.rx_nonce, 0)

        # Encrypt 3 consecutive packets
        ct1 = session_a.encrypt_payload(b"packet 1")
        self.assertEqual(session_a.tx_nonce, 1)

        ct2 = session_a.encrypt_payload(b"packet 2")
        self.assertEqual(session_a.tx_nonce, 2)

        ct3 = session_a.encrypt_payload(b"packet 3")
        self.assertEqual(session_a.tx_nonce, 3)

        # Decrypt in order
        p1 = session_b.decrypt_payload(ct1)
        self.assertEqual(session_b.rx_nonce, 1)
        self.assertEqual(p1, b"packet 1")

        p2 = session_b.decrypt_payload(ct2)
        self.assertEqual(session_b.rx_nonce, 2)
        self.assertEqual(p2, b"packet 2")

        p3 = session_b.decrypt_payload(ct3)
        self.assertEqual(session_b.rx_nonce, 3)
        self.assertEqual(p3, b"packet 3")


# ============================================================================
# Domain 2.3: Heartbeat Quorum & Dead Peer Eviction
# (Migrated from tests/test-node-heartbeat-eviction.py)
# ============================================================================

class TestNodeHeartbeatEviction(unittest.TestCase):
    """Validates 5s heartbeat interval, 3-strike dead peer eviction, and routing table lifecycle."""

    def setUp(self):
        self.monitor = discovery.HeartbeatMonitor(
            local_node_id=100,
            heartbeat_interval=5.0,
            degraded_threshold=10.0,
            eviction_threshold=15.0,
        )

    def test_record_heartbeat_and_initial_health(self):
        peer = self.monitor.record_heartbeat(
            node_id=201,
            addr="10.0.0.21",
            port=8650,
            uptime_secs=3600,
            cpu_load_pct=15,
            mem_available_kb=2048000,
            now=1000.0,
        )
        self.assertIsNotNone(peer)
        self.assertEqual(peer.node_id, 201)
        self.assertEqual(peer.status, discovery.PeerHealthStatus.HEALTHY)
        self.assertEqual(peer.missed_strikes, 0)
        self.assertEqual(self.monitor.peer_count, 1)
        self.assertTrue(self.monitor.is_peer_active(201))

    def test_degraded_status_transition_at_two_strikes(self):
        # Peer registered at T=1000
        self.monitor.record_heartbeat(201, "10.0.0.21", 8650, now=1000.0)

        # Sweep at T=1006 (6s elapsed -> 1 strike -> still Healthy)
        healthy, degraded, evicted = self.monitor.sweep(now=1006.0)
        self.assertIn(201, healthy)
        self.assertEqual(len(degraded), 0)
        self.assertEqual(len(evicted), 0)

        # Sweep at T=1011 (11s elapsed -> 2 strikes -> Degraded)
        healthy, degraded, evicted = self.monitor.sweep(now=1011.0)
        self.assertEqual(len(healthy), 0)
        self.assertIn(201, degraded)
        self.assertEqual(len(evicted), 0)
        peer = self.monitor.get_peer(201)
        self.assertEqual(peer.status, discovery.PeerHealthStatus.DEGRADED)
        self.assertEqual(peer.missed_strikes, 2)

    def test_3_strike_dead_peer_eviction_at_15s(self):
        self.monitor.record_heartbeat(202, "10.0.0.22", 8650, now=1000.0)

        # Sweep at T=1016 (16s elapsed -> 3 strikes >= 15s -> Evicted)
        healthy, degraded, evicted = self.monitor.sweep(now=1016.0)
        self.assertEqual(len(healthy), 0)
        self.assertEqual(len(degraded), 0)
        self.assertEqual(len(evicted), 1)

        event = evicted[0]
        self.assertEqual(event.node_id, 202)
        self.assertIn("3-strike timeout", event.reason)
        self.assertEqual(event.missed_strikes, 3)
        self.assertGreaterEqual(event.elapsed_secs, 15.0)

        # Routing table pruned
        self.assertEqual(self.monitor.peer_count, 0)
        self.assertFalse(self.monitor.is_peer_active(202))
        self.assertIsNone(self.monitor.get_peer(202))

    def test_eviction_event_listener_dispatch(self):
        dispatched_events = []

        def on_evict(event: discovery.EvictionEvent):
            dispatched_events.append(event)

        self.monitor.add_eviction_listener(on_evict)
        self.monitor.record_heartbeat(303, "10.0.0.33", 8650, now=500.0)

        # Trigger eviction at T=520 (20s elapsed)
        self.monitor.sweep(now=520.0)

        self.assertEqual(len(dispatched_events), 1)
        self.assertEqual(dispatched_events[0].node_id, 303)
        self.assertEqual(dispatched_events[0].missed_strikes, 4)

    def test_peer_readmission_after_eviction(self):
        # Register and evict peer
        self.monitor.record_heartbeat(404, "10.0.0.44", 8650, now=100.0)
        self.monitor.sweep(now=120.0)
        self.assertEqual(self.monitor.peer_count, 0)

        # Peer comes back online at T=150 with fresh Heartbeat
        re_admitted = self.monitor.record_heartbeat(
            404, "10.0.0.44", 8650, uptime_secs=10, cpu_load_pct=5, now=150.0
        )
        self.assertIsNotNone(re_admitted)
        self.assertEqual(self.monitor.peer_count, 1)
        self.assertEqual(re_admitted.status, discovery.PeerHealthStatus.HEALTHY)
        self.assertEqual(re_admitted.missed_strikes, 0)
        self.assertEqual(re_admitted.uptime_secs, 10)

    def test_manual_peer_eviction(self):
        self.monitor.record_heartbeat(505, "10.0.0.55", 8650, now=200.0)
        self.assertEqual(self.monitor.peer_count, 1)

        event = self.monitor.evict_peer(505, reason="operator_drain_node", now=205.0)
        self.assertIsNotNone(event)
        self.assertEqual(event.node_id, 505)
        self.assertEqual(event.reason, "operator_drain_node")
        self.assertEqual(self.monitor.peer_count, 0)

    def test_multi_peer_sweep_mixed_states(self):
        now = 1000.0
        # Peer A: fresh (last seen at 998 -> 2s elapsed)
        self.monitor.record_heartbeat(10, "10.0.0.10", 8650, now=998.0)
        # Peer B: degraded (last seen at 988 -> 12s elapsed)
        self.monitor.record_heartbeat(20, "10.0.0.20", 8650, now=988.0)
        # Peer C: dead (last seen at 980 -> 20s elapsed)
        self.monitor.record_heartbeat(30, "10.0.0.30", 8650, now=980.0)

        healthy, degraded, evicted = self.monitor.sweep(now=now)
        self.assertEqual(healthy, [10])
        self.assertEqual(degraded, [20])
        self.assertEqual(len(evicted), 1)
        self.assertEqual(evicted[0].node_id, 30)

        # Final active count should be 2 (Node 10 and Node 20)
        self.assertEqual(self.monitor.peer_count, 2)
        active_ids = [p.node_id for p in self.monitor.get_active_peers()]
        self.assertIn(10, active_ids)
        self.assertIn(20, active_ids)


# ============================================================================
# Domain 2.4: Fixed 16-Byte Binary Wire Framing & Dispatch
# (Migrated from tests/test-node-wire.py)
# ============================================================================

class TestNodeWireProtocol(unittest.TestCase):
    """Validates 16-byte binary wire framing, checksum validation, and dispatch."""

    def test_header_pack_unpack(self):
        hdr = wire.Header(
            magic=wire.MIOS_MAGIC,
            version=wire.MIOS_VERSION,
            opcode=wire.Opcode.HEARTBEAT,
            node_id=101,
            payload_len=48,
            checksum=0x12345678,
        )
        encoded = hdr.encode()
        self.assertEqual(len(encoded), 16)
        decoded = wire.Header.decode(encoded)
        self.assertEqual(hdr, decoded)
        self.assertEqual(decoded.magic, 0x4D49)
        self.assertEqual(decoded.version, 0x01)
        self.assertEqual(decoded.opcode, wire.Opcode.HEARTBEAT)
        self.assertEqual(decoded.msg_type, wire.Opcode.HEARTBEAT)

    def test_frame_roundtrip_all_opcodes(self):
        for op in wire.Opcode:
            payload = f'{{"msg":"test payload for opcode {op.name}"}}'.encode("utf-8")
            frame = wire.Frame.create(op, node_id=42, payload=payload)
            encoded = frame.encode()
            self.assertEqual(len(encoded), 16 + len(payload))

            decoded = wire.Frame.decode(encoded)
            self.assertEqual(decoded.header.magic, 0x4D49)
            self.assertEqual(decoded.header.version, 0x01)
            self.assertEqual(decoded.header.opcode, op)
            self.assertEqual(decoded.header.node_id, 42)
            self.assertEqual(decoded.payload, payload)

    def test_crc32_corruption_detection(self):
        payload = b"CRITICAL_TASK_OFFLOAD_PAYLOAD"
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=99, payload=payload)
        encoded = bytearray(frame.encode())

        # Corrupt one bit in payload
        encoded[-1] ^= 0x01

        with self.assertRaises(ValueError) as ctx:
            wire.Frame.decode(bytes(encoded))
        self.assertIn("CRC32 mismatch", str(ctx.exception))

    def test_invalid_magic_and_version(self):
        # Invalid magic
        bad_magic_header = bytearray(16)
        wire.HEADER_STRUCT.pack_into(bad_magic_header, 0, 0x9999, 0x01, 0x01, 1, 0, 0)
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(bad_magic_header)
        self.assertIn("Invalid MiOS magic", str(ctx.exception))

        # Unsupported version
        bad_version_header = bytearray(16)
        wire.HEADER_STRUCT.pack_into(bad_version_header, 0, 0x4D49, 0x02, 0x01, 1, 0, 0)
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(bad_version_header)
        self.assertIn("Unsupported protocol version", str(ctx.exception))

    def test_truncated_frame(self):
        payload = b"LONG_PAYLOAD_STRING"
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=1, payload=payload)
        encoded = frame.encode()
        truncated = encoded[:-5]

        with self.assertRaises(ValueError) as ctx:
            wire.Frame.decode(truncated)
        self.assertIn("Incomplete payload", str(ctx.exception))

    def test_payload_ceiling_protection(self):
        # Header claiming >64MB payload
        oversized_header = bytearray(16)
        wire.HEADER_STRUCT.pack_into(oversized_header, 0, 0x4D49, 0x01, 0x01, 1, 70 * 1024 * 1024, 0)
        with self.assertRaises(ValueError) as ctx:
            wire.Header.decode(oversized_header)
        self.assertIn("exceeds maximum allowed ceiling", str(ctx.exception))

    def test_opcode_dispatcher(self):
        dispatcher = wire.NodeWireDispatcher(node_id=10)

        def handle_heartbeat(frame: wire.Frame) -> wire.Frame:
            ack_payload = b'{"status":"ack"}'
            return wire.Frame.create(wire.Opcode.STATE_ACK, node_id=dispatcher.node_id, payload=ack_payload)

        dispatcher.register_handler(wire.Opcode.HEARTBEAT, handle_heartbeat)

        hb_frame = wire.Frame.create(wire.Opcode.HEARTBEAT, node_id=20, payload=b'{"ping":true}')
        response_bytes = dispatcher.process_packet(hb_frame.encode())
        self.assertIsNotNone(response_bytes)

        resp_frame = wire.Frame.decode(response_bytes)
        self.assertEqual(resp_frame.header.opcode, wire.Opcode.STATE_ACK)
        self.assertEqual(resp_frame.header.node_id, 10)
        self.assertEqual(resp_frame.payload, b'{"status":"ack"}')

    def test_wire_frame_alias(self):
        wf = wire.WireFrame(wire.Opcode.TASK_RESULT, 77, b"result_data")
        encoded = wf.encode()
        decoded = wire.Frame.decode(encoded)
        self.assertEqual(decoded.header.opcode, wire.Opcode.TASK_RESULT)
        self.assertEqual(decoded.header.node_id, 77)
        self.assertEqual(decoded.payload, b"result_data")


if __name__ == "__main__":
    unittest.main()
