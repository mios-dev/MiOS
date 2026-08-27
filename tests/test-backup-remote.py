#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-DURA remote delta backup synchronizer with chunk hashing, zstd compression, and hash verification.
# AI-related: usr/libexec/mios/storage/mios-backup-remote, usr/lib/systemd/system/mios-backup-remote.service
"""Automated tests for WS-DURA remote delta backup synchronization (T-408 / AGY-2006)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_BACKUP_REMOTE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "mios-backup-remote")

loader = importlib.machinery.SourceFileLoader("backup_remote", _BACKUP_REMOTE_PATH)
spec = importlib.util.spec_from_loader("backup_remote", loader)
if spec and spec.loader:
    backup_remote = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backup_remote
    spec.loader.exec_module(backup_remote)
else:
    raise ImportError(f"Could not load backup_remote module from {_BACKUP_REMOTE_PATH}")

class TestBackupRemote(unittest.TestCase):
    """Validates chunk hashing, manifest creation, delta plan computation, zstd staging, sync, and verification."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mios_test_backup_remote_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_hash_file_chunks(self):
        test_file = os.path.join(self.test_dir, "sample.bin")
        # 10KB file with chunk size 4KB -> 3 chunks (4096, 4096, 2048)
        content = os.urandom(10240)
        with open(test_file, "wb") as f:
            f.write(content)

        chunks = backup_remote.hash_file_chunks(test_file, chunk_size=4096)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["offset"], 0)
        self.assertEqual(chunks[0]["length"], 4096)
        self.assertEqual(chunks[1]["offset"], 4096)
        self.assertEqual(chunks[1]["length"], 4096)
        self.assertEqual(chunks[2]["offset"], 8192)
        self.assertEqual(chunks[2]["length"], 2048)

        # Hash check of chunk 0
        expected_hash0 = backup_remote.hash_bytes(content[:4096])
        self.assertEqual(chunks[0]["sha256"], expected_hash0)

    def test_create_snapshot_manifest(self):
        src_dir = os.path.join(self.test_dir, "source")
        os.makedirs(src_dir, exist_ok=True)

        with open(os.path.join(src_dir, "file1.txt"), "w") as f:
            f.write("Hello MiOS Backup Remote 1")
        with open(os.path.join(src_dir, "file2.txt"), "w") as f:
            f.write("Hello MiOS Backup Remote 2")

        manifest = backup_remote.create_snapshot_manifest(src_dir, snapshot_id="snap_001", chunk_size=1024)
        self.assertEqual(manifest["snapshot_id"], "snap_001")
        self.assertEqual(manifest["total_files"], 2)
        self.assertGreater(manifest["total_bytes"], 0)
        self.assertIn("file1.txt", manifest["files"])
        self.assertIn("file2.txt", manifest["files"])
        self.assertEqual(len(manifest["chunk_index"]), 2)

    def test_delta_plan_retransmission_prevention(self):
        """
        Verify: Generate a baseline backup; add 10MB of data; verify delta backup
        transmits only the 10MB diff payload without retransmitting unchanged data.
        """
        src_dir = os.path.join(self.test_dir, "src_delta")
        os.makedirs(src_dir, exist_ok=True)

        # Baseline: 5MB static database file
        static_file = os.path.join(src_dir, "static_db.bin")
        static_data = b"".join(f"STATIC_DB_BLOCK_{i:04d}_".encode("utf-8") * (1024 * 1024 // 20) for i in range(5))
        with open(static_file, "wb") as f:
            f.write(static_data)

        baseline_manifest = backup_remote.create_snapshot_manifest(src_dir, snapshot_id="snap_base", chunk_size=1024*1024)

        # Add 10MB new incremental delta file with unique chunks
        new_file = os.path.join(src_dir, "incremental_diff.bin")
        new_data = b"".join(f"DIFF_PAYLOAD_BLK_{i:04d}".encode("utf-8") * (1024 * 1024 // 20) for i in range(10))
        with open(new_file, "wb") as f:
            f.write(new_data)

        current_manifest = backup_remote.create_snapshot_manifest(src_dir, snapshot_id="snap_inc", chunk_size=1024*1024)

        delta_plan = backup_remote.compute_delta_plan(current_manifest, baseline_manifest)

        # Verify only 10MB new bytes are planned for transmission, not 15MB
        self.assertEqual(delta_plan["new_raw_bytes"], len(new_data))
        self.assertEqual(delta_plan["reused_bytes"], len(static_data))
        self.assertEqual(delta_plan["total_raw_bytes"], len(static_data) + len(new_data))
        self.assertGreater(delta_plan["dedup_ratio_pct"], 30.0)

    def test_compression_and_staging(self):
        src_dir = os.path.join(self.test_dir, "src_comp")
        staging_dir = os.path.join(self.test_dir, "staging")
        os.makedirs(src_dir, exist_ok=True)

        test_payload = b"COMPRESSION_TEST_DATA_ABCXYZ" * 1000
        with open(os.path.join(src_dir, "data.bin"), "wb") as f:
            f.write(test_payload)

        manifest = backup_remote.create_snapshot_manifest(src_dir, snapshot_id="snap_stage", chunk_size=1024*1024)
        delta_plan = backup_remote.compute_delta_plan(manifest, baseline_manifest=None)

        staged_files, comp_bytes = backup_remote.stage_delta_chunks(
            source_dir=src_dir,
            current_manifest=manifest,
            delta_plan=delta_plan,
            staging_dir=staging_dir,
            zstd_level=3,
        )

        self.assertGreater(len(staged_files), 1)  # Chunks + manifest
        self.assertTrue(any(f.endswith(".chunk.zst") for f in staged_files))
        self.assertTrue(any(f.endswith("manifest_snap_stage.json") for f in staged_files))
        self.assertGreater(comp_bytes, 0)
        self.assertLess(comp_bytes, len(test_payload))  # Verified compression

    def test_sync_and_remote_verification(self):
        src_dir = os.path.join(self.test_dir, "src_sync")
        staging_dir = os.path.join(self.test_dir, "staging_sync")
        remote_dir = os.path.join(self.test_dir, "remote_store")
        os.makedirs(src_dir, exist_ok=True)

        with open(os.path.join(src_dir, "file_a.txt"), "w") as f:
            f.write("Alpha delta content")

        manifest = backup_remote.create_snapshot_manifest(src_dir, snapshot_id="snap_sync_01", chunk_size=4096)
        delta_plan = backup_remote.compute_delta_plan(manifest, baseline_manifest=None)

        backup_remote.stage_delta_chunks(
            source_dir=src_dir,
            current_manifest=manifest,
            delta_plan=delta_plan,
            staging_dir=staging_dir,
        )

        sync_res = backup_remote.sync_delta_payload(
            staging_dir=staging_dir,
            remote_target=remote_dir,
            backend="local",
        )
        self.assertEqual(sync_res["status"], "success")

        # Verify remote target
        ok, msg = backup_remote.verify_remote_manifest(
            remote_target=remote_dir,
            snapshot_id="snap_sync_01",
            backend="local",
        )
        self.assertTrue(ok, f"Verification failed: {msg}")

    def test_prune_old_manifests(self):
        manifest_dir = os.path.join(self.test_dir, "manifests")
        os.makedirs(manifest_dir, exist_ok=True)

        for i in range(10):
            m_path = os.path.join(manifest_dir, f"manifest_snap_{i:02d}.json")
            with open(m_path, "w") as f:
                json.dump({"snapshot_id": f"snap_{i:02d}"}, f)
            # Set progressive mtime
            mtime = time.time() - (10 - i) * 100
            os.utime(m_path, (mtime, mtime))

        deleted = backup_remote.prune_old_manifests(manifest_dir, keep_count=7)
        self.assertEqual(len(deleted), 3)

        remaining = [f for f in os.listdir(manifest_dir) if f.startswith("manifest_")]
        self.assertEqual(len(remaining), 7)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBackupRemote)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
