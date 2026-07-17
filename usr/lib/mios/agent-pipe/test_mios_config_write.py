# AI-hint: Standalone unit test for the /portal/config read/write routes to ensure correct auth, TOML parsing, and background DB re-seeding.
# AI-related: /usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py, /usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py
# AI-functions: TestConfigWrite

import unittest
import sys
import os

try:
    from fastapi.testclient import TestClient
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import server
    import mios_toml
except ImportError as e:
    class TestConfigWrite(unittest.TestCase):
        def setUp(self):
            raise unittest.SkipTest(f"Missing test dependencies: {e}")
        def test_dummy(self):
            pass
    if __name__ == "__main__":
        unittest.main()
    sys.exit(0)

from unittest.mock import patch, MagicMock

class TestConfigWrite(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)

    @patch("mios_pipe.routing.portal._portal_authed", return_value=True)
    @patch("mios_toml.load_merged")
    def test_get_config_success(self, mock_load_merged, mock_authed):
        mock_load_merged.return_value = {
            "meta": {"mios_version": "0.3.0"},
            "test_section": {"key": "val", "arr": [{"a": 1}, {"b": 2}]}
        }
        response = self.client.get("/portal/config")
        self.assertEqual(response.status_code, 200)
        self.assertIn("meta.mios_version = \"0.3.0\"", response.text)
        self.assertIn("[test_section]", response.text)
        self.assertIn("[[test_section.arr]]", response.text)

    def test_get_config_unauth(self):
        with patch("mios_pipe.routing.portal._portal_authed", return_value=False):
            response = self.client.get("/portal/config")
            self.assertEqual(response.status_code, 401)

    @patch("mios_pipe.routing.portal._portal_authed", return_value=True)
    @patch("mios_pipe.kernel.config.write_user_config")
    @patch("fastapi.BackgroundTasks.add_task")
    def test_post_config_success(self, mock_add_task, mock_write_user, mock_authed):
        payload = """
[meta]
mios_version = "0.3.0"

[[test_section.arr]]
a = 1
"""
        response = self.client.post("/portal/config", content=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_write_user.assert_called_once()
        parsed = mock_write_user.call_args[0][0]
        self.assertEqual(parsed["meta"]["mios_version"], "0.3.0")
        self.assertEqual(parsed["test_section"]["arr"][0]["a"], 1)
        mock_add_task.assert_called_once()

    @patch("mios_pipe.routing.portal._portal_authed", return_value=True)
    def test_post_config_invalid_toml(self, mock_authed):
        payload = "invalid = [toml"
        response = self.client.post("/portal/config", content=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid TOML", response.json()["error"])

    def test_post_config_unauth(self):
        with patch("mios_pipe.routing.portal._portal_authed", return_value=False):
            response = self.client.post("/portal/config", content="key = 'val'")
            self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
