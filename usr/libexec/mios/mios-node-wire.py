#!/usr/bin/env python3
# AI-hint: 16-byte fixed binary wire protocol encoder, decoder, and opcode dispatcher for mios-node.
# AI-related: usr/share/doc/mios/adr/0020-edge-mesh-binary-wire-protocol-and-dual-tier-sandboxing.md, src/mios-rs/mios-node/src/protocol.rs
# AI-doc: usr/share/doc/mios/manual/ch55-edge-mesh-binary-wire-protocol.md
"""
WS-NODE: Edge Micro-Mesh 16-Byte Fixed Binary Wire Protocol Engine.
Provides byte-for-byte wire compatibility with the Rust mios-node runtime.

Header Format (16 Bytes Fixed, Big-Endian Network Byte Order):
+-------------------------------------------------------------------+
| Magic (2B: 0x4D 0x49) | Ver (1B) | Opcode (1B) | NodeID (4B: u32) |
+-------------------------------------------------------------------+
| PayloadLen (4B: u32)             | Checksum (4B: u32 CRC32)       |
+-------------------------------------------------------------------+
"""

from __future__ import annotations

import enum
import struct
import sys
import zlib
from typing import Callable, Dict, Optional, Union

MIOS_MAGIC = 0x4D49  # 'MI'
MIOS_VERSION = 0x01
HEADER_SIZE = 16
MAX_PAYLOAD_LEN = 64 * 1024 * 1024  # 64 MB ceiling
HEADER_STRUCT = struct.Struct(">HBBIII")  # Big-Endian: u16, u8, u8, u32, u32, u32


class Opcode(enum.IntEnum):
    HEARTBEAT = 0x01
    NODE_ANNOUNCE = 0x02
    TASK_OFFLOAD = 0x03
    TASK_RESULT = 0x04
    STATE_SYNC = 0x05
    STATE_ACK = 0x06
    ERROR = 0x07


# Alias for Rust MessageType parity
MessageType = Opcode


class Header:
    __slots__ = ("magic", "version", "opcode", "node_id", "payload_len", "checksum")

    def __init__(
        self,
        magic: int = MIOS_MAGIC,
        version: int = MIOS_VERSION,
        opcode: Union[Opcode, int] = Opcode.HEARTBEAT,
        node_id: int = 0,
        payload_len: int = 0,
        checksum: int = 0,
    ):
        self.magic = magic
        self.version = version
        self.opcode = Opcode(opcode)
        self.node_id = node_id
        self.payload_len = payload_len
        self.checksum = checksum

    @property
    def msg_type(self) -> Opcode:
        return self.opcode

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Header):
            return False
        return (
            self.magic == other.magic
            and self.version == other.version
            and self.opcode == other.opcode
            and self.node_id == other.node_id
            and self.payload_len == other.payload_len
            and self.checksum == other.checksum
        )

    def __repr__(self) -> str:
        return (
            f"Header(magic=0x{self.magic:04X}, version={self.version}, opcode={self.opcode.name}, "
            f"node_id={self.node_id}, payload_len={self.payload_len}, checksum=0x{self.checksum:08X})"
        )

    def encode(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.version,
            int(self.opcode),
            self.node_id,
            self.payload_len,
            self.checksum,
        )

    @classmethod
    def decode(cls, data: bytes) -> Header:
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Buffer underflow: expected {HEADER_SIZE} bytes, got {len(data)}")
        magic, version, opcode_val, node_id, payload_len, checksum = HEADER_STRUCT.unpack_from(data, 0)
        if magic != MIOS_MAGIC:
            raise ValueError(f"Invalid MiOS magic: 0x{magic:04X} (expected 0x{MIOS_MAGIC:04X})")
        if version != MIOS_VERSION:
            raise ValueError(f"Unsupported protocol version: {version} (expected {MIOS_VERSION})")
        try:
            opcode = Opcode(opcode_val)
        except ValueError:
            raise ValueError(f"Unknown MiOS message opcode: 0x{opcode_val:02X}")
        if payload_len > MAX_PAYLOAD_LEN:
            raise ValueError(f"Payload length exceeds maximum allowed ceiling: {payload_len} > {MAX_PAYLOAD_LEN}")
        return cls(
            magic=magic,
            version=version,
            opcode=opcode,
            node_id=node_id,
            payload_len=payload_len,
            checksum=checksum,
        )


# Alias WireHeader
WireHeader = Header


class Frame:
    __slots__ = ("header", "payload")

    def __init__(self, header: Header, payload: bytes):
        self.header = header
        self.payload = bytes(payload)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Frame):
            return False
        return self.header == other.header and self.payload == other.payload

    def __repr__(self) -> str:
        return f"Frame(header={self.header!r}, payload={len(self.payload)}B)"

    @classmethod
    def create(cls, opcode: Union[Opcode, int], node_id: int, payload: bytes) -> Frame:
        op = Opcode(opcode)
        payload_bytes = bytes(payload)
        crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        header = Header(
            magic=MIOS_MAGIC,
            version=MIOS_VERSION,
            opcode=op,
            node_id=node_id,
            payload_len=len(payload_bytes),
            checksum=crc,
        )
        return cls(header=header, payload=payload_bytes)

    # Alias new for Rust Frame::new parity
    @classmethod
    def new(cls, opcode: Union[Opcode, int], node_id: int, payload: bytes) -> Frame:
        return cls.create(opcode, node_id, payload)

    def encode(self) -> bytes:
        return self.header.encode() + self.payload

    @classmethod
    def decode(cls, data: bytes) -> Frame:
        header = Header.decode(data)
        expected_len = HEADER_SIZE + header.payload_len
        if len(data) < expected_len:
            raise ValueError(f"Incomplete payload: expected {header.payload_len}B, available {len(data) - HEADER_SIZE}B")
        payload = data[HEADER_SIZE:expected_len]
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if actual_crc != header.checksum:
            raise ValueError(f"CRC32 mismatch: expected 0x{header.checksum:08X}, calculated 0x{actual_crc:08X}")
        return cls(header=header, payload=payload)


# WireFrame class alias for API flexibility
class WireFrame(Frame):
    def __init__(self, opcode: Union[Opcode, int], node_id: int, payload: bytes):
        fr = Frame.create(opcode, node_id, payload)
        super().__init__(header=fr.header, payload=fr.payload)


class NodeWireDispatcher:
    """Dispatches received frames to registered opcode handlers."""

    def __init__(self, node_id: int = 0):
        self.node_id = node_id
        self.handlers: Dict[Opcode, Callable[[Frame], Optional[Frame]]] = {}

    def register_handler(self, opcode: Union[Opcode, int], handler: Callable[[Frame], Optional[Frame]]) -> None:
        self.handlers[Opcode(opcode)] = handler

    def register(self, opcode: Union[Opcode, int], handler: Callable[[Frame], Optional[Frame]]) -> None:
        self.register_handler(opcode, handler)

    def dispatch(self, frame: Frame) -> Optional[Frame]:
        handler = self.handlers.get(frame.header.opcode)
        if handler:
            return handler(frame)
        err_msg = f"Unhandled opcode 0x{int(frame.header.opcode):02X}".encode("utf-8")
        return Frame.create(Opcode.ERROR, self.node_id, err_msg)

    def process_packet(self, data: bytes) -> Optional[bytes]:
        frame = Frame.decode(data)
        resp_frame = self.dispatch(frame)
        if resp_frame:
            return resp_frame.encode()
        return None


# Alias OpcodeDispatcher
OpcodeDispatcher = NodeWireDispatcher


def main() -> int:
    print("[mios-node-wire] MiOS Binary Wire Protocol Engine Ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
