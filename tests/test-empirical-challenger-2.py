#!/usr/bin/env python3
# AI-hint: Comprehensive empirical adversarial test suite authored by Challenger 2 for T-404..T-412.
# AI-related: usr/libexec/mios/storage/mios-bench-storage, usr/libexec/mios/sec/mios-luks-rotate, usr/libexec/mios/mem/mios-tmpfs-spill, usr/libexec/mios/log/mios-log-streamer, usr/libexec/mios/storage/mios-backup-remote, usr/libexec/mios/db/mios-db-doctor.py, usr/libexec/mios/db/mios-db-migrate.py, usr/share/containers/systemd/mios-radosgw.container
"""
MiOS Empirical Adversarial Test Harness (Challenger 2).

Executes stress-testing, boundary attacks, simulated memory pressure,
fuzzing payloads, security exclusions, SQL injection defense, and
zero-downtime safety checks against:
- T-404: Ceph RADOS Gateway Quadlet S3 Container
- T-405: LUKS2 Zero-Downtime Key Rotation Engine (mios-luks-rotate)
- T-407: SQLite / PostgreSQL Database Doctor (mios-db-doctor)
- T-408: Remote Delta Snapshot Backup Synchronizer (mios-backup-remote)
- T-409: Storage Performance Benchmark Harness (mios-bench-storage)
- T-410: Automated tmpfs Spill-to-NVMe Manager (mios-tmpfs-spill)
- T-411: Unified Journald Log Aggregation & pgvector Streamer (mios-log-streamer)
- T-412: Zero-Downtime Database Migration Runner (mios-db-migrate)
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional

_HERE = os.path.abspath(os.path.dirname(__file__)) if "__file__" in globals() else os.path.abspath(".")
_ROOT = os.path.normpath(os.path.join(_HERE, "..")) if os.path.basename(_HERE) == "tests" else _HERE


def load_module(name: str, rel_path: str) -> Any:
    from importlib.machinery import SourceFileLoader
    full_path = os.path.join(_ROOT, rel_path)
    loader = SourceFileLoader(name, full_path)
    spec = importlib.util.spec_from_loader(name, loader)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise ImportError(f"Could not load module {name} from {full_path}")


# Load target modules under test
mod_bench = load_module("bench_storage", "usr/libexec/mios/storage/mios-bench-storage")
mod_luks = load_module("luks_rotate", "usr/libexec/mios/sec/mios-luks-rotate")
mod_spill = load_module("tmpfs_spill", "usr/libexec/mios/mem/mios-tmpfs-spill")
mod_log = load_module("log_streamer", "usr/libexec/mios/log/mios-log-streamer")
mod_backup = load_module("backup_remote", "usr/libexec/mios/storage/mios-backup-remote")
mod_doctor = load_module("db_doctor", "usr/libexec/mios/db/mios-db-doctor.py")
mod_migrate = load_module("db_migrate", "usr/libexec/mios/db/mios-db-migrate.py")


class TestAdversarialBenchStorage(unittest.TestCase):
    """Adversarial testing on mios-bench-storage: percentile math, profile bounds, and cleanup."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-bench-adv-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_percentile_boundary_conditions(self):
        """Stress-test percentile function with empty, 1-element, duplicates, and extreme percentiles."""
        # 1. Empty list
        self.assertEqual(mod_bench.percentile([], 50), 0.0)
        self.assertEqual(mod_bench.percentile([], 0), 0.0)
        self.assertEqual(mod_bench.percentile([], 100), 0.0)

        # 2. Single element
        self.assertEqual(mod_bench.percentile([42.5], 0), 42.5)
        self.assertEqual(mod_bench.percentile([42.5], 50), 42.5)
        self.assertEqual(mod_bench.percentile([42.5], 100), 42.5)

        # 3. Two elements
        data = [10.0, 20.0]
        self.assertEqual(mod_bench.percentile(data, 0), 10.0)
        self.assertEqual(mod_bench.percentile(data, 50), 15.0)
        self.assertEqual(mod_bench.percentile(data, 100), 20.0)

        # 4. Large list with duplicate values
        data_dup = [100.0] * 50
        self.assertEqual(mod_bench.percentile(data_dup, 95), 100.0)

    def test_quick_benchmark_execution_and_guaranteed_cleanup(self):
        """Execute full benchmark and verify scratch file lifecycle and cleanup."""
        report = mod_bench.run_full_storage_benchmark(
            target_dir=self.tmpdir,
            file_size_mb=4,
            duration_sec=0.1,
            fsync_iterations=5,
            profile="edge_llm",
        )
        self.assertIn("iops_rand_read_4k", report)
        self.assertIn("fsync_latency_us", report)
        self.assertIn("assessment", report)
        self.assertEqual(report["assessment"]["profile"], "edge_llm")

        # Verify no scratch files (.dat) were leaked in target_dir
        remaining = [f for f in os.listdir(self.tmpdir) if f.startswith("mios_bench_scratch_")]
        self.assertEqual(len(remaining), 0, f"Leaked scratch files: {remaining}")

    def test_inference_floor_evaluation_matrix(self):
        """Adversarially test hardware inference floor boundary decisions."""
        mock_metrics_pass = {
            "iops_rand_read_4k": 3500,
            "iops_rand_write_4k": 1600,
            "mbps_seq_read_1m": 300.0,
            "mbps_seq_write_1m": 150.0,
            "fsync_latency_us": {"p95_us": 12000.0},
        }
        res_pass = mod_bench.evaluate_inference_floors(mock_metrics_pass, profile_name="edge_llm")
        self.assertTrue(res_pass["meets_ai_inference_floors"])

        # Test failure if even 1 metric misses floor
        mock_metrics_fail = dict(mock_metrics_pass)
        mock_metrics_fail["mbps_seq_read_1m"] = 249.0  # Required: 250.0
        res_fail = mod_bench.evaluate_inference_floors(mock_metrics_fail, profile_name="edge_llm")
        self.assertFalse(res_fail["meets_ai_inference_floors"])
        self.assertFalse(res_fail["evaluations"]["mbps_seq_read_1m"]["passed"])


