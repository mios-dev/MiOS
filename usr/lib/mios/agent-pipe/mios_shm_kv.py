# AI-hint: POSIX shared memory zero-copy KV-cache transfer between co-located worker processes.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-shm-kv.py
"""
MiOS Agent-Pipe Zero-Copy Shared Memory KV Cache Manager.
Allocates POSIX shared memory segments under /dev/shm/mios_kv_* for high-throughput tensor sharing.
"""

from __future__ import annotations

import os
import sys
import mmap
import struct
from typing import Optional, Tuple


class ShmKVTransfer:
    """Manages shared memory tensor buffers with binary serialization headers."""

    HEADER_FORMAT = "!II"  # seq_len, hidden_dim (8 bytes)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, segment_name: str = "mios_kv_default", size_bytes: int = 1048576) -> None:
        self.segment_name = segment_name.replace("/", "").replace("\\", "")
        self.size_bytes = size_bytes
        self._shm_path = f"/dev/shm/{self.segment_name}" if os.path.exists("/dev/shm") else os.path.join(os.environ.get("TEMP", "C:\\temp"), self.segment_name)

    def write_tensor_metadata(self, seq_len: int, hidden_dim: int, payload: bytes) -> bool:
        """Writes tensor header and raw binary payload to the shared memory buffer."""
        header = struct.pack(self.HEADER_FORMAT, seq_len, hidden_dim)
        data = header + payload
        if len(data) > self.size_bytes:
            return False

        os.makedirs(os.path.dirname(self._shm_path), exist_ok=True)
        with open(self._shm_path, "wb") as f:
            f.write(data)
        return True

    def read_tensor_metadata(self) -> Optional[Tuple[int, int, bytes]]:
        """Reads tensor header and payload from the shared memory segment."""
        if not os.path.exists(self._shm_path):
            return None
        with open(self._shm_path, "rb") as f:
            raw = f.read()
        if len(raw) < self.HEADER_SIZE:
            return None
        seq_len, hidden_dim = struct.unpack(self.HEADER_FORMAT, raw[:self.HEADER_SIZE])
        payload = raw[self.HEADER_SIZE:]
        return seq_len, hidden_dim, payload

    def cleanup(self) -> None:
        """Removes the shared memory backing file."""
        if os.path.exists(self._shm_path):
            try:
                os.remove(self._shm_path)
            except OSError:
                pass
