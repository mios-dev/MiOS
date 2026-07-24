# AI-hint: stdlib unit test for secrets and PII redaction (AGY-8).
# Verifies redaction of API keys, email addresses, and MIOS_* env credentials.
import os
import unittest
try:
    import psycopg
except ImportError:
    psycopg = None

def setUpModule():
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

from mios_pipe.redact import redact
from mios_pg import execute as pg_execute

class TestMiosRedact(unittest.TestCase):

    def test_redact_api_keys(self):
        text = "My key is sk-12345678901234567890123456789012 and anthropic is sk-ant-12345678901234567890123456789012"
        res, redacted = redact(text)
        self.assertTrue(redacted)
        self.assertIn("[REDACTED_API_KEY]", res)
        self.assertNotIn("sk-1234567890", res)

    def test_redact_emails(self):
        text = "Contact me at alice.bob@example.com for details."
        res, redacted = redact(text)
        self.assertTrue(redacted)
        self.assertIn("[REDACTED_EMAIL]", res)
        self.assertNotIn("alice.bob", res)

    def test_redact_mios_secrets(self):
        text = 'Setting MIOS_PG_PASS="secretpassword" in env'
        res, redacted = redact(text)
        self.assertTrue(redacted)
        self.assertIn("MIOS_PG_PASS=[REDACTED_SECRET]", res)
        self.assertNotIn("secretpassword", res)

    def test_redact_no_secrets(self):
        text = "This is a normal message without any keys or emails."
        res, redacted = redact(text)
        self.assertFalse(redacted)
        self.assertEqual(res, text)

class TestMiosRedactDatabase(unittest.TestCase):

    def setUp(self):
        self.conn_str = "postgresql://mios:mios@localhost:8432/mios"
        # Ensure clean state
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM knowledge WHERE q = 'test_redact_q'")
                cur.execute("DELETE FROM agent_memory WHERE mem_key = 'test_redact_key'")
            conn.commit()

    def tearDown(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM knowledge WHERE q = 'test_redact_q'")
                cur.execute("DELETE FROM agent_memory WHERE mem_key = 'test_redact_key'")
            conn.commit()

    async def async_test_db_redaction(self):
        # 1. Insert into knowledge with an API key using parameters (SSOT/production style)
        await pg_execute(
            "INSERT INTO knowledge (q, answer) VALUES (%(q)s, %(answer)s)",
            {"q": "test_redact_q", "answer": "contact sk-12345678901234567890123456789012"}
        )
        
        # Verify it got redacted
        rows = await pg_execute(
            "SELECT answer FROM knowledge WHERE q = %(q)s",
            {"q": "test_redact_q"},
            fetch=True
        )
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["answer"], "contact [REDACTED_API_KEY]")

        # 2. Insert into agent_memory with an email
        await pg_execute(
            "INSERT INTO agent_memory (fact, mem_key) VALUES (%(fact)s, %(key)s)",
            {"fact": "email is user@example.com", "key": "test_redact_key"}
        )
        
        # Verify it got redacted
        rows = await pg_execute(
            "SELECT fact FROM agent_memory WHERE mem_key = %(key)s",
            {"key": "test_redact_key"},
            fetch=True
        )
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fact"], "email is [REDACTED_EMAIL]")

    def test_db_redaction_sync_wrapper(self):
        import asyncio
        asyncio.run(self.async_test_db_redaction())

if __name__ == "__main__":
    unittest.main()
