#!/usr/bin/env python3
# AI-hint: CRDT LWW-Element-Set and Vector Clock state synchronization engine for edge mesh nodes.
# AI-related: src/mios-rs/mios-node/src/state_sync.rs, tests/test-node-crdt.py, usr/share/doc/mios/adr/0020-edge-node-mesh-protocol-and-dual-tier-execution.md
"""
MiOS Distributed Lock-Free State Synchronization Engine.
Implements Last-Write-Wins Element-Set (LWW-Element-Set) CRDT, Vector Clock Causality,
and Disk-Backed Persistence (Snapshot & Append-Only Log).
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional, Tuple


class VectorClock:
    """Vector clock causality tracker for distributed mesh nodes."""

    def __init__(self, clocks: Optional[Dict[int, int]] = None) -> None:
        self.clocks: Dict[int, int] = dict(clocks) if clocks else {}

    def increment(self, node_id: int) -> None:
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1

    def merge(self, other: VectorClock) -> None:
        for node_id, remote_val in other.clocks.items():
            local_val = self.clocks.get(node_id, 0)
            self.clocks[node_id] = max(local_val, remote_val)

    def to_dict(self) -> Dict[str, int]:
        return {str(k): v for k, v in self.clocks.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> VectorClock:
        return cls({int(k): v for k, v in d.items()})

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return False
        return self.clocks == other.clocks


class StateElement:
    """Individual state register with LWW timestamp, originator, and deletion tombstone."""

    def __init__(
        self,
        key: str,
        value: bytes,
        timestamp_ns: int,
        originating_node_id: int,
        is_deleted: bool = False,
    ) -> None:
        self.key = key
        self.value = value
        self.timestamp_ns = timestamp_ns
        self.originating_node_id = originating_node_id
        self.is_deleted = is_deleted

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value_hex": self.value.hex(),
            "timestamp_ns": self.timestamp_ns,
            "originating_node_id": self.originating_node_id,
            "is_deleted": self.is_deleted,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StateElement:
        return cls(
            key=d["key"],
            value=bytes.fromhex(d.get("value_hex", "")),
            timestamp_ns=d["timestamp_ns"],
            originating_node_id=d["originating_node_id"],
            is_deleted=d.get("is_deleted", False),
        )

    def is_newer_than(self, other: StateElement) -> bool:
        if self.timestamp_ns != other.timestamp_ns:
            return self.timestamp_ns > other.timestamp_ns
        return self.originating_node_id > other.originating_node_id


class StateStore:
    """LWW-Element-Set CRDT state store with snapshotting and vector clock tracking."""

    def __init__(self, node_id: int, persistence_path: Optional[str] = None) -> None:
        self.node_id = node_id
        self.vector_clock = VectorClock()
        self.elements: Dict[str, StateElement] = {}
        self.persistence_path = persistence_path
        if persistence_path and os.path.exists(persistence_path):
            self.load_from_disk(persistence_path)

    def set(self, key: str, value: bytes) -> None:
        now_ns = time.time_ns()
        self.vector_clock.increment(self.node_id)
        elem = StateElement(
            key=key,
            value=value,
            timestamp_ns=now_ns,
            originating_node_id=self.node_id,
            is_deleted=False,
        )
        self.elements[key] = elem
        self._append_log(elem)

    def delete(self, key: str) -> None:
        now_ns = time.time_ns()
        self.vector_clock.increment(self.node_id)
        elem = StateElement(
            key=key,
            value=b"",
            timestamp_ns=now_ns,
            originating_node_id=self.node_id,
            is_deleted=True,
        )
        self.elements[key] = elem
        self._append_log(elem)

    def get(self, key: str) -> Optional[bytes]:
        elem = self.elements.get(key)
        if elem and not elem.is_deleted:
            return elem.value
        return None

    def replicable_elements(self) -> List[StateElement]:
        return list(self.elements.values())

    def merge_remote_store(
        self, remote_clock: VectorClock, remote_elements: List[StateElement]
    ) -> int:
        """Merges remote elements into local store; returns count of applied mutations."""
        self.vector_clock.merge(remote_clock)
        applied = 0
        for rem in remote_elements:
            loc = self.elements.get(rem.key)
            if loc is None or rem.is_newer_than(loc):
                self.elements[rem.key] = rem
                self._append_log(rem)
                applied += 1
        return applied

    def _append_log(self, elem: StateElement) -> None:
        if not self.persistence_path:
            return
        log_file = self.persistence_path + ".log"
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(elem.to_dict()) + "\n")

    def save_to_disk(self, path: Optional[str] = None) -> None:
        out_path = path or self.persistence_path
        if not out_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        data = {
            "node_id": self.node_id,
            "vector_clock": self.vector_clock.to_dict(),
            "elements": [e.to_dict() for e in self.elements.values()],
        }
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, out_path)

    def load_from_disk(self, path: str) -> None:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.node_id = data["node_id"]
        self.vector_clock = VectorClock.from_dict(data["vector_clock"])
        self.elements = {}
        for ed in data.get("elements", []):
            elem = StateElement.from_dict(ed)
            self.elements[elem.key] = elem