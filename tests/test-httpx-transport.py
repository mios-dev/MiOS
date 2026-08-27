#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS HTTPX async transport pool and UDS stream decoder.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
import unittest
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))
from mios_httpx import MiOSAsyncHTTPTransport

class TestMiOSAsyncHTTPTransport(unittest.TestCase):
    def setUp(self):
        self.transport = MiOSAsyncHTTPTransport(mock_mode=True)

    def test_fetch_tcp_endpoint_mock(self):
        res = asyncio.run(self.transport.fetch_endpoint("http://127.0.0.1:8640/v1/models"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["http_version"], "HTTP/2")
        self.assertFalse(res["is_unix_socket"])

    def test_fetch_unix_socket_endpoint_mock(self):
        res = asyncio.run(self.transport.fetch_endpoint("http+unix://%2Frun%2Fmios%2Fsockets%2Fhermes.sock/v1/chat"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["status_code"], 200)
        self.assertTrue(res["is_unix_socket"])
        self.assertEqual(res["http_version"], "HTTP/1.1-UDS")

    def test_stream_chunks_mock(self):
        async def run_stream():
            collected = []
            async for chunk in self.transport.stream_chunks("http://localhost/v1/stream"):
                collected.append(chunk)
            return collected

        chunks = asyncio.run(run_stream())
        self.assertEqual(len(chunks), 3)
        self.assertIn("[DONE]", chunks[-1])

if __name__ == "__main__":
    unittest.main()
