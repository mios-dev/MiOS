#!/usr/bin/env python3
import sys
import os
import unittest
import psycopg
from psycopg.rows import dict_row

# Ensure /usr/lib/mios is in path
sys.path.insert(0, "/usr/lib/mios")

class TestMiosConfigAudit(unittest.TestCase):

    def setUp(self):
        self.conn_str = "postgresql://mios:mios@localhost:8432/mios"
        # Ensure we clean up any prior leftover test rows
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
                # 1. Non-secret insert
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('test_audit_scope', 'normal_key', '"normal_value"'::jsonb, 3, 'normal')
                    """
                )
                # 2. Secret-key insert
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('test_audit_scope', 'github_api_key', '"ghp_abcdef123456"'::jsonb, 3, 'secret key')
                    """
                )
                # 3. Secret-scope insert
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('security', 'default_password', '"mypass123"'::jsonb, 3, 'secret scope')
                    """
                )
            conn.commit()

        # Query config_event to assert redactions
        with psycopg.connect(self.conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Assert normal key
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

                # Assert secret key key
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

                # Assert secret scope key
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

    def test_verb_cmd_redaction(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # 1. Non-secret verb cmd
                cur.execute(
                    """
                    INSERT INTO verb (name, sig, desc_default, tier, permission, cmd)
                    VALUES ('test_audit_verb_clean', '()', 'clean desc', 'common', 'read', 'git status')
                    """
                )
                # 2. Secret verb cmd containing inline token
                cur.execute(
                    """
                    INSERT INTO verb (name, sig, desc_default, tier, permission, cmd)
                    VALUES ('test_audit_verb_secret', '()', 'secret desc', 'common', 'read', 'curl -H "Authorization: Bearer my_secret_token_123" https://api.github.com')
                    """
                )
            conn.commit()

        # Query config_event to assert redactions
        with psycopg.connect(self.conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Assert normal verb
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

                # Assert secret verb
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
