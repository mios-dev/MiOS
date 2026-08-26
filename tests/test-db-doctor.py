#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-407 (WS-DURA database corruption detector and automated doctor).
# AI-related: usr/libexec/mios/db/mios-db-doctor.py, usr/lib/greenboot/check/required.d/55-mios-db-check.sh
"""Automated tests for SQLite and PostgreSQL corruption detection, integrity checks, and repair."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_DOCTOR_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-db-doctor.py")

spec = importlib.util.spec_from_file_location("db_doctor", _DOCTOR_PATH)
if spec and spec.loader:
    db_doctor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = db_doctor
    spec.loader.exec_module(db_doctor)
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
        # Non-sqlite file
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

        # Should detect corruption
        check_res = self.doctor.check_sqlite_db(db)
        self.assertEqual(check_res["status"], "corrupt")
        self.assertGreater(len(check_res["errors"]), 0)

        # Attempt repair
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


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDbDoctor)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
