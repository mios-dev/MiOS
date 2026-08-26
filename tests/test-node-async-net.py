#!/usr/bin/env python3
# AI-hint: Automated unit and integration test suite for T-386 / AGY-1984 async TCP framing and stream buffering.
# AI-doc: usr/share/doc/mios/manual/node.md
"""
Unit and integration test suite for WS-NODE: Async TCP frame reader, writer actor,
stream buffer management, partial packet chunking, and channel dispatch.
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "node"))

import wire


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


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAsyncNetFraming)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
