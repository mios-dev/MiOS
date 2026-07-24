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
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    DEP_ERROR = e

from unittest.mock import patch, MagicMock

class TestDeltaConfigWrite(unittest.TestCase):
    def test_delta_write(self):
        import tempfile
        import shutil
        from mios_pipe.kernel.config import write_user_config

        tmp_dir = tempfile.mkdtemp()
        vendor_file = os.path.join(tmp_dir, "vendor.toml")
        host_file = os.path.join(tmp_dir, "host.toml")
        user_file = os.path.join(tmp_dir, "user.toml")

        with open(vendor_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey1 = 'vendor_val'\nkey2 = 'vendor_val2'\n")

        with open(host_file, "w", encoding="utf-8") as f:
            f.write("[section]\nkey2 = 'host_val2'\nkey3 = 'host_val3'\n")

        env_vars = {
            "MIOS_VENDOR_TOML": vendor_file,
            "MIOS_HOST_TOML": host_file,
            "MIOS_USER_TOML": user_file,
            "MIOS_VENDOR_TOML_D": os.path.join(tmp_dir, "nonexistent1"),
            "MIOS_HOST_TOML_D": os.path.join(tmp_dir, "nonexistent2"),
            "MIOS_USER_TOML_D": os.path.join(tmp_dir, "nonexistent3"),
        }

        orig_env = {k: os.environ.get(k) for k in env_vars}
        for k, v in env_vars.items():
            os.environ[k] = v

        try:
            full_config = {
                "section": {
                    "key1": "vendor_val",
                    "key2": "host_val2",
                    "key3": "user_val3",
                    "key4": "new_val",
                }
            }

            write_user_config(full_config, dest_path=user_file)

            try:
                import tomllib as tl
            except ImportError:
                import tomli as tl

            with open(user_file, "rb") as f:
                res = tl.load(f)

            self.assertNotIn("key1", res.get("section", {}))
            self.assertNotIn("key2", res.get("section", {}))
            self.assertEqual(res.get("section", {}).get("key3"), "user_val3")
            self.assertEqual(res.get("section", {}).get("key4"), "new_val")

        finally:
            for k, v in orig_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_to_toml_datetime_and_unsupported(self):
        import datetime
        from mios_pipe.kernel.config import to_toml
        try:
            import tomllib as tl
        except ImportError:
            import tomli as tl

        now = datetime.datetime(2026, 7, 18, 12, 0, 0, tzinfo=datetime.timezone.utc)
        d = {"time": now}
        toml_str = to_toml(d)
        parsed = tl.loads(toml_str)
        self.assertEqual(parsed["time"], now)

        # test raising on unknown types
        with self.assertRaises(TypeError):
            to_toml({"unsupported": object()})

class TestConfigWrite(unittest.TestCase):
    def setUp(self):
        if not HAS_DEPS:
            raise unittest.SkipTest(f"Missing test dependencies: {DEP_ERROR}")
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
        # to_toml renders SECTION-style TOML ("[meta]\nmios_version = ..."), not the
        # old dotted "meta.mios_version = ..." form (the sibling asserts below already
        # expect section style); match the actual, correct output.
        self.assertIn("[meta]", response.text)
        self.assertIn('mios_version = "0.3.0"', response.text)
        self.assertIn("[test_section]", response.text)
        self.assertIn("[[test_section.arr]]", response.text)

    def test_get_config_unauth(self):
        with patch("mios_pipe.routing.portal._portal_authed", return_value=False):
            response = self.client.get("/portal/config")
            self.assertEqual(response.status_code, 401)

    # Mock the live-config load so validate_config's drop-guard sees an EMPTY live
    # config (nothing to "drop") and the minimal payload is accepted. The guard
    # ([identity]/[ports] must not be dropped from the LIVE config) is correct
    # production behavior; this unit test exercises only the write path.
    @patch("mios_toml.load_merged", return_value={})
    @patch("mios_pipe.routing.portal._portal_authed", return_value=True)
    @patch("mios_pipe.kernel.config.write_user_config")
    @patch("fastapi.BackgroundTasks.add_task")
    def test_post_config_success(self, mock_add_task, mock_write_user, mock_authed, mock_load_merged):
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
