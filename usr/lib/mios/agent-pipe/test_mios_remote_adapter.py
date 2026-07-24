# AI-hint: Unit test for mios_pipe.routing.remote_adapter. Validates Anthropic, Gemini, and OpenAI remote calls.
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from mios_pipe.routing.remote_adapter import call_remote


class TestRemoteAdapter(unittest.TestCase):
    def test_openai_passthrough(self):
        async def _run():
            node_cfg = {"name": "remote-oai", "api": "openai"}
            oai_req = {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}

            captured = []
            async def mock_transport(cfg, payload):
                captured.append((cfg, payload))
                return {"choices": [{"message": {"role": "assistant", "content": "hello"}}]}

            res = await call_remote(node_cfg, oai_req, mock_transport)
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0][1], oai_req)
            self.assertEqual(res["choices"][0]["message"]["content"], "hello")

        asyncio.run(_run())

    def test_anthropic_adapter(self):
        async def _run():
            node_cfg = {"name": "remote-claude", "api": "anthropic"}
            oai_req = {
                "model": "claude-3-5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"}
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "get weather",
                            "parameters": {"type": "object", "properties": {"loc": {"type": "string"}}}
                        }
                    }
                ]
            }

            captured = []
            async def mock_transport(cfg, payload):
                captured.append(payload)
                return {
                    "content": [
                        {"type": "text", "text": "The weather is sunny."},
                        {"type": "tool_use", "id": "call_123", "name": "get_weather", "input": {"loc": "NYC"}}
                    ]
                }

            res = await call_remote(node_cfg, oai_req, mock_transport)
            self.assertEqual(len(captured), 1)
            p = captured[0]
            self.assertEqual(p["system"], "You are helpful.")
            self.assertEqual(p["messages"][0]["role"], "user")
            self.assertEqual(p["messages"][0]["content"][0]["text"], "Hello")
            self.assertEqual(p["tools"][0]["name"], "get_weather")

            self.assertEqual(res["role"], "assistant")
            self.assertEqual(res["content"], "The weather is sunny.")
            self.assertEqual(len(res["tool_calls"]), 1)
            self.assertEqual(res["tool_calls"][0]["function"]["name"], "get_weather")

        asyncio.run(_run())

    def test_gemini_adapter(self):
        async def _run():
            node_cfg = {"name": "remote-gemini", "api": "gemini"}
            oai_req = {
                "model": "gemini-1.5-pro",
                "messages": [
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": "Hi"}
                ]
            }

            captured = []
            async def mock_transport(cfg, payload):
                captured.append(payload)
                return {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Gemini response text"}]
                            }
                        }
                    ]
                }

            res = await call_remote(node_cfg, oai_req, mock_transport)
            self.assertEqual(len(captured), 1)
            p = captured[0]
            self.assertEqual(p["systemInstruction"]["parts"][0]["text"], "System prompt")
            self.assertEqual(p["contents"][0]["role"], "user")

            self.assertEqual(res["role"], "assistant")
            self.assertEqual(res["content"], "Gemini response text")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
