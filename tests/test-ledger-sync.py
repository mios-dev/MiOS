#!/usr/bin/env python3
# AI-hint: Automated unit test suite for CephFS transactional ledger replication and SHA-256 integrity verification.
# AI-related: usr/libexec/mios/storage/mios-ledger-sync, usr/lib/systemd/system/mios-ledger-sync.service
"""Automated tests for CephFS transactional ledger replication, block hashing, and reconciliation."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios"))
sys.path.insert(0, os.path.join(_ROOT, "lib", "mios"))

_SYNC_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "mios-ledger-sync")
loader = importlib.machinery.SourceFileLoader("ledger_sync", _SYNC_PATH)
spec = importlib.util.spec_from_loader("ledger_sync", loader)
if spec and spec.loader:
    ledger_sync = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ledger_sync
    spec.loader.exec_module(ledger_sync)
else:
    raise ImportError(f"Could not load mios-ledger-sync module from {_SYNC_PATH}")

class TestLedgerSync(unittest.TestCase):
    """Tests block creation, cryptographic linking, tamper detection, and cross-pool sync."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mios_ledger_test_")
        self.src_dir = os.path.join(self.test_dir, "src_pool")
        self.dst_dir = os.path.join(self.test_dir, "dst_pool")
        self.rec_log = os.path.join(self.test_dir, "reconciliation.log")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_canonical_json_determinism(self):
        d1 = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
        d2 = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}
        self.assertEqual(ledger_sync.canonical_json(d1), ledger_sync.canonical_json(d2))
        self.assertEqual(ledger_sync.canonical_json(d1), '{"a":1,"b":2,"nested":{"y":20,"z":10}}')

    def test_block_creation_and_genesis_validation(self):
        payload = {"event": "genesis_init", "cluster": "ceph-test"}
        block = ledger_sync.Block.create(
            index=0,
            prev_hash=ledger_sync.GENESIS_PREV_HASH,
            payload=payload,
        )
        self.assertEqual(block.index, 0)
        self.assertEqual(block.prev_hash, ledger_sync.GENESIS_PREV_HASH)
        self.assertEqual(block.payload_hash, ledger_sync.compute_hash(ledger_sync.canonical_json(payload)))

        ok, err = block.validate_integrity(prev_block=None)
        self.assertTrue(ok, f"Genesis validation failed: {err}")

    def test_sequential_chain_linking(self):
        chain = ledger_sync.LedgerChain(self.src_dir)
        b0 = chain.append({"action": "create_user", "uid": 1000})
        b1 = chain.append({"action": "assign_quota", "uid": 1000, "bytes": 5000000})
        b2 = chain.append({"action": "audit_event", "status": "approved"})

        self.assertEqual(b0.index, 0)
        self.assertEqual(b1.index, 1)
        self.assertEqual(b2.index, 2)

        self.assertEqual(b1.prev_hash, b0.block_hash)
        self.assertEqual(b2.prev_hash, b1.block_hash)

        valid, count, errors = chain.verify()
        self.assertTrue(valid, f"Chain verify failed: {errors}")
        self.assertEqual(count, 3)

    def test_hmac_signature_verification(self):
        key = "mios-secret-cryptographic-key-12345"
        chain = ledger_sync.LedgerChain(self.src_dir)
        b0 = chain.append({"action": "root_command", "cmd": "ceph status"}, secret_key=key)
        self.assertIsNotNone(b0.signature)

        # Verify with correct key
        valid, count, errors = chain.verify(secret_key=key)
        self.assertTrue(valid)

        # Verify with wrong key fails
        valid_wrong, _, errors_wrong = chain.verify(secret_key="wrong-key")
        self.assertFalse(valid_wrong)
        self.assertTrue(any("signature" in e for e in errors_wrong))

    def test_tamper_detection_mutated_payload(self):
        chain = ledger_sync.LedgerChain(self.src_dir)
        chain.append({"tx": 1, "amount": 100})
        chain.append({"tx": 2, "amount": 200})

        # Mutate block 1 on disk
        b1_path = os.path.join(self.src_dir, "blocks", "block_00000001.json")
        with open(b1_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["payload"]["amount"] = 999999  # Tamper!
        with open(b1_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        valid, count, errors = chain.verify()
        self.assertFalse(valid, "Tampered block should have failed verification")
        self.assertTrue(any("payload hash mismatch" in e for e in errors))

    def test_tamper_detection_broken_chain_hash(self):
        chain = ledger_sync.LedgerChain(self.src_dir)
        chain.append({"tx": 1})
        chain.append({"tx": 2})

        # Mutate prev_hash in block 1
        b1_path = os.path.join(self.src_dir, "blocks", "block_00000001.json")
        with open(b1_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["prev_hash"] = "f" * 64
        # Recalculate block hash so internal matches, but parent linkage fails
        header = f"1:{data['timestamp']}:{data['prev_hash']}:{data['payload_hash']}"
        data["block_hash"] = ledger_sync.compute_hash(header)
        with open(b1_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        valid, count, errors = chain.verify()
        self.assertFalse(valid)
        self.assertTrue(any("does not match parent" in e for e in errors))

    def test_replication_between_pools(self):
        src_chain = ledger_sync.LedgerChain(self.src_dir)
        for i in range(5):
            src_chain.append({"entry_index": i, "data": f"payload_{i}"})

        engine = ledger_sync.LedgerSyncEngine()
        report = engine.replicate(self.src_dir, self.dst_dir, reconciliation_log=self.rec_log)

        self.assertEqual(report["status"], "synchronized")
        self.assertEqual(report["synced_blocks"], 5)
        self.assertEqual(report["total_blocks"], 5)

        # Verify destination chain independently
        dst_chain = ledger_sync.LedgerChain(self.dst_dir)
        valid, count, errors = dst_chain.verify()
        self.assertTrue(valid)
        self.assertEqual(count, 5)

        # Verify reconciliation log exists and contains valid JSON record
        self.assertTrue(os.path.exists(self.rec_log))
        with open(self.rec_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        rec_data = json.loads(lines[0])
        self.assertEqual(rec_data["synced_blocks"], 5)

    def test_incremental_replication(self):
        src_chain = ledger_sync.LedgerChain(self.src_dir)
        for i in range(3):
            src_chain.append({"entry": i})

        engine = ledger_sync.LedgerSyncEngine()
        engine.replicate(self.src_dir, self.dst_dir)

        # Append 2 more entries to source
        src_chain.append({"entry": 3})
        src_chain.append({"entry": 4})

        # Incremental sync
        report2 = engine.replicate(self.src_dir, self.dst_dir)
        self.assertEqual(report2["synced_blocks"], 2)
        self.assertEqual(report2["total_blocks"], 5)

    def test_replication_refuses_corrupted_source(self):
        src_chain = ledger_sync.LedgerChain(self.src_dir)
        src_chain.append({"clean": True})

        # Tamper source block
        b0_path = os.path.join(self.src_dir, "blocks", "block_00000000.json")
        with open(b0_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["payload"]["clean"] = False
        with open(b0_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        engine = ledger_sync.LedgerSyncEngine()
        with self.assertRaises(ValueError) as ctx:
            engine.replicate(self.src_dir, self.dst_dir)
        self.assertIn("Source ledger integrity failure", str(ctx.exception))

    def test_service_unit_file_exists(self):
        svc_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-ledger-sync.service")
        self.assertTrue(os.path.exists(svc_path), f"Service unit missing at {svc_path}")
        with open(svc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("mios-ledger-sync", content)
        self.assertIn("Type=oneshot", content)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLedgerSync)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