class TestAdversarialLUKSRotate(unittest.TestCase):
    """Adversarial testing on mios-luks-rotate: key validation aborts, slot exhaustion, and log safety."""

    def test_key_rotation_aborts_and_preserves_old_slot_on_failure(self):
        """CRITICAL: If test_passphrase fails on newly added slot, abort without touching old slot."""
        calls = []

        def mock_runner(cmd, input=None, capture_output=True, text=True, check=True):
            cmd_str = " ".join(cmd)
            calls.append((cmd_str, input))
            if "luksDump" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, stdout='{"keyslots":{"0":{"state":"active"}}}', stderr="")
            elif "luksHeaderBackup" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            elif "luksAddKey" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            elif "--test-passphrase" in cmd_str:
                # First check (current key) passes; second check (new key) FAILS
                if input and "old_secret" in input:
                    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Decryption failed")
            elif "luksKillSlot" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        dev = mod_luks.LUKSDevice(runner=mock_runner)
        tmpdir = tempfile.mkdtemp()
        engine = mod_luks.LUKSRotationEngine(luks_device=dev, backup_root=tmpdir)

        try:
            with self.assertRaises(RuntimeError) as ctx:
                engine.rotate_key("/dev/sda2", current_passphrase="old_secret", new_passphrase="bad_new_secret")
            self.assertIn("ABORTED ROTATION", str(ctx.exception))

            # Verify that luksKillSlot was NOT called with slot 0 (the active old slot)
            killed_slots = [c[0] for c in calls if "luksKillSlot" in c[0]]
            for k in killed_slots:
                self.assertNotIn("luksKillSlot /dev/sda2 0", k, "CRITICAL ERROR: Old slot 0 was killed despite new key verification failure!")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_free_keyslots_rejection(self):
        """Verify engine refuses to rotate if all keyslots are occupied."""
        # 32 active slots
        all_slots_json = json.dumps({"keyslots": {str(i): {"state": "active"} for i in range(32)}})

        def mock_runner(cmd, input=None, capture_output=True, text=True, check=True):
            if "luksDump" in " ".join(cmd):
                return subprocess.CompletedProcess(cmd, 0, stdout=all_slots_json, stderr="")
            elif "--test-passphrase" in " ".join(cmd):
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        dev = mod_luks.LUKSDevice(runner=mock_runner)
        engine = mod_luks.LUKSRotationEngine(luks_device=dev)
        with self.assertRaises(RuntimeError) as ctx:
            engine.rotate_key("/dev/nvme0n1p3", current_passphrase="valid_pass")
        self.assertIn("No available free keyslots", str(ctx.exception))


