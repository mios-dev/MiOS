# AI-hint: Standalone unit test for mios_toml.py overlay and DB authoritative fallbacks.
# AI-related: /usr/lib/mios/mios_toml.py
# AI-functions: TestMiosToml

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch

# Ensure /usr/lib/mios is in python path
sys.path.insert(0, "/usr/lib/mios")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mios_toml

class TestMiosToml(unittest.TestCase):
    def setUp(self):
        mios_toml.clear_cache()
        self.tmp_dir = tempfile.mkdtemp()
        self.vendor_file = os.path.join(self.tmp_dir, "vendor.toml")
        self.host_file = os.path.join(self.tmp_dir, "host.toml")
        self.user_file = os.path.join(self.tmp_dir, "user.toml")

        with open(self.vendor_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey1 = 'vendor_val'\nkey2 = 'vendor_val2'\n")

        with open(self.host_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey2 = 'host_val2'\nkey3 = 'host_val3'\n")

        # Mock env vars
        self.env_vars = {
            "MIOS_VENDOR_TOML": self.vendor_file,
            "MIOS_HOST_TOML": self.host_file,
            "MIOS_USER_TOML": self.user_file,
            "MIOS_VENDOR_TOML_D": os.path.join(self.tmp_dir, "nonexistent1"),
            "MIOS_HOST_TOML_D": os.path.join(self.tmp_dir, "nonexistent2"),
            "MIOS_USER_TOML_D": os.path.join(self.tmp_dir, "nonexistent3"),
        }
        self.orig_env = {k: os.environ.get(k) for k in self.env_vars}
        for k, v in self.env_vars.items():
            os.environ[k] = v

    def tearDown(self):
        mios_toml.clear_cache()
        for k, v in self.orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_merged(self):
        with open(self.user_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey3 = 'user_val3'\nkey4 = 'user_val4'\n")

        res = mios_toml.load_merged()
        self.assertEqual(res["section"]["key1"], "vendor_val")
        self.assertEqual(res["section"]["key2"], "host_val2")
        self.assertEqual(res["section"]["key3"], "user_val3")
        self.assertEqual(res["section"]["key4"], "user_val4")

    @patch("mios_db_config.is_db_authoritative", return_value=True)
    @patch("mios_db_config.load_db_config")
    def test_load_merged_db_authoritative_fallback(self, mock_load_db, mock_is_auth):
        # DB config overrides key3, key4 but is missing key1, key2!
        mock_load_db.return_value = {
            "section": {
                "key3": "db_val3",
                "key4": "db_val4"
            }
        }
        
        # User TOML also has key3
        with open(self.user_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey3 = 'user_val3'\n")

        res = mios_toml.load_merged()
        # key1 and key2 should fall back to files!
        self.assertEqual(res["section"]["key1"], "vendor_val")
        self.assertEqual(res["section"]["key2"], "host_val2")
        # key3 and key4 should be overridden by the DB!
        self.assertEqual(res["section"]["key3"], "db_val3")
        self.assertEqual(res["section"]["key4"], "db_val4")

    def test_cache_memoization_and_invalidation(self):
        # Initial load caches the result
        res1 = mios_toml.load_merged()
        
        # Manually modify user file behind its back
        with open(self.user_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey3 = 'sneaky_change'\n")
            
        # Loading again should return the cached value (not the sneaky change)
        res2 = mios_toml.load_merged()
        self.assertEqual(res1["section"].get("key3"), res2["section"].get("key3"))
        
        # After clear_cache(), it should load the sneaky change!
        mios_toml.clear_cache()
        res3 = mios_toml.load_merged()
        self.assertEqual(res3["section"].get("key3"), "sneaky_change")

if __name__ == "__main__":
    unittest.main()
