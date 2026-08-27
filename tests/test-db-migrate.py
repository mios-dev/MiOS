#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-412 (WS-DURA transactional database schema migration runner and rollback safety).
# AI-related: usr/libexec/mios/db/mios-db-migrate.py, usr/share/mios/postgres/migrations/
"""Automated tests for schema migration loading, SHA-256 ledger recording, and rollback on error."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MIGRATE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-db-migrate.py")

spec = importlib.util.spec_from_file_location("db_migrate", _MIGRATE_PATH)
if spec and spec.loader:
    db_migrate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = db_migrate
    spec.loader.exec_module(db_migrate)
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
            self.assertEqual(len(m.checksum), 64)  # SHA-256 hex string

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

        # Check status after migration
        post_status = self.migrator.check_status()
        self.assertEqual(len(post_status), 2)
        for s in post_status:
            self.assertEqual(s["state"], "applied")
            self.assertIsNotNone(s["recorded_checksum"])
            self.assertEqual(s["checksum"], s["recorded_checksum"])

    def test_checksum_mismatch_detection(self):
        """Detects if a previously applied migration script was modified post-application."""
        self.migrator.migrate()

        # Modify on-disk file for migration 1
        m1 = os.path.join(self.tmpdir, "0001_init.sql")
        with open(m1, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE users (id serial primary key, name text, TAMPERED text);")

        status = self.migrator.check_status()
        self.assertEqual(status[0]["state"], "checksum_mismatch")

        # Running migrate() should halt with error
        with self.assertRaises(RuntimeError) as ctx:
            self.migrator.migrate()
        self.assertIn("checksum mismatch", str(ctx.exception).lower())

    def test_transaction_rollback_on_failure(self):
        """Invariant check: Migration errors must trigger transaction rollback."""
        # Add a bad migration with intentional error
        m3_bad = os.path.join(self.tmpdir, "0003_bad_migration.sql")
        with open(m3_bad, "w", encoding="utf-8") as f:
            f.write("SYNTAX_ERROR_IN_MIGRATION; INVALID SQL BLOCK;")

        with self.assertRaises(RuntimeError) as ctx:
            self.migrator.migrate()
        self.assertIn("ROLLED BACK", str(ctx.exception))

        # Ensure migration 3 was not recorded as applied in ledger
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

        # Database should still show migrations as pending
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

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDbMigrate)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
