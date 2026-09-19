#!/usr/bin/env python3
# AI-hint: Consolidated database test suite: backup/retention, db doctor/corruption, migrations/rollback, SSOT materialization, PG events, streaming replica, autovacuum tuner, pgvector halfvec HNSW, and pgvector vacuum/reindexing.
# AI-related: usr/libexec/mios/db/, usr/lib/mios/ai/pgvector_hnsw.py, tests/test-db.py
"""Consolidated MiOS database tests (backup, doctor, migrate, ssot materialize, events, replica, vacuum, hnsw, optimize)."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))


# ======================================================================
# from tests/test-backup-pgvector.py
# ======================================================================
_BACKUP_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-backup-pgvector.py")
spec_backup = importlib.util.spec_from_file_location("backup_pgvector", _BACKUP_PATH)
if spec_backup and spec_backup.loader:
    backup_pgvector = importlib.util.module_from_spec(spec_backup)
    sys.modules[spec_backup.name] = backup_pgvector
    spec_backup.loader.exec_module(backup_pgvector)
else:
    raise ImportError(f"Could not load backup_pgvector module from {_BACKUP_PATH}")


class TestBackupPgVector(unittest.TestCase):
    """Validates backup filename format, mock snapshot generation, and 7-day retention rotation."""

    def test_backup_filename_format(self):
        filename = backup_pgvector.generate_backup_filename("mios_test")
        self.assertTrue(filename.startswith("mios_test_backup_"))
        self.assertTrue(filename.endswith(".sql.zst"))

    def test_mock_snapshot_generation_and_storage(self):
        with tempfile.TemporaryDirectory(prefix="mios-backup-test-") as tmpdir:
            out_path = backup_pgvector.execute_backup(
                db_name="test_agent_db",
                output_dir=tmpdir,
                mock=True,
            )
            self.assertTrue(os.path.isfile(out_path))
            self.assertGreater(os.path.getsize(out_path), 10)

    def test_rolling_retention_purge(self):
        with tempfile.TemporaryDirectory(prefix="mios-retention-test-") as tmpdir:
            # Create a recent backup
            recent_file = os.path.join(tmpdir, "mios_backup_recent.sql.zst")
            with open(recent_file, "wb") as f:
                f.write(b"RECENT_SNAPSHOT")

            # Create an old backup (10 days old)
            old_file = os.path.join(tmpdir, "mios_backup_old.sql.zst")
            with open(old_file, "wb") as f:
                f.write(b"OLD_SNAPSHOT")
            old_time = time.time() - (10 * 86400)
            os.utime(old_file, (old_time, old_time))

            # Enforce 7-day retention
            deleted = backup_pgvector.enforce_retention(output_dir=tmpdir, retention_days=7)
            self.assertEqual(len(deleted), 1)
            self.assertEqual(deleted[0], old_file)
            self.assertFalse(os.path.exists(old_file))
            self.assertTrue(os.path.exists(recent_file))


# ======================================================================
# from tests/test-db-doctor.py
# ======================================================================
_DOCTOR_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-db-doctor.py")
spec_doctor = importlib.util.spec_from_file_location("db_doctor", _DOCTOR_PATH)
if spec_doctor and spec_doctor.loader:
    db_doctor = importlib.util.module_from_spec(spec_doctor)
    sys.modules[spec_doctor.name] = db_doctor
    spec_doctor.loader.exec_module(db_doctor)
else:
    raise ImportError(f"Could not load db_doctor module from {_DOCTOR_PATH}")


class TestDbDoctor(unittest.TestCase):
    """Validates SQLite and PostgreSQL integrity checking and non-destructive repair logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-db-doctor-test-")
        self.doctor = db_doctor.DbDoctor(
            sqlite_paths=[self.tmpdir],
            pg_data_dir=os.path.join(self.tmpdir, "pgdata"),
            mock=False,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_healthy_sqlite(self, filename: str = "healthy.sqlite") -> str:
        path = os.path.join(self.tmpdir, filename)
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
        cursor.execute("CREATE INDEX idx_users_name ON users(name);")
        cursor.executemany("INSERT INTO users (name) VALUES (?);", [("alice",), ("bob",), ("charlie",)])
        conn.commit()
        conn.close()
        return path

    def test_sqlite_discovery(self):
        db1 = self._create_healthy_sqlite("app1.db")
        db2 = self._create_healthy_sqlite("app2.sqlite")
        with open(os.path.join(self.tmpdir, "notes.txt"), "w") as f:
            f.write("just text")

        found = self.doctor.find_sqlite_databases()
        self.assertEqual(len(found), 2)
        self.assertIn(os.path.abspath(db1), found)
        self.assertIn(os.path.abspath(db2), found)

    def test_sqlite_healthy_check(self):
        db = self._create_healthy_sqlite("valid.sqlite3")
        res = self.doctor.check_sqlite_db(db)
        self.assertEqual(res["status"], "healthy")
        self.assertEqual(res["quick_check"], "ok")
        self.assertEqual(res["integrity_check"], "ok")
        self.assertEqual(len(res["errors"]), 0)

    def test_sqlite_healthy_repair_invariant(self):
        """Invariant check: Do NOT run destructive recovery over healthy databases."""
        db = self._create_healthy_sqlite("valid_untouched.db")
        before_mtime = os.path.getmtime(db)
        repair_res = self.doctor.repair_sqlite_db(db, force_dump=False)
        self.assertEqual(repair_res["status"], "healthy")
        self.assertEqual(repair_res["action"], "none_needed")
        self.assertIn("skipping repair", repair_res["message"])

    def test_sqlite_corrupt_detection_and_repair(self):
        db = self._create_healthy_sqlite("corrupt_test.db")
        # Corrupt table page 2 by overwriting b-tree page header
        with open(db, "r+b") as f:
            f.seek(4096)
            f.write(b"\xFF\xFE\xFD\xFC" * 64)

        check_res = self.doctor.check_sqlite_db(db)
        self.assertEqual(check_res["status"], "corrupt")
        self.assertGreater(len(check_res["errors"]), 0)

        repair_res = self.doctor.repair_sqlite_db(db)
        self.assertIn(repair_res["status"], ("repaired", "unrecoverable"))
        self.assertTrue(os.path.exists(repair_res["backup_path"]))

    def test_postgres_diagnostics_mock(self):
        mock_doctor = db_doctor.DbDoctor(
            sqlite_paths=[self.tmpdir],
            pg_data_dir=os.path.join(self.tmpdir, "pgdata"),
            mock=True,
        )
        pg_check = mock_doctor.check_postgres()
        self.assertEqual(pg_check["status"], "healthy")
        self.assertEqual(pg_check["corrupted_blocks"], 0)

        pg_repair = mock_doctor.repair_postgres()
        self.assertEqual(pg_repair["status"], "repaired")
        self.assertEqual(pg_repair["action"], "reindex_database")

    def test_overall_diagnostics_report(self):
        self._create_healthy_sqlite("sys.sqlite")
        mock_doctor = db_doctor.DbDoctor(
            sqlite_paths=[self.tmpdir],
            pg_data_dir=os.path.join(self.tmpdir, "pgdata"),
            mock=True,
        )
        report = mock_doctor.run_diagnostics(repair=False, db_type="all")
        self.assertEqual(report["overall_status"], "healthy")
        self.assertEqual(report["mode"], "check")
        self.assertIn("sqlite_databases", report)
        self.assertIn("postgres", report)


# ======================================================================
# from tests/test-db-migrate.py
# ======================================================================
_MIGRATE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-db-migrate.py")
spec_migrate = importlib.util.spec_from_file_location("db_migrate", _MIGRATE_PATH)
if spec_migrate and spec_migrate.loader:
    db_migrate = importlib.util.module_from_spec(spec_migrate)
    sys.modules[spec_migrate.name] = db_migrate
    spec_migrate.loader.exec_module(db_migrate)
else:
    raise ImportError(f"Could not load db_migrate module from {_MIGRATE_PATH}")


class TestDbMigrate(unittest.TestCase):
    """Validates migration discovery, SHA-256 hashing, transactional application, and rollback handling."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-db-migrate-test-")
        self._create_sample_migrations()
        self.migrator = db_migrate.DbMigrator(
            migrations_dir=self.tmpdir,
            db_name="test_mios",
            mock=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_sample_migrations(self):
        m1 = os.path.join(self.tmpdir, "0001_init.sql")
        with open(m1, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE users (id serial primary key, name text);")

        m2 = os.path.join(self.tmpdir, "0002_add_index.sql")
        with open(m2, "w", encoding="utf-8") as f:
            f.write("CREATE INDEX idx_users_name ON users(name);")

    def test_load_migrations_and_checksum(self):
        migrations = self.migrator.load_migrations()
        self.assertEqual(len(migrations), 2)
        self.assertEqual(migrations[0].version, 1)
        self.assertEqual(migrations[0].name, "init")
        self.assertEqual(migrations[1].version, 2)
        self.assertEqual(migrations[1].name, "add_index")
        for m in migrations:
            self.assertEqual(len(m.checksum), 64)

    def test_initial_pending_status(self):
        status = self.migrator.check_status()
        self.assertEqual(len(status), 2)
        self.assertEqual(status[0]["state"], "pending")
        self.assertEqual(status[1]["state"], "pending")
        self.assertIsNone(status[0]["recorded_checksum"])

    def test_migration_application_and_ledger_recording(self):
        """Invariant check: Every applied migration MUST record version ID and SHA-256 checksum."""
        report = self.migrator.migrate()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["total_applied"], 2)

        post_status = self.migrator.check_status()
        self.assertEqual(len(post_status), 2)
        for s in post_status:
            self.assertEqual(s["state"], "applied")
            self.assertIsNotNone(s["recorded_checksum"])
            self.assertEqual(s["checksum"], s["recorded_checksum"])

    def test_checksum_mismatch_detection(self):
        """Detects if a previously applied migration script was modified post-application."""
        self.migrator.migrate()

        m1 = os.path.join(self.tmpdir, "0001_init.sql")
        with open(m1, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE users (id serial primary key, name text, TAMPERED text);")

        status = self.migrator.check_status()
        self.assertEqual(status[0]["state"], "checksum_mismatch")

        with self.assertRaises(RuntimeError) as ctx:
            self.migrator.migrate()
        self.assertIn("checksum mismatch", str(ctx.exception).lower())

    def test_transaction_rollback_on_failure(self):
        """Invariant check: Migration errors must trigger transaction rollback."""
        m3_bad = os.path.join(self.tmpdir, "0003_bad_migration.sql")
        with open(m3_bad, "w", encoding="utf-8") as f:
            f.write("SYNTAX_ERROR_IN_MIGRATION; INVALID SQL BLOCK;")

        with self.assertRaises(RuntimeError) as ctx:
            self.migrator.migrate()
        self.assertIn("ROLLED BACK", str(ctx.exception))

        applied = self.migrator.get_applied_migrations()
        self.assertNotIn(3, applied)

    def test_dry_run_mode(self):
        dry_migrator = db_migrate.DbMigrator(
            migrations_dir=self.tmpdir,
            db_name="test_mios",
            dry_run=True,
            mock=True,
        )
        report = dry_migrator.migrate()
        self.assertEqual(report["status"], "completed")
        for detail in report["applied_details"]:
            self.assertEqual(detail["status"], "dry_run")

        status = dry_migrator.check_status()
        for s in status:
            self.assertEqual(s["state"], "pending")

    def test_real_repo_migrations(self):
        """Verifies the actual migrations in usr/share/mios/postgres/migrations/ parse cleanly."""
        repo_migrations_dir = os.path.join(_ROOT, "usr", "share", "mios", "postgres", "migrations")
        real_migrator = db_migrate.DbMigrator(
            migrations_dir=repo_migrations_dir,
            db_name="mios",
            mock=True,
        )
        migrations = real_migrator.load_migrations()
        self.assertGreaterEqual(len(migrations), 3)
        versions = [m.version for m in migrations]
        self.assertEqual(versions, sorted(versions))
        report = real_migrator.migrate()
        self.assertEqual(report["status"], "completed")
        self.assertGreaterEqual(report["total_applied"], 3)


# ======================================================================
# from tests/test-db-ssot-materialize.py
# ======================================================================
_MAT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "materialize-config-toml.py")
spec_mat = importlib.util.spec_from_file_location("materialize_config_toml", _MAT_PATH)
if spec_mat and spec_mat.loader:
    mat = importlib.util.module_from_spec(spec_mat)
    sys.modules[spec_mat.name] = mat
    spec_mat.loader.exec_module(mat)
else:
    raise ImportError(f"Could not load materialize-config-toml module from {_MAT_PATH}")


class TestDBSSOTMaterialize(unittest.TestCase):
    """Validates TOML key escaping, value formatting, list/dict serialization, and integrity."""

    def test_key_escaping(self):
        self.assertEqual(mat.escape_toml_key("simple_key"), "simple_key")
        self.assertEqual(mat.escape_toml_key("hyphen-key-123"), "hyphen-key-123")
        self.assertEqual(mat.escape_toml_key("dotted.key"), '"dotted.key"')
        self.assertEqual(mat.escape_toml_key("space key"), '"space key"')

    def test_value_formatting(self):
        self.assertEqual(mat.format_toml_value(True), "true")
        self.assertEqual(mat.format_toml_value(False), "false")
        self.assertEqual(mat.format_toml_value(8600), "8600")
        self.assertEqual(mat.format_toml_value("test_val"), '"test_val"')
        self.assertEqual(mat.format_toml_value(["a", "b", 123]), '["a", "b", 123]')
        self.assertEqual(mat.format_toml_value({"port": 8640, "host": "127.0.0.1"}), '{host = "127.0.0.1", port = 8640}')


# ======================================================================
# from tests/test-pg-events.py
# ======================================================================
_AGENT_PIPE_DIR = os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe")
if _AGENT_PIPE_DIR not in sys.path:
    sys.path.insert(0, _AGENT_PIPE_DIR)
from mios_pg_events import EventBus, AgentEvent


class TestPgEvents(unittest.TestCase):
    """Tests for T-342: mios_pg_events -- PostgreSQL LISTEN/NOTIFY event bus."""

    def test_inject_and_dispatch(self):
        """Injected events are dispatched to subscribers within SLA."""
        bus = EventBus(dry_run=True)
        received = []

        async def handler(evt: AgentEvent):
            received.append(evt)

        bus.subscribe(handler)
        bus.inject({"table": "tasks", "op": "INSERT", "row_id": 42})
        events = asyncio.run(bus.run_once(timeout_s=0.1))
        self.assertEqual(len(events), 1)
        self.assertEqual(received[0].payload["table"], "tasks")
        self.assertEqual(received[0].payload["row_id"], 42)

    def test_multiple_subscribers(self):
        """Multiple handlers all receive each event."""
        bus = EventBus(dry_run=True)
        counts = [0, 0]

        async def h1(evt):
            counts[0] += 1

        async def h2(evt):
            counts[1] += 1

        bus.subscribe(h1)
        bus.subscribe(h2)
        bus.inject({"op": "NOTIFY"})
        asyncio.run(bus.run_once())
        self.assertEqual(counts, [1, 1], f"Expected [1,1] got {counts}")

    def test_no_events_returns_empty(self):
        """run_once() with no injected events returns empty list quickly."""
        bus = EventBus(dry_run=True)
        events = asyncio.run(bus.run_once(timeout_s=0.05))
        self.assertEqual(events, [])


# ======================================================================
# from tests/test-pg-replica.py
# ======================================================================
_REPLICA_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-pg-replica.py")
spec_replica = importlib.util.spec_from_file_location("pg_replica", _REPLICA_PATH)
if spec_replica and spec_replica.loader:
    pg_replica = importlib.util.module_from_spec(spec_replica)
    sys.modules[spec_replica.name] = pg_replica
    spec_replica.loader.exec_module(pg_replica)
else:
    raise ImportError(f"Could not load pg_replica module from {_REPLICA_PATH}")


class TestPgReplica(unittest.TestCase):
    """Validates replication provisioning, WAL lag calculation, fencing enforcement, and promotion."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios-pg-replica-test-")
        self.data_dir = os.path.join(self.tmpdir, "data")
        self.fence_dir = os.path.join(self.tmpdir, "fencing")
        self.manager = pg_replica.PgReplicaManager(
            primary_host="10.0.0.1",
            primary_port=5432,
            replica_host="10.0.0.2",
            replica_port=5432,
            slot_name="test_slot",
            data_dir=self.data_dir,
            fence_dir=self.fence_dir,
            max_lag_ms=50.0,
            mock=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_provision_replica(self):
        res = self.manager.provision_replica()
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["primary_conninfo_written"])
        standby_signal = os.path.join(self.data_dir, "standby.signal")
        auto_conf = os.path.join(self.data_dir, "postgresql.auto.conf")
        self.assertTrue(os.path.isfile(standby_signal))
        self.assertTrue(os.path.isfile(auto_conf))
        with open(auto_conf, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("10.0.0.1", content)
            self.assertIn("test_slot", content)

    def test_replication_status_and_lag(self):
        status = self.manager.get_replication_status()
        self.assertEqual(status["status"], "active")
        self.assertTrue(status["is_healthy"])
        self.assertLessEqual(status["lag_ms"], 50.0)
        self.assertEqual(status["sync_state"], "streaming")

    def test_health_check_within_threshold(self):
        health = self.manager.health_check()
        self.assertTrue(health["healthy"])
        self.assertIn("healthy", health["reason"])

    def test_fencing_primary(self):
        self.assertFalse(self.manager.is_primary_fenced())
        fence_record = self.manager.fence_primary(reason="planned_failover")
        self.assertEqual(fence_record["status"], "fenced")
        self.assertTrue(self.manager.is_primary_fenced())

        ok = self.manager.unfence_primary()
        self.assertTrue(ok)
        self.assertFalse(self.manager.is_primary_fenced())

    def test_promotion_blocked_when_unfenced(self):
        """Invariant check: Promotion MUST fail if primary is not fenced (split-brain prevention)."""
        self.manager.unfence_primary()
        self.assertFalse(self.manager.is_primary_fenced())

        with self.assertRaises(RuntimeError) as ctx:
            self.manager.promote_replica(force_unfenced=False)
        self.assertIn("Old primary is NOT fenced", str(ctx.exception))

    def test_promotion_succeeds_when_fenced(self):
        self.manager.provision_replica()
        self.manager.fence_primary()
        self.assertTrue(self.manager.is_primary_fenced())

        res = self.manager.promote_replica(force_unfenced=False)
        self.assertEqual(res["status"], "promoted")
        self.assertTrue(res["primary_fenced"])

    def test_promotion_force_unfenced_override(self):
        self.manager.provision_replica()
        self.manager.unfence_primary()
        res = self.manager.promote_replica(force_unfenced=True)
        self.assertEqual(res["status"], "promoted")


# ======================================================================
# from tests/test-pg-vacuum.py
# ======================================================================
_DB_LIBEXEC_DIR = os.path.join(_ROOT, "usr", "libexec", "mios", "db")
if _DB_LIBEXEC_DIR not in sys.path:
    sys.path.insert(0, _DB_LIBEXEC_DIR)
from pg_vacuum_tuner import PGVacuumTuner


class TestPGVacuumTuner(unittest.TestCase):
    """Unit tests for MiOS PostgreSQL autovacuum tuner and pg_cron HNSW reindexer."""

    def setUp(self):
        self.tuner = PGVacuumTuner(dry_run=True)

    def test_render_pg_conf(self):
        conf = self.tuner.render_pg_conf()
        self.assertIn("autovacuum = on", conf)
        self.assertIn("autovacuum_vacuum_scale_factor = 0.05", conf)
        self.assertIn("wal_compression = 'zstd'", conf)
        self.assertIn("max_parallel_maintenance_workers = 4", conf)

    def test_render_pg_cron_reindex_sql(self):
        sql = self.tuner.render_pg_cron_reindex_sql()
        self.assertIn("REINDEX TABLE CONCURRENTLY", sql)
        self.assertIn("system_logs_rag", sql)
        self.assertIn("agent_memories", sql)
        self.assertIn("0 3 * * *", sql)


# ======================================================================
# from tests/test-pgvector-hnsw.py
# ======================================================================
_AI_LIB_DIR = os.path.join(_ROOT, "usr", "lib", "mios", "ai")
if _AI_LIB_DIR not in sys.path:
    sys.path.insert(0, _AI_LIB_DIR)
from pgvector_hnsw import MAX_KNN_SEARCH_MS, MIN_RECALL_ACCURACY_PCT, PgVectorHNSWManager


class TestPgVectorHNSW(unittest.TestCase):
    """Automated unit test suite for MiOS PgVector HNSW Manager."""

    def setUp(self):
        self.mgr = PgVectorHNSWManager(dry_run=True)

    def test_schema_sql_specifies_halfvec_and_partitioning(self):
        """Test generated SQL uses halfvec(1536) and partitioned tables."""
        sql = self.mgr.generate_partition_schema_sql()
        self.assertIn("halfvec(1536)", sql)
        self.assertIn("PARTITION BY LIST", sql)
        self.assertIn("USING hnsw", sql)

    def test_sub_5ms_knn_search_latency_and_high_recall(self):
        """Test kNN search executes in <5ms with >98% recall accuracy."""
        res = self.mgr.execute_knn_query("test_vec_01", k=10)
        self.assertLess(res.search_latency_ms, MAX_KNN_SEARCH_MS)
        self.assertGreaterEqual(res.recall_accuracy_pct, MIN_RECALL_ACCURACY_PCT)
        self.assertGreaterEqual(res.memory_reduction_pct, 70.0)


# ======================================================================
# from tests/test-pgvector-optimize.py
# ======================================================================
_OPTIMIZE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-pgvector-optimize.py")
spec_optimize = importlib.util.spec_from_file_location("pgvector_optimize", _OPTIMIZE_PATH)
if spec_optimize and spec_optimize.loader:
    pgvector_optimize = importlib.util.module_from_spec(spec_optimize)
    sys.modules[spec_optimize.name] = pgvector_optimize
    spec_optimize.loader.exec_module(pgvector_optimize)
else:
    raise ImportError(f"Could not load pgvector_optimize module from {_OPTIMIZE_PATH}")


class TestPgVectorOptimize(unittest.TestCase):
    """Validates dead tuple statistics retrieval, concurrent index reindexing, and full optimization cycle."""

    def setUp(self):
        self.optimizer = pgvector_optimize.PgVectorOptimizer(
            db="mios",
            host="127.0.0.1",
            port=5432,
            user="postgres",
            parallel=4,
            dry_run=False,
            mock=True,
        )

    def test_dead_tuple_discovery(self):
        stats = self.optimizer.get_dead_tuples()
        self.assertIsInstance(stats, list)
        self.assertGreater(len(stats), 0)
        table_names = [s["table_name"] for s in stats]
        self.assertIn("knowledge", table_names)
        self.assertIn("agent_memory", table_names)
        for entry in stats:
            self.assertIn("live_tuples", entry)
            self.assertIn("dead_tuples", entry)
            self.assertIn("dead_tuple_pct", entry)

    def test_vector_index_discovery(self):
        indexes = self.optimizer.get_vector_indexes()
        self.assertIsInstance(indexes, list)
        self.assertGreater(len(indexes), 0)
        index_names = [i["index_name"] for i in indexes]
        self.assertIn("knowledge_emb_hnsw", index_names)
        self.assertIn("agent_memory_emb_hnsw", index_names)
        for idx in indexes:
            self.assertEqual(idx["index_type"], "hnsw")
            self.assertGreater(idx["index_bytes"], 0)

    def test_vacuum_analyze_tables(self):
        results = self.optimizer.vacuum_analyze_tables(["knowledge", "agent_memory"])
        self.assertEqual(len(results), 2)
        for res in results:
            self.assertEqual(res["status"], "success")
            self.assertIn("VACUUM (ANALYZE, PARALLEL 4)", res["command"])
            self.assertIsNone(res["error"])

    def test_concurrent_reindex_invariant(self):
        """Invariant check: Reindex operations MUST be CONCURRENT to avoid blocking read queries."""
        results = self.optimizer.reindex_vector_indexes_concurrently()
        self.assertGreater(len(results), 0)
        for res in results:
            self.assertEqual(res["status"], "success")
            self.assertTrue(
                res["command"].startswith("REINDEX INDEX CONCURRENTLY "),
                f"Command '{res['command']}' violates non-blocking concurrency invariant!",
            )

    def test_full_optimization_report(self):
        report = self.optimizer.optimize()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["database"], "mios")
        self.assertGreater(report["tables_vacuumed"], 0)
        self.assertGreater(report["indexes_reindexed"], 0)
        self.assertIn("dead_tuple_stats", report)
        self.assertIn("total_elapsed_ms", report)

    def test_dry_run_mode(self):
        dry_optimizer = pgvector_optimize.PgVectorOptimizer(
            db="mios",
            host="127.0.0.1",
            port=5432,
            user="postgres",
            parallel=2,
            dry_run=True,
            mock=True,
        )
        report = dry_optimizer.optimize()
        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["dry_run"])
        for v in report["vacuum_details"]:
            self.assertEqual(v["status"], "dry_run")
        for r in report["reindex_details"]:
            self.assertEqual(r["status"], "dry_run")


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
