#!/usr/bin/env python3
# AI-hint: Standalone unit test suite for mios-gateway-agent service (T-078).
# Pure stdlib + asyncio + fastapi.testclient. Test runs offline: exit 0 = pass.
# usr/lib/mios/agent-pipe/test_mios_gateway_agent.py

import sys
import os
import json
import asyncio

# Prevent path collisions (ensure we load the gateway-agent's server, not the orchestrator's server)
sys.path = [p for p in sys.path if p not in ("", ".", os.path.dirname(os.path.abspath(__file__)))]
# Resolve gateway-agent path relative to this script
gateway_agent_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../gateway-agent"))
sys.path.insert(0, gateway_agent_path)

from fastapi.testclient import TestClient
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

class MockAsyncCursor:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    async def execute(self, sql, params=None):
        pass
    async def fetchone(self):
        return [json.dumps([{"role": "user", "content": "prior turn"}])]

class MockAsyncConnection:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    def cursor(self):
        return MockAsyncCursor()

class MockPsycopg:
    AsyncConnection = MagicMock()
    
    @classmethod
    def setup_mock(cls):
        cls.AsyncConnection.connect = AsyncMock(return_value=MockAsyncConnection())

class TestGatewayAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override psycopg lazy loader inside session_db with a mock
        MockPsycopg.setup_mock()
        sys.modules["psycopg"] = MockPsycopg
        
        # Now import the server FastAPI app
        import server
        cls.app = server.app
        cls.client = TestClient(server.app)

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "service": "mios-gateway-agent"})

    def test_cluster_health(self):
        r = self.client.get("/v1/cluster/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "service": "mios-gateway-agent"})

    def test_models(self):
        r = self.client.get("/v1/models")
        self.assertEqual(r.status_code, 200)
        resp = r.json()
        self.assertEqual(resp.get("object"), "list")
        self.assertTrue(len(resp.get("data", [])) > 0)
        self.assertEqual(resp.get("data")[0].get("owned_by"), "system")

    @patch("smolagents.OpenAIServerModel")
    @patch("smolagents.ToolCallingAgent")
    def test_chat_completions_non_stream(self, mock_agent_cls, mock_model_cls):
        mock_agent = MagicMock()
        mock_agent.run = MagicMock(return_value="Mocked response content")
        mock_agent_cls.return_value = mock_agent

        payload = {
            "model": "granite4.1:3b",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "metadata": {"chat_id": "test-session-123"}
        }
        r = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(r.status_code, 200)
        resp = r.json()
        self.assertTrue(resp.get("id").startswith("chatcmpl-"))
        self.assertEqual(resp.get("object"), "chat.completion")
        self.assertEqual(resp.get("choices")[0].get("message").get("content"), "Mocked response content")
        self.assertEqual(resp.get("choices")[0].get("finish_reason"), "stop")

    @patch("smolagents.OpenAIServerModel")
    @patch("smolagents.ToolCallingAgent")
    def test_chat_completions_stream(self, mock_agent_cls, mock_model_cls):
        from smolagents.memory import ActionStep, ToolCall
        from smolagents.agents import FinalAnswerStep
        
        step1 = ActionStep(step_number=1, timing=None, model_input_messages=[])
        step1.model_output = "Thinking..."
        step1.tool_calls = [ToolCall(name="dummy", arguments={}, id="1")]
        step1.observations = "Done tool"
        
        step2 = FinalAnswerStep(output="Final result")
        
        mock_agent = MagicMock()
        mock_agent.run = MagicMock(return_value=[step1, step2])
        mock_agent_cls.return_value = mock_agent

        payload = {
            "model": "granite4.1:3b",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
            "metadata": {"chat_id": "test-session-123"}
        }
        r = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(r.status_code, 200)
        self.assertTrue("text/event-stream" in r.headers.get("content-type", ""))
        
        lines = [line for line in r.iter_lines() if line]
        chunks = [json.loads(line.replace("data: ", "")) for line in lines if line.startswith("data: ") and not line.endswith("[DONE]")]
        
        self.assertTrue(len(chunks) > 0)
        self.assertEqual(chunks[-1].get("choices")[0].get("finish_reason"), "stop")

if __name__ == "__main__":
    unittest.main()
