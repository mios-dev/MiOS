# AI-hint: stdlib unit test for pgvector schema and cosine similarity matching (AGY-7).
# Connects to the database and performs a vector similarity query to assert correct functionality.
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
        with psycopg.connect(conn_str, connect_timeout=1):
            pass
    except Exception:
        raise unittest.SkipTest("no live pgvector -- integration test")

class TestMiosVectorDb(unittest.TestCase):

    def setUp(self):
        self.conn_str = "postgresql://mios:mios@localhost:8432/mios"
        # Seed test verbs
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # Clean up any leftover test data
                # Escaped % for psycopg placeholder parser
                cur.execute("DELETE FROM verb WHERE name LIKE 'test_verb_%%'")
                
                # Insert test verbs with 768-dim embeddings
                # Let's create two orthogonal vectors
                vec_a = [0.0] * 768
                vec_a[0] = 1.0
                
                vec_b = [0.0] * 768
                vec_b[1] = 1.0
                
                cur.execute(
                    "INSERT INTO verb (name, sig, desc_default, tier, permission, emb, emb_model, emb_version) "
                    "VALUES ('test_verb_a', 'test_sig', 'test search query', 'common', 'read', %s::vector, 'test-model', 'v1')",
                    (vec_a,)
                )
                cur.execute(
                    "INSERT INTO verb (name, sig, desc_default, tier, permission, emb, emb_model, emb_version) "
                    "VALUES ('test_verb_b', 'test_sig', 'completely different action', 'common', 'read', %s::vector, 'test-model', 'v1')",
                    (vec_b,)
                )
            conn.commit()

    def tearDown(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM verb WHERE name LIKE 'test_verb_%%'")
            conn.commit()

    def test_pgvector_cosine_similarity(self):
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # Query with a target vector close to vec_a
                target_vec = [0.0] * 768
                target_vec[0] = 0.9
                target_vec[1] = 0.1
                
                # Fetch closest verb by cosine distance (<=>)
                cur.execute(
                    "SELECT name, emb <=> %s::vector as distance "
                    "FROM verb WHERE name LIKE 'test_verb_%%' "
                    "ORDER BY emb <=> %s::vector ASC LIMIT 1",
                    (target_vec, target_vec)
                )
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "test_verb_a")
                
                # Distance should be small for matching, larger for different
                dist_a = row[1]
                
                cur.execute(
                    "SELECT name, emb <=> %s::vector as distance "
                    "FROM verb WHERE name = 'test_verb_b'",
                    (target_vec,)
                )
                row_b = cur.fetchone()
                self.assertIsNotNone(row_b)
                dist_b = row_b[1]
                
                self.assertTrue(dist_a < dist_b, f"dist_a={dist_a} should be less than dist_b={dist_b}")

if __name__ == "__main__":
    unittest.main()
