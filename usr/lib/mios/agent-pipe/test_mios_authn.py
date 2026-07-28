# AI-hint: Unit tests for mios_pipe.access.authn.
"""Unit tests for authentication and caller key management."""

import json
import os
import tempfile
import unittest

from mios_pipe.access.authn import (
    _bind_host,
    _check_inbound_principal,
    _load_backend_key,
    _probe_auth_headers,
    configure,
)


class TestAuthn(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.caller_keys_file = os.path.join(self.tmp_dir.name, "caller-keys.json")

        keys_data = {
            "keys": {
                "secret_token_123": {"principal": "worker_agent", "scope": "read"},
            }
        }
        with open(self.caller_keys_file, "w", encoding="utf-8") as fh:
            json.dump(keys_data, fh)

        configure(
            backend_key="backend_secret_xyz",
            ingress_key="ingress_secret_999",
            api_require_auth=True,
            caller_keys_path=self.caller_keys_file,
            auth_hostports={"127.0.0.1:8000"},
            agent_auth_by_hostport={"remote:8000": "Bearer remote_tok"},
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_check_inbound_principal_shared_and_caller(self):
        # Operator key
        op = _check_inbound_principal("backend_secret_xyz")
        self.assertIsNotNone(op)
        self.assertEqual(op["principal"], "operator")

        # Valid caller key
        ck = _check_inbound_principal("secret_token_123")
        self.assertIsNotNone(ck)
        self.assertEqual(ck["principal"], "worker_agent")

        # Unknown key
        un = _check_inbound_principal("invalid_token_999")
        self.assertIsNone(un)

    def test_probe_auth_headers(self):
        hdrs = _probe_auth_headers("http://127.0.0.1:8000/v1/models")
        self.assertEqual(hdrs.get("Authorization"), "Bearer backend_secret_xyz")

    def test_bind_host(self):
        self.assertEqual(_bind_host(require_auth=False), "127.0.0.1")
        self.assertEqual(_bind_host(require_auth=True), "0.0.0.0")
        self.assertEqual(_bind_host(require_auth=False, override="10.0.0.5"), "10.0.0.5")


if __name__ == "__main__":
    unittest.main()
