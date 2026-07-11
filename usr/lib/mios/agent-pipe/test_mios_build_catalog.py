import unittest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
import os
import json
import sys

# Import the modules by adding their directories to path
sys.path.insert(0, "/mnt/c/MiOS/usr/libexec/mios")


def setUpModule():
    # Test hermeticity (AGY-35): self-skip when no live pgvector so the
    # offline build gate reports SKIP (not FAIL/ERROR) while still running in CI.
    try:
        import psycopg
    except ImportError:
        raise unittest.SkipTest("no live pgvector -- integration test")
    port = os.environ.get("MIOS_PORT_PGVECTOR", "8432")
    dsn = f"postgresql://mios:mios@localhost:{port}/mios"
    try:
        with psycopg.connect(dsn, connect_timeout=1):
            pass
    except Exception:
        raise unittest.SkipTest("no live pgvector -- integration test")


class TestMiosBuildCatalog(unittest.TestCase):

    def test_seeding_and_materializing(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        toml_data = {
            "packages": {
                "sections": ["base", "repos"],
                "base": {
                    "pkgs": ["firewalld", "audit"]
                },
                "repos": {
                    "pkgs": ["dnf"]
                }
            }
        }
        mock_tomllib = MagicMock()
        mock_tomllib.load.return_value = toml_data
        sys.modules["tomllib"] = mock_tomllib
        sys.modules["tomli"] = mock_tomllib
        
        import importlib
        seed = importlib.import_module("seed-db-config")
        
        with patch("psycopg.connect") as mock_connect, \
             patch("builtins.open", mock_open()), \
             patch("os.path.isfile", return_value=True), \
             patch("os.path.isdir", return_value=True), \
             patch("os.listdir", return_value=["01-repos.sh", "02-kernel.sh", "firstboot"]):
            
            mock_connect.return_value.__enter__.return_value = mock_conn
            
            res = seed.main()
            self.assertEqual(res, 0)
            
            calls = [c[0][0] for c in mock_cur.execute.call_args_list]
            self.assertTrue(any("INSERT INTO package_set" in sql for sql in calls))
            self.assertTrue(any("INSERT INTO build_phase" in sql for sql in calls))

    @patch("psycopg.connect")
    @patch("os.makedirs")
    def test_materialization(self, mock_makedirs, mock_connect):
        import importlib
        mat = importlib.import_module("materialize-build-ctx")
        
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        mock_cur.fetchall.side_effect = [
            [{"name": "base", "section": "packages", "pkgs": '["audit"]', "enable": True, "layer": 0, "base_image_ref": None}],
            [{"ordinal": 1, "script": "01-repos.sh", "stage": "container", "deps": '[]'}],
            [{"name": "p1", "policy_type": "type1", "rules": '[]'}],
            [{"name": "prof1", "description": "desc1"}],
            [{"name": "preset1", "description": "desc2", "features": '[]', "debloat_profile_name": "prof1"}]
        ]
        
        written_files = {}
        def mock_open_impl(path, mode="r", encoding=None):
            m = mock_open()()
            def write_impl(data):
                k = os.path.basename(path)
                written_files[k] = written_files.get(k, "") + data
            m.write.side_effect = write_impl
            return m
            
        with patch("builtins.open", mock_open_impl), \
             patch.dict(os.environ, {"MIOS_BUILD_CTX": "/tmp/ctx_test"}):
            
            res = mat.main()
            self.assertEqual(res, 0)
            
            self.assertIn("package_sets.json", written_files)
            self.assertIn("build_phases.json", written_files)
            self.assertIn("debloat_profiles.json", written_files)
            
            package_sets = json.loads(written_files["package_sets.json"])
            self.assertEqual(package_sets[0]["name"], "base")
            self.assertEqual(package_sets[0]["pkgs"], ["audit"])

if __name__ == "__main__":
    unittest.main()