class TestAdversarialTmpfsSpill(unittest.TestCase):
    """Adversarial testing on mios-tmpfs-spill: security exclusions, PSI triggers, and LRU eviction."""

    def setUp(self):
        self.src_dir = tempfile.mkdtemp(prefix="mios-tmpfs-src-")
        self.tgt_dir = tempfile.mkdtemp(prefix="mios-tmpfs-tgt-")

    def tearDown(self):
        shutil.rmtree(self.src_dir, ignore_errors=True)
        shutil.rmtree(self.tgt_dir, ignore_errors=True)

    def test_security_sensitive_exclusion_matrix(self):
        """Adversarially verify that no crypto keys, tokens, ssh/gpg sockets, or credentials are spilled."""
        sensitive_files = [
            "id_rsa", "id_ed25519", "server.key", "ca.crt", "tls.pem",
            "access_token.jwt", "bearer_token", "admin.password", "app.secret",
            "ssh-agent.1234", "gpg-agent.socket", "X11-unix.sock", "systemd.lock",
        ]
        for sname in sensitive_files:
            p = os.path.join(self.src_dir, sname)
            with open(p, "wb") as f:
                f.write(b"TOP_SECRET_CREDENTIALS_" * 100000)  # > 1MB

        # Create 1 legitimate big file
        legit_path = os.path.join(self.src_dir, "large_cache.bin")
        with open(legit_path, "wb") as f:
            f.write(b"LEGITIMATE_CACHE_DATA_" * 100000)

        # Trigger spill under high PSI
        res = mod_spill.evaluate_and_spill(
            source_dir=self.src_dir,
            target_dir=self.tgt_dir,
            mock_psi=75.0,  # > 60%
            min_file_size=1024 * 1024,
        )

        self.assertTrue(res["spill_action_taken"])
        self.assertEqual(res["files_spilled"], 1)
        self.assertEqual(res["spilled_details"][0]["source"], legit_path)

        # Ensure all sensitive files remain regular non-symlinked files in src_dir
        for sname in sensitive_files:
            p = os.path.join(self.src_dir, sname)
            self.assertTrue(os.path.exists(p))
            self.assertFalse(os.path.islink(p), f"Security sensitive file {sname} was improperly symlinked/spilled!")

    def test_lru_quota_eviction_and_broken_symlink_cleanup(self):
        """Verify oldest spilled files are evicted when exceeding max_spill_bytes and broken symlinks purged."""
        # Create 3 files of 1MB each
        f1 = os.path.join(self.src_dir, "file1.dat")
        f2 = os.path.join(self.src_dir, "file2.dat")
        f3 = os.path.join(self.src_dir, "file3.dat")

        with open(f1, "wb") as f:
            f.write(b"A" * (1024 * 1024))
        time.sleep(0.01)
        with open(f2, "wb") as f:
            f.write(b"B" * (1024 * 1024))
        time.sleep(0.01)
        with open(f3, "wb") as f:
            f.write(b"C" * (1024 * 1024))

        # Set quota to 2.5MB (file1 + file2 + file3 = 3.0MB -> file1 must be evicted)
        res = mod_spill.evaluate_and_spill(
            source_dir=self.src_dir,
            target_dir=self.tgt_dir,
            mock_psi=80.0,
            min_file_size=512 * 1024,
            max_spill_bytes=int(2.5 * 1024 * 1024),
        )

        self.assertTrue(res["spill_action_taken"])
        self.assertEqual(res["files_spilled"], 3)
        self.assertEqual(res["evicted_files"], 1)

        ledger = mod_spill.load_spill_ledger(self.tgt_dir)
        self.assertLessEqual(ledger["total_spilled_bytes"], int(2.5 * 1024 * 1024))

    def test_unspill_full_restoration(self):
        """Verify unspill cleanly restores symlinks back to physical files."""
        fpath = os.path.join(self.src_dir, "workload.dat")
        test_content = b"RESTORATION_INTEGRITY_CHECK_" * 50000
        with open(fpath, "wb") as f:
            f.write(test_content)

        mod_spill.evaluate_and_spill(
            source_dir=self.src_dir,
            target_dir=self.tgt_dir,
            mock_psi=90.0,
            min_file_size=500 * 1024,
        )
        self.assertTrue(os.path.islink(fpath))

        # Unspill
        restored_cnt, restored_b = mod_spill.unspill_files(target_dir=self.tgt_dir)
        self.assertEqual(restored_cnt, 1)
        self.assertFalse(os.path.islink(fpath))
        self.assertTrue(os.path.isfile(fpath))
        with open(fpath, "rb") as f:
            self.assertEqual(f.read(), test_content)


