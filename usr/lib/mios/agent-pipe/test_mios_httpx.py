#!/usr/bin/env python3
# AI-hint: Unit test for mios_httpx.py
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_httpx import MiOSAsyncHTTPTransport


class TestMiOSAsyncHTTPTransport(unittest.TestCase):
    def test_fetch_endpoint_mock(self):
        transport = MiOSAsyncHTTPTransport(mock_mode=True)
        res = asyncio.run(transport.fetch_endpoint("http://localhost:8000/v1/models"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["status_code"], 200)

    def test_uds_endpoint_mock(self):
        transport = MiOSAsyncHTTPTransport(mock_mode=True)
        res = asyncio.run(transport.fetch_endpoint("http+unix://%2Frun%2Fmios%2Fpipe.sock/status"))
        self.assertTrue(res["is_unix_socket"])
        self.assertEqual(res["status_code"], 200)


if __name__ == "__main__":
    unittest.main()
