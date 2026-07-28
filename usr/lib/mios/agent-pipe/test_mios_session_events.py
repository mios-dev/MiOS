# AI-hint: Unit tests for mios_pipe.observability.session_events.
"""Unit tests for session event emission and tool text sanitization."""

import unittest
from unittest import mock

from mios_pipe.observability import audit as mios_audit
from mios_pipe.observability.session_events import (
    _emit_session_event,
    _sanitize_tool_text,
    configure,
)


class TestSessionEvents(unittest.TestCase):

    def setUp(self):
        mios_audit.CHAIN_ENABLE = True
        mios_audit._CHAINER.seed(0, mios_audit.GENESIS)

    def test_sanitize_tool_text(self):
        # ANSI CSI stripped
        self.assertEqual(_sanitize_tool_text("\x1b[31mRed\x1b[0m"), "Red")
        # Bidi override stripped
        self.assertEqual(_sanitize_tool_text("\u202aLeftToRight\u202c"), "LeftToRight")
        # C0 controls stripped except tab/newline/CR
        self.assertEqual(_sanitize_tool_text("Hello\x07\tWorld\r\n"), "Hello\tWorld\r\n")

    def test_emit_session_event_stamping(self):
        created_sqls = []

        def mock_pg_mirror(table, fields):
            pass

        def mock_db_create(table, fields, now_fields=None, _mirror=True):
            self.assertIn("chain_hash", fields)
            return f"CREATE {table} SET foo='bar';"

        def mock_db_post(sql):
            return sql

        def mock_db_fire(sql):
            created_sqls.append(sql)

        configure(
            pg_mirror=mock_pg_mirror,
            db_create=mock_db_create,
            db_post=mock_db_post,
            db_fire=mock_db_fire,
        )

        _emit_session_event({"kind": "test_event"}, session_id="s123")
        self.assertEqual(len(created_sqls), 1)
        self.assertIn("session = s123", created_sqls[0])


if __name__ == "__main__":
    unittest.main()