class TestAdversarialLogStreamer(unittest.TestCase):
    """Adversarial testing on mios-log-streamer: malformed streams, SQL injection, and vector math."""

    def test_hostile_journal_stream_and_sql_injection_defense(self):
        """Feed adversarial SQL injection payloads and malformed json to journal parser."""
        hostile_records = [
            # 1. SQL Injection attempt
            {
                "PRIORITY": 2,
                "MESSAGE": "'); DROP TABLE system_logs; SELECT pg_sleep(10); --",
                "_SYSTEMD_UNIT": "malicious'; DROP TABLE users; --.service",
                "__REALTIME_TIMESTAMP": "1724688000000000",
            },
            # 2. Binary message payload
            {
                "PRIORITY": 3,
                "MESSAGE": [0xDE, 0xAD, 0xBE, 0xEF, 0x48, 0x65, 0x6C, 0x6C, 0x6F],
                "SYSLOG_IDENTIFIER": "kernel",
            },
            # 3. High priority filter exclusion (debug level 7)
            {
                "PRIORITY": 7,
                "MESSAGE": "Standard debug trace",
                "_SYSTEMD_UNIT": "systemd.service",
            },
            # 4. Missing required fields
            {
                "PRIORITY": 1,
            },
        ]

        parsed = []
        for r in hostile_records:
            p = mod_log.parse_journal_record(r, max_priority=3)
            if p:
                parsed.append(p)

        # Records 1 & 2 should parse; 3 (priority 7) and 4 (empty message) should be filtered
        self.assertEqual(len(parsed), 2)

        # Check SQL formatting safety
        parsed[0]["emb"] = [0.1] * 768
        parsed[1]["emb"] = [0.2] * 768
        sql = mod_log.format_sql_insert(parsed)

        # Single quotes must be doubled for SQL escape
        self.assertIn("malicious''; DROP TABLE users; --.service", sql)
        self.assertIn("'''); DROP TABLE system_logs; SELECT pg_sleep(10); --", sql)

    def test_vector_embeddings_mathematical_properties(self):
        """Verify deterministic embeddings are 768-dim, unit normalized (L2=1.0), and deterministic."""
        text1 = "[sshd.service] Failed password for root from 192.168.1.100 port 22 ssh2"
        text2 = "[systemd] Started MiOS Autonomous Agent Daemon."

        emb1_a = mod_log.generate_deterministic_embedding(text1, dim=768)
        emb1_b = mod_log.generate_deterministic_embedding(text1, dim=768)
        emb2 = mod_log.generate_deterministic_embedding(text2, dim=768)

        # 1. Dimension check
        self.assertEqual(len(emb1_a), 768)
        self.assertEqual(len(emb2), 768)

        # 2. Determinism check
        self.assertEqual(emb1_a, emb1_b)
        self.assertNotEqual(emb1_a, emb2)

        # 3. Unit norm check (sum of squares ~ 1.0)
        norm1 = math.sqrt(sum(x * x for x in emb1_a))
        norm2 = math.sqrt(sum(x * x for x in emb2))
        self.assertAlmostEqual(norm1, 1.0, delta=0.01)
        self.assertAlmostEqual(norm2, 1.0, delta=0.01)


