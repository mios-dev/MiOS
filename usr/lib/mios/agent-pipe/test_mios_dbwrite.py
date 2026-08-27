# AI-hint: Unit tests for mios_pipe.dbwrite.
"""Unit tests for database writer layer."""

import unittest

from mios_pipe.dbwrite import (
    _db_create,
    _db_fire,
    _db_write,
    _pg_mirror,
    configure,
)

class TestDbWrite(unittest.TestCase):

    def setUp(self):
        self.posts = []
        configure(
            pg_enabled=True,
            pg_primary=False,
            db_post=lambda sql: self.posts.append(sql),
        )

    def test_db_create_sql_formatting(self):
        sql = _db_create("test_table", {"name": "test", "val": 123}, now_fields=("created_at",), _mirror=False)
        self.assertIn("CREATE test_table SET", sql)
        self.assertIn("created_at = time::now()", sql)
        self.assertIn('name = "test"', sql)
        self.assertIn("val = 123", sql)

    def test_db_write_dispatches_post(self):
        _db_write("event", {"action": "login"})
        self.assertEqual(len(self.posts), 1)
        self.assertIn("CREATE event SET", self.posts[0])

    def test_pg_mirror_degrade_open(self):
        _pg_mirror("event", {"action": "logout"})

if __name__ == "__main__":
    unittest.main()
