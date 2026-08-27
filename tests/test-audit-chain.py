#!/usr/bin/env python3
# AI-hint: Automated unit test suite for cryptographic Merkle audit chain, Ed25519 signing, and tamper detection.
# AI-related: usr/libexec/mios/ai/audit_chain.py, usr/share/mios/mios.toml
"""Unit and integration test suite for AuditChainRecorder and audit_chain CLI (T-554)."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "audit_chain.py")

spec = importlib.util.spec_from_file_location("audit_chain", _TARGET_PATH)
if spec and spec.loader:
    audit_chain = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = audit_chain
    spec.loader.exec_module(audit_chain)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestAuditChain(unittest.TestCase):
    """Test suite for cryptographic audit chain verification, Ed25519 signatures, and Merkle proofs."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-test-audit-")
        self.log_path = os.path.join(self.tmpdir.name, "audit_chain.jsonl")
        self.key_path = os.path.join(self.tmpdir.name, "node_ed25519.key")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_genesis_block_and_chain_creation(self):
        recorder = audit_chain.AuditChainRecorder(
            log_path=self.log_path,
            key_path=self.key_path,
            mock=True,
        )
        blocks = recorder.load_blocks()
        self.assertEqual(len(blocks), 1)
        genesis = blocks[0]
        self.assertEqual(genesis["index"], 0)
        self.assertEqual(genesis["prev_hash"], "0" * 64)
        self.assertEqual(genesis["event_type"], "genesis")

        ver = recorder.verify_chain()
        self.assertTrue(ver["valid"])
        self.assertEqual(ver["status"], "verified")
        self.assertEqual(ver["blocks_verified"], 1)

    def test_record_sequential_events(self):
        recorder = audit_chain.AuditChainRecorder(
            log_path=self.log_path,
            key_path=self.key_path,
            mock=True,
        )

        for i in range(1, 10):
            res = recorder.record_event(
                event_type="file_edit",
                payload={"target_file": f"usr/share/doc/chapter_{i}.md", "lines_changed": i * 10},
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["index"], i)

        blocks = recorder.load_blocks()
        self.assertEqual(len(blocks), 10)

        ver = recorder.verify_chain()
        self.assertTrue(ver["valid"])
        self.assertEqual(ver["blocks_verified"], 10)
        self.assertIsNotNone(ver["merkle_root"])

    def test_merkle_tree_proof_generation_and_verification(self):
        leaf_hashes = [
            audit_chain.hashlib.sha256(f"leaf_{i}".encode("utf-8")).hexdigest()
            for i in range(8)
        ]
        tree = audit_chain.MerkleTree(leaf_hashes)
        root = tree.root

        for idx in range(len(leaf_hashes)):
            proof = tree.get_proof(idx)
            is_valid = audit_chain.MerkleTree.verify_proof(leaf_hashes[idx], proof, root)
            self.assertTrue(is_valid, f"Merkle proof verification failed for leaf index {idx}")

        # Invalid leaf hash must fail verification
        bad_leaf = audit_chain.hashlib.sha256(b"fake_leaf").hexdigest()
        self.assertFalse(audit_chain.MerkleTree.verify_proof(bad_leaf, tree.get_proof(0), root))

    def test_tamper_detection_payload_modified(self):
        recorder = audit_chain.AuditChainRecorder(log_path=self.log_path, key_path=self.key_path, mock=True)
        recorder.record_event("decision", {"action": "deploy_service", "target": "agent-pipe"})
        recorder.record_event("tool_call", {"tool": "bwrap", "status": "executed"})

        blocks = recorder.load_blocks()
        tampered_blocks = copy.deepcopy(blocks)

        # Alter payload of block 1
        tampered_blocks[1]["payload"]["target"] = "malicious_backdoor"

        ver = recorder.verify_chain(tampered_blocks)
        self.assertFalse(ver["valid"])
        self.assertEqual(ver["status"], "payload_tampered")
        self.assertEqual(ver["failed_block_index"], 1)

    def test_tamper_detection_broken_prev_hash(self):
        recorder = audit_chain.AuditChainRecorder(log_path=self.log_path, key_path=self.key_path, mock=True)
        recorder.record_event("decision", {"step": 1})
        recorder.record_event("decision", {"step": 2})

        blocks = recorder.load_blocks()
        tampered_blocks = copy.deepcopy(blocks)

        # Alter prev_hash of block 2
        tampered_blocks[2]["prev_hash"] = "f" * 64

        ver = recorder.verify_chain(tampered_blocks)
        self.assertFalse(ver["valid"])
        self.assertEqual(ver["status"], "broken_hash_link")
        self.assertEqual(ver["failed_block_index"], 2)

    def test_tamper_detection_invalid_signature(self):
        recorder = audit_chain.AuditChainRecorder(log_path=self.log_path, key_path=self.key_path, mock=True)
        recorder.record_event("decision", {"step": "approve"})

        blocks = recorder.load_blocks()
        tampered_blocks = copy.deepcopy(blocks)

        # Invalidate signature
        tampered_blocks[1]["signature"] = "0" * 64

        ver = recorder.verify_chain(tampered_blocks)
        self.assertFalse(ver["valid"])
        self.assertEqual(ver["status"], "signature_invalid")
        self.assertEqual(ver["failed_block_index"], 1)

    def test_file_persistence_and_reload(self):
        recorder = audit_chain.AuditChainRecorder(
            log_path=self.log_path,
            key_path=self.key_path,
            mock=False,
        )
        recorder.record_event("boot", {"status": "firstboot_ok"})
        recorder.record_event("auth", {"user": "mios", "method": "fido2"})

        self.assertTrue(os.path.isfile(self.log_path))

        # Re-instantiate recorder to load from disk
        recorder2 = audit_chain.AuditChainRecorder(
            log_path=self.log_path,
            key_path=self.key_path,
            mock=False,
        )
        blocks = recorder2.load_blocks()
        self.assertEqual(len(blocks), 3)  # Genesis + 2 events

        ver = recorder2.verify_chain(blocks)
        self.assertTrue(ver["valid"])

    def test_cli_execution_mock(self):
        with patch.object(sys, "argv", ["audit_chain.py", "--mock", "--record", "--event", "test_cli", "--json"]):
            code = audit_chain.main()
            self.assertEqual(code, 0)

        with patch.object(sys, "argv", ["audit_chain.py", "--mock", "--verify", "--json"]):
            code = audit_chain.main()
            self.assertEqual(code, 0)

        with patch.object(sys, "argv", ["audit_chain.py", "--mock", "--status", "--json"]):
            code = audit_chain.main()
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