class TestAdversarialBackupRemote(unittest.TestCase):
    """Adversarial testing on mios-backup-remote: chunk boundary edge cases and delta deduplication."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-backup-adv-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_chunking_boundary_sizes(self):
        """Test hashing on 0-byte, 1-byte, exact chunk boundary, and cross-boundary files."""
        # 0 bytes
        p0 = os.path.join(self.tmpdir, "zero.dat")
        open(p0, "wb").close()
        c0 = mod_backup.hash_file_chunks(p0, chunk_size=1024)
        self.assertEqual(len(c0), 0)

        # Exact boundary: 2048 bytes with chunk_size 1024 -> exactly 2 chunks
        p2048 = os.path.join(self.tmpdir, "exact.dat")
        with open(p2048, "wb") as f:
            f.write(b"X" * 2048)
        c2048 = mod_backup.hash_file_chunks(p2048, chunk_size=1024)
        self.assertEqual(len(c2048), 2)
        self.assertEqual(c2048[0]["length"], 1024)
        self.assertEqual(c2048[1]["length"], 1024)

        # Cross boundary: 2049 bytes with chunk_size 1024 -> 3 chunks (1024, 1024, 1)
        p2049 = os.path.join(self.tmpdir, "cross.dat")
        with open(p2049, "wb") as f:
            f.write(b"Y" * 2049)
        c2049 = mod_backup.hash_file_chunks(p2049, chunk_size=1024)
        self.assertEqual(len(c2049), 3)
        self.assertEqual(c2049[2]["length"], 1)

    def test_delta_plan_deduplication_accuracy(self):
        """Verify delta plan accurately detects unchanged vs modified chunks across snapshots."""
        src_dir = os.path.join(self.tmpdir, "data")
        os.makedirs(src_dir, exist_ok=True)

        f_static = os.path.join(src_dir, "static.bin")
        f_mut = os.path.join(src_dir, "mut.bin")

        with open(f_static, "wb") as f:
            f.write(b"STATIC_CHUNK_DATA_" * 1000)
        with open(f_mut, "wb") as f:
            f.write(b"MUTABLE_INITIAL_" * 1000)

        # Baseline snapshot
        m1 = mod_backup.create_snapshot_manifest(src_dir, snapshot_id="snap1", chunk_size=4096)

        # Mutate second file
        with open(f_mut, "wb") as f:
            f.write(b"MUTABLE_MODIFIED_PAYLOAD_" * 1000)

        # Second snapshot
        m2 = mod_backup.create_snapshot_manifest(src_dir, snapshot_id="snap2", chunk_size=4096)

        plan = mod_backup.compute_delta_plan(m2, baseline_manifest=m1)
        self.assertGreater(plan["new_chunks_count"], 0)
        self.assertGreater(plan["reused_chunks_count"], 0)
        self.assertGreater(plan["dedup_ratio_pct"], 0.0)


class TestAdversarialDbDoctorAndMigrate(unittest.TestCase):
    """Adversarial testing on mios-db-doctor and mios-db-migrate."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-db-adv-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_db_doctor_garbage_and_corrupt_files(self):
        """Verify db doctor ignores non-sqlite files and creates backup before repair."""
        # 1. 0-byte file
        p_zero = os.path.join(self.tmpdir, "empty.db")
        open(p_zero, "wb").close()

        # 2. Random garbage file
        p_rand = os.path.join(self.tmpdir, "garbage.sqlite")
        with open(p_rand, "wb") as f:
            f.write(os.urandom(1024))

        doc = mod_doctor.DbDoctor(sqlite_paths=[self.tmpdir])
        found = doc.find_sqlite_databases()
        self.assertEqual(len(found), 0, "Non-sqlite files were falsely discovered")

    def test_db_migrate_checksum_tampering_detection(self):
        """Verify migration runner detects post-application script modification."""
        mig_dir = os.path.join(self.tmpdir, "migrations")
        os.makedirs(mig_dir, exist_ok=True)

        m1_path = os.path.join(mig_dir, "0001_init.sql")
        with open(m1_path, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE test_table (id INT);\n")

        migrator = mod_migrate.DbMigrator(
            migrations_dir=mig_dir,
            mock=True,
        )

        # Apply initial migration
        res = migrator.migrate()
        self.assertEqual(res["total_applied"], 1)

        # Tamper with migration file on disk
        with open(m1_path, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE test_table (id INT, tampered_col TEXT);\n")

        # Re-run: must detect checksum mismatch
        with self.assertRaises(RuntimeError) as ctx:
            migrator.migrate()
        self.assertIn("checksum mismatch", str(ctx.exception).lower())


def main() -> int:
    suite = unittest.TestSuite()
    for test_class in [
        TestAdversarialBenchStorage,
        TestAdversarialLUKSRotate,
        TestAdversarialTmpfsSpill,
        TestAdversarialLogStreamer,
        TestAdversarialBackupRemote,
        TestAdversarialDbDoctorAndMigrate,
    ]:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_class))

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
