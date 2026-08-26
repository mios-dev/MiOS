#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE 16-byte fixed binary wire protocol framing & dispatch.
# AI-doc: usr/share/doc/mios/manual/ch55-edge-mesh-binary-wire-protocol.md
"""Unit test suite for WS-NODE binary framing, CRC32 verification, and opcode dispatch."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios"))

import importlib.util

_WIRE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "mios-node-wire.py")
spec = importlib.util.spec_from_file_location("mios_node_wire", _WIRE_PATH)
if spec and spec.loader:
    wire = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = wire
    spec.loader.exec_module(wire)
else:
    raise ImportError(f"Could not load mios-node-wire module from {_WIRE_PATH}")


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


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeWireProtocol)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
