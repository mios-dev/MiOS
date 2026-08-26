#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_shm_kv sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_shm_kv."""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_shm_kv import ShmKVTransfer

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    shm = ShmKVTransfer(segment_name="test_shm_kv_segment", size_bytes=65536)
    written = shm.write_tensor_metadata(128, 768, b"dummy_tensor_bytes")
    check("write tensor metadata", written)

    res = shm.read_tensor_metadata()
    check("read tensor metadata returns tuple", res is not None)
    if res:
        seq, dim, payload = res
        check("seq_len matches", seq == 128)
        check("hidden_dim matches", dim == 768)
        check("payload matches", payload == b"dummy_tensor_bytes")

    shm.cleanup()

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
