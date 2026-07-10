# AI-hint: stdlib unit test for mios_db_config resolver (AGY-9).
# Exercises the DB read path, precedence ordering, TOML fall-back, and shadow-compare divergences.
import sys
import os
# Ensure /usr/lib/mios and relative path are in python path
sys.path.insert(0, "/usr/lib/mios")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import psycopg
import mios_db_config

class TestMiosDbConfig(unittest.TestCase):

    def setUp(self):
        self.conn_str = "postgresql://mios:mios@localhost:8432/mios"
        # Reset divergence counter
        mios_db_config.reset_divergences()

    def test_is_db_authoritative(self):
        # Test env override
        os.environ["MIOS_DB_AUTHORITATIVE"] = "True"
        self.assertTrue(mios_db_config.is_db_authoritative())
        
        os.environ["MIOS_DB_AUTHORITATIVE"] = "False"
        self.assertFalse(mios_db_config.is_db_authoritative())
        
        del os.environ["MIOS_DB_AUTHORITATIVE"]

    def test_toml_fail_open(self):
        # Override connection port to invalid port to simulate db outage
        os.environ["MIOS_PORT_PGVECTOR"] = "9999"
        try:
            # Under db_authoritative=true, should fall back to TOML without raising
            os.environ["MIOS_DB_AUTHORITATIVE"] = "True"
            val = mios_db_config.get("ai", "kernel_dispatch")
            # Should match TOML value (True)
            self.assertTrue(val)
        finally:
            del os.environ["MIOS_PORT_PGVECTOR"]
            if "MIOS_DB_AUTHORITATIVE" in os.environ:
                del os.environ["MIOS_DB_AUTHORITATIVE"]

    def test_shadow_compare_divergence(self):
        # Temporarily insert a divergent value in the database config_kv
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # Ensure layer 3 config_layer exists
                cur.execute(
                    """
                    INSERT INTO config_layer (rank, name)
                    VALUES (3, 'machine')
                    ON CONFLICT (rank) DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('mcp', 'port', '11111'::jsonb, 3, 'Test machine layer override')
                    ON CONFLICT (scope, key, layer) DO UPDATE SET value = EXCLUDED.value
                    """
                )
            conn.commit()
            
        try:
            # Under db_authoritative = false (default), should shadow-compare and detect divergence
            os.environ["MIOS_DB_AUTHORITATIVE"] = "False"
            mios_db_config.reset_divergences()
            
            # Read mcp.port
            val = mios_db_config.get("mcp", "port")
            
            # Should return TOML value (not 11111)
            self.assertNotEqual(val, 11111)
            
            # Divergence counter should have incremented
            self.assertTrue(mios_db_config.get_divergences() > 0)
            
            # Now flip to db_authoritative = true, should return DB value (11111)
            os.environ["MIOS_DB_AUTHORITATIVE"] = "True"
            val_db = mios_db_config.get("mcp", "port")
            self.assertEqual(val_db, 11111)
            
        finally:
            # Clean up test row
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM config_kv WHERE scope = 'mcp' AND key = 'port' AND layer = 3")
                conn.commit()
            if "MIOS_DB_AUTHORITATIVE" in os.environ:
                del os.environ["MIOS_DB_AUTHORITATIVE"]

if __name__ == "__main__":
    unittest.main()
