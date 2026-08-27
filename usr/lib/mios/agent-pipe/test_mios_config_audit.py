#!/usr/bin/env python3
import sys
import os
import unittest
import json
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

def setUpModule():
    if psycopg is None:
        raise unittest.SkipTest("no live pgvector -- integration test")
    port = os.environ.get("MIOS_PORT_PGVECTOR", "8600")
    conn_str = f"postgresql://mios:mios@localhost:{port}/mios"
    try:
        with psycopg.connect(conn_str, connect_timeout=1):
            pass
    except Exception:
        raise unittest.SkipTest("no live pgvector -- integration test")

class TestMiosConfigAudit(unittest.TestCase):

    def setUp(self):
        self.conn_str = "postgresql://mios:mios@localhost:8432/mios"
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM config_kv WHERE scope = 'test_audit_scope'")
                cur.execute("DELETE FROM config_kv WHERE scope = 'security' AND key = 'default_password'")
                cur.execute("DELETE FROM verb WHERE name IN ('test_audit_verb_clean', 'test_audit_verb_secret')")
                cur.execute("DELETE FROM config_event WHERE scope = 'config_kv' AND key LIKE 'test_audit_scope.%'")
                cur.execute("DELETE FROM config_event WHERE scope = 'config_event' AND key = 'security.default_password'")
                cur.execute("DELETE FROM config_event WHERE scope = 'config_kv' AND key = 'security.default_password'")
                cur.execute("DELETE FROM config_event WHERE scope = 'verb' AND key IN ('test_audit_verb_clean', 'test_audit_verb_secret')")
            conn.commit()

    def test_config_kv_redaction(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('test_audit_scope', 'normal_key', '"normal_value"'::jsonb, 3, 'normal')
                    """
                )
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('test_audit_scope', 'github_api_key', '"ghp_abcdef123456"'::jsonb, 3, 'secret key')
                    """
                )
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('security', 'default_password', '"mypass123"'::jsonb, 3, 'secret scope')
                    """
                )
            conn.commit()

        with psycopg.connect(self.conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT new_value FROM config_event
                    WHERE scope = 'config_kv' AND key = 'test_audit_scope.normal_key'
                    ORDER BY id DESC LIMIT 1;
                    """
                )
                r_normal = cur.fetchone()
                self.assertIsNotNone(r_normal)
                self.assertEqual(r_normal["new_value"], "normal_value")

                cur.execute(
                    """
                    SELECT new_value FROM config_event
                    WHERE scope = 'config_kv' AND key = 'test_audit_scope.github_api_key'
                    ORDER BY id DESC LIMIT 1;
                    """
                )
                r_secret_key = cur.fetchone()
                self.assertIsNotNone(r_secret_key)
                self.assertEqual(r_secret_key["new_value"], "[REDACTED_SECRET]")

                cur.execute(
                    """
                    SELECT new_value FROM config_event
                    WHERE scope = 'config_kv' AND key = 'security.default_password'
                    ORDER BY id DESC LIMIT 1;
                    """
                )
                r_secret_scope = cur.fetchone()
                self.assertIsNotNone(r_secret_scope)
                self.assertEqual(r_secret_scope["new_value"], "[REDACTED_SECRET]")

    def test_container_env_redaction(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                val_json = {
                    "Container": {
                        "ContainerName": "test-container",
                        "Environment": [
                            "PORT=8080",
                            "K3S_TOKEN=mysecret-token-value",
                            "DATABASE_PASSWORD=secretpassword123"
                        ],
                        "SecretConfig": {
                            "some_value": "nested-value"
                        },
                        "OtherConfig": {
                            "api_key": "some-value-to-redact"
                        }
                    }
                }
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('test_audit_scope', 'container_cfg', %s::jsonb, 3, 'container with env secrets')
                    """,
                    (json.dumps(val_json),)
                )
            conn.commit()

        with psycopg.connect(self.conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT new_value FROM config_event
                    WHERE scope = 'config_kv' AND key = 'test_audit_scope.container_cfg'
                    ORDER BY id DESC LIMIT 1;
                    """
                )
                r_container = cur.fetchone()
                self.assertIsNotNone(r_container)
                new_val = r_container["new_value"]
                if isinstance(new_val, str):
                    new_val = json.loads(new_val)

                env = new_val["Container"]["Environment"]
                self.assertIn("PORT=8080", env)
                self.assertIn("K3S_TOKEN=[REDACTED_SECRET]", env)
                self.assertIn("DATABASE_PASSWORD=[REDACTED_SECRET]", env)

                self.assertEqual(new_val["Container"]["SecretConfig"], "[REDACTED_SECRET]")

                self.assertEqual(new_val["Container"]["OtherConfig"]["api_key"], "[REDACTED_SECRET]")

    def test_verb_cmd_redaction(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO verb (name, sig, desc_default, tier, permission, cmd)
                    VALUES ('test_audit_verb_clean', '()', 'clean desc', 'common', 'read', 'git status')
                    """
                )
                cur.execute(
                    """
                    INSERT INTO verb (name, sig, desc_default, tier, permission, cmd)
                    VALUES ('test_audit_verb_secret', '()', 'secret desc', 'common', 'read', 'curl -H "Authorization: Bearer my_secret_token_123" https://api.github.com')
                    """
                )
            conn.commit()

        with psycopg.connect(self.conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT new_value FROM config_event
                    WHERE scope = 'verb' AND key = 'test_audit_verb_clean'
                    ORDER BY id DESC LIMIT 1;
                    """
                )
                r_clean = cur.fetchone()
                self.assertIsNotNone(r_clean)
                self.assertEqual(r_clean["new_value"]["cmd"], "git status")

                cur.execute(
                    """
                    SELECT new_value FROM config_event
                    WHERE scope = 'verb' AND key = 'test_audit_verb_secret'
                    ORDER BY id DESC LIMIT 1;
                    """
                )
                r_secret = cur.fetchone()
                self.assertIsNotNone(r_secret)
                self.assertEqual(r_secret["new_value"]["cmd"], "[REDACTED_SECRET]")

if __name__ == "__main__":
    unittest.main()
