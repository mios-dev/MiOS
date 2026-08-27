#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-DURA automated PostgreSQL+pgvector backup and retention.
# AI-related: usr/libexec/mios/db/mios-backup-pgvector.py, usr/lib/systemd/system/mios-backup-pgvector.service
"""Automated tests for WS-DURA automated pgvector zstd backup generation and retention rotation."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_BACKUP_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "db", "mios-backup-pgvector.py")

spec = importlib.util.spec_from_file_location("backup_pgvector", _BACKUP_PATH)
if spec and spec.loader:
    backup_pgvector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backup_pgvector
    spec.loader.exec_module(backup_pgvector)
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

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBackupPgVector)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
