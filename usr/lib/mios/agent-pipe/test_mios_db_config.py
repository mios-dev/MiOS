# AI-hint: stdlib unit test for mios_db_config resolver (AGY-9).
# Exercises the DB read path, precedence ordering, TOML fall-back, and shadow-compare divergences.
# WS-A2 compliance: Sibling test present and free of server.py imports.
import sys
import os
import unittest
from unittest.mock import patch
# Ensure /usr/lib/mios and relative path are in python path
sys.path.insert(0, "/usr/lib/mios")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import psycopg
except ImportError:
    psycopg = None
import mios_db_config

def setUpModule():
    # Test hermeticity (AGY-35): self-skip when no live pgvector so the
    # offline build gate reports SKIP (not FAIL/ERROR) while still running in CI.
    if psycopg is None:
        raise unittest.SkipTest("no live pgvector -- integration test")
    port = os.environ.get("MIOS_PORT_PGVECTOR", "8432")
    conn_str = f"postgresql://mios:mios@localhost:{port}/mios"
    try:
        with psycopg.connect(conn_str, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(1) FROM verb")
                if cur.fetchone()[0] == 0:
                    raise unittest.SkipTest("no seeded pgvector -- integration test")
    except Exception:
        raise unittest.SkipTest("no live pgvector -- integration test")

class TestMiosDbConfig(unittest.TestCase):

    def setUp(self):
        self.conn_str = "postgresql://mios:mios@localhost:8432/mios"
        # Reset divergence counter and clear cache
        mios_db_config.clear_cache()
        mios_db_config.reset_divergences()

    def test_is_db_authoritative(self):
        # Test env override
        os.environ["MIOS_DB_AUTHORITATIVE"] = "True"
        mios_db_config.clear_cache()
        self.assertTrue(mios_db_config.is_db_authoritative())
        
        os.environ["MIOS_DB_AUTHORITATIVE"] = "False"
        mios_db_config.clear_cache()
        self.assertFalse(mios_db_config.is_db_authoritative())
        
        del os.environ["MIOS_DB_AUTHORITATIVE"]
        mios_db_config.clear_cache()

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

    def test_health_logic_divergences(self):
        class MockApp:
            version = "test-version"
        
        import mios_pipe.kernel.clusterhealth as ch
        
        ch.configure(
            app=MockApp(),
            BACKEND="http://localhost:8000",
            BACKEND_MODEL="test-model",
            ROUTER_ENABLED=False,
            ROUTER_MODEL="test-router",
            ROUTER_ENDPOINT="test-ep",
            PLANNER_ENABLED=False,
            PLANNER_MODEL="test-planner",
            PLANNER_ENDPOINT="test-ep",
            PLANNER_MAX_NODES=3,
            PLANNER_REFLEXION_CAP=3,
            DCI_ENABLED=False,
            DCI_MODEL="test-dci",
            DCI_ENDPOINT="test-ep",
            _DCI_ACTS=[],
            DCI_FLOW_ENABLED=False,
            DCI_FLOW_R_MAX=3,
            _DCI_PERSONAS=[],
            DCI_FLOW_TRIGGER_CONF=0.5,
            _ALLOWLIST_HOSTS={"localhost", "127.0.0.1"},
            _HIGH_PRIVILEGE_VERBS={"shell_exec"},
            _HIGH_PRIVILEGE_CURATED={"shell_exec"},
            _toml_section=lambda s: {},
            _TAINT_VERBS={"web_extract"},
            SKILLS_ENABLED=False,
            SKILLS_MIN_LENGTH=0,
            SKILLS_MAX_LENGTH=0,
            SKILLS_MIN_SUPPORT=0,
            SKILLS_WINDOW_HOURS=0,
            SKILLS_AUTO_PROMOTE_THRESHOLD=0,
            PASSPORT_ENABLE=False,
            PASSPORT_ALGO="RS256",
            PASSPORT_AGENT_NAME="test",
            PASSPORT_KEY_DIR="/test",
            PASSPORT_VERIFY_ON_READ=False,
            _passport_load_priv=lambda: None,
            _passport_kid=lambda: None,
            REFINE_ENABLED=False,
            REFINE_MODEL="test",
            REFINE_ENDPOINT="test",
            REFINE_BYPASS_CHARS=0,
            POLISH_ENABLED=False,
            POLISH_MODEL="test",
            POLISH_ENDPOINT="test",
            _AGENT_REGISTRY={},
            _agent_lane=lambda a: "gpu",
            LAUNCHER_SOCK="/test.sock",
            DB_URL="postgresql://test",
            PORT=8640,
        )
        
        mios_db_config.reset_divergences()
        
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
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
                    VALUES ('mcp', 'port', '22222'::jsonb, 3, 'Divergent Test')
                    ON CONFLICT (scope, key, layer) DO UPDATE SET value = EXCLUDED.value
                    """
                )
            conn.commit()
            
        try:
            os.environ["MIOS_DB_AUTHORITATIVE"] = "False"
            _ = mios_db_config.get("mcp", "port")
            
            import asyncio
            res = asyncio.run(ch.health_logic())
            
            self.assertIn("config_divergences", res)
            self.assertEqual(res["config_divergences"], mios_db_config.get_divergences())
            self.assertTrue(res["config_divergences"] > 0)
        finally:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM config_kv WHERE scope = 'mcp' AND key = 'port' AND layer = 3")
                conn.commit()
            if "MIOS_DB_AUTHORITATIVE" in os.environ:
                del os.environ["MIOS_DB_AUTHORITATIVE"]

    def test_verb_catalog_sentinel_and_shadow(self):
        import mios_pipe.routing.verbcatalog as vc
        
        # Divergence setup: update parallel_limit for list_windows in DB
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE verb
                    SET parallel_limit = 99
                    WHERE name = 'list_windows'
                    """
                )
            conn.commit()
            
        try:
            # Under db_authoritative = false (default), should shadow-compare and detect divergence
            os.environ["MIOS_DB_AUTHORITATIVE"] = "False"
            mios_db_config.reset_divergences()
            
            cat = vc._load_verb_catalog()
            # Under false, parallel_limit should remain TOML default (0 or not 99)
            self.assertNotEqual(cat["list_windows"]["parallel_limit"], 99)
            # Divergence should have incremented (wait for background thread)
            import time
            for _ in range(50):
                if mios_db_config.get_divergences() > 0:
                    break
                time.sleep(0.05)
            self.assertTrue(mios_db_config.get_divergences() > 0)
            
            # Now flip db_authoritative = true
            os.environ["MIOS_DB_AUTHORITATIVE"] = "True"
            cat_db = vc._load_verb_catalog()
            # Under true, parallel_limit should be loaded from DB (99)
            self.assertEqual(cat_db["list_windows"]["parallel_limit"], 99)
            
        finally:
            # Restore db state
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE verb
                        SET parallel_limit = 0
                        WHERE name = 'list_windows'
                        """
                    )
                conn.commit()
            if "MIOS_DB_AUTHORITATIVE" in os.environ:
                del os.environ["MIOS_DB_AUTHORITATIVE"]

    @patch("mios_toml.load_merged")
    @patch("mios_db_config.load_db_config")
    def test_zero_divergence_on_seeded_tree(self, mock_db_config, mock_load):
        import mios_toml
        import mios_pipe.routing.verbcatalog as vc
        
        # Retrieve the clean vendor TOML baseline
        vendor_data = mios_toml.load_vendor()
        mock_load.return_value = vendor_data
        mock_db_config.return_value = vendor_data
        
        # Reset divergences
        mios_db_config.reset_divergences()
        
        # 1. Test load_merged
        merged = mios_db_config.load_merged()
        self.assertIsNotNone(merged)
        
        # 2. Test section loading for seeded scopes
        for sec in ["ai", "mcp", "routing", "recipes", "security"]:
            sec_val = mios_db_config.section(None, sec)
            self.assertIsNotNone(sec_val)
            
        # 3. Test get keys
        self.assertEqual(
            mios_db_config.get("ai", "kernel_dispatch"),
            vendor_data.get("ai", {}).get("kernel_dispatch")
        )
        
        # 4. Test colors
        self.assertIsNotNone(mios_db_config.colors())
        
        # 5. Test verb catalog shadow compare directly
        toml_cat = vc._load_verb_catalog()
        db_cat = vc._load_verb_catalog_from_db()
        self.assertEqual(vc._compare_catalogs(toml_cat, db_cat), set())
        
        # Ensure 0 divergences detected
        self.assertEqual(mios_db_config.get_divergences(), 0)

    def test_record_divergence_deduplication(self):
        mios_db_config.reset_divergences()
        mios_db_config.record_divergence("scope.key1")
        mios_db_config.record_divergence("scope.key1")
        mios_db_config.record_divergence({"scope.key1", "scope.key2"})
        self.assertEqual(mios_db_config.get_divergences(), 2)

if __name__ == "__main__":
    unittest.main()
