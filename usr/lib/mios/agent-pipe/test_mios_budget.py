# AI-hint: stdlib unit test for mios_agent_call budget and depth limits (AGY-6).
# Verifies the conversation and autonomous token budget ceilings, as well as the
# max dispatch depth recursion limit.
import unittest
import asyncio
from unittest.mock import patch, MagicMock

import mios_agent_call
import mios_pipe.routing.agent_call as target_module

class AsyncContextMock:
    def __init__(self, *args, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    def __call__(self, *args, **kwargs):
        return self

async def dummy_async(*args, **kwargs):
    pass

class TestMiosBudgetAndDepth(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Clear/reset state
        target_module._IN_FLIGHT_PROMPTS.clear()
        target_module._SESSION_TOKENS.clear()
        target_module._AUTONOMOUS_SOURCE_TOKENS.clear()
        target_module._dispatch_depth_var.set(0)
        target_module._opt_int_mb = lambda x: int(x or 0)
        target_module._lane_sem_key = lambda cfg: "test-lane"
        target_module._strip_agent_chrome = lambda text: text
        
        class MockSloShed(Exception):
            pass
        target_module._SloShed = MockSloShed

    @patch("mios_pipe.routing.agent_call._get_budget_ceil")
    @patch("mios_pipe.routing.agent_call._conv_key_var")
    async def test_conversation_token_budget_ceiling(self, mock_conv_key, mock_budget):
        mock_conv_key.get.return_value = "session-1"
        # Mock budget ceiling to 2M tokens
        mock_budget.side_effect = lambda key, default: {
            "conversation_token_ceil": 2000000,
            "max_dispatch_depth": 5
        }.get(key, default)
        
        # Exceed budget
        target_module._SESSION_TOKENS["session-1"] = 2500000
        
        cfg = {"vram_mb": 0}
        body = {
            "messages": [
                {"role": "system", "content": "sys1"},
                {"role": "system", "content": "sys2"},
                {"role": "user", "content": "usr1"},
                {"role": "user", "content": "usr2"},
                {"role": "user", "content": "usr3"},
                {"role": "user", "content": "usr4"},
                {"role": "user", "content": "usr5"},
                {"role": "user", "content": "usr6"},
            ]
        }
        
        # Mock downstream dependency to intercept execution after budget check
        class PassedCheck(Exception):
            pass
        target_module._agent_offload_engine = MagicMock(side_effect=PassedCheck)
        
        with self.assertRaises(PassedCheck):
            await target_module._call_agent_complete(
                "test-agent", cfg, body, {}, MagicMock(), priority=1.0
            )
        
        # Verify that messages are trimmed: should keep system messages + the last 4 non-system messages
        expected = [
            {"role": "system", "content": "sys1"},
            {"role": "system", "content": "sys2"},
            {"role": "user", "content": "usr3"},
            {"role": "user", "content": "usr4"},
            {"role": "user", "content": "usr5"},
            {"role": "user", "content": "usr6"},
        ]
        self.assertEqual(body["messages"], expected)

    @patch("mios_pipe.routing.agent_call._get_budget_ceil")
    @patch("mios_pipe.routing.agent_call._autonomous_var")
    @patch("mios_pipe.routing.agent_call._autonomous_source_var")
    async def test_autonomous_token_budget_ceiling(self, mock_source, mock_auto, mock_budget):
        mock_auto.get.return_value = True
        mock_source.get.return_value = "source-1"
        mock_budget.side_effect = lambda key, default: {
            "autonomous_token_ceil": 400000,
            "max_dispatch_depth": 5
        }.get(key, default)
        
        # Exceed budget
        target_module._AUTONOMOUS_SOURCE_TOKENS["source-1"] = 450000
        
        cfg = {"vram_mb": 0}
        body = {
            "messages": [
                {"role": "system", "content": "sys1"},
                {"role": "system", "content": "sys2"},
                {"role": "user", "content": "usr1"},
                {"role": "user", "content": "usr2"},
                {"role": "user", "content": "usr3"},
                {"role": "user", "content": "usr4"},
                {"role": "user", "content": "usr5"},
                {"role": "user", "content": "usr6"},
            ]
        }
        
        # Mock downstream dependency to intercept execution after budget check
        class PassedCheck(Exception):
            pass
        target_module._agent_offload_engine = MagicMock(side_effect=PassedCheck)
        
        with self.assertRaises(PassedCheck):
            await target_module._call_agent_complete(
                "test-agent", cfg, body, {}, MagicMock(), priority=1.0
            )
        
        # Verify that messages are trimmed: should keep system messages + the last 4 non-system messages
        expected = [
            {"role": "system", "content": "sys1"},
            {"role": "system", "content": "sys2"},
            {"role": "user", "content": "usr3"},
            {"role": "user", "content": "usr4"},
            {"role": "user", "content": "usr5"},
            {"role": "user", "content": "usr6"},
        ]
        self.assertEqual(body["messages"], expected)

    @patch("mios_pipe.routing.agent_call._get_budget_ceil")
    async def test_max_dispatch_depth(self, mock_budget):
        mock_budget.side_effect = lambda key, default: {
            "max_dispatch_depth": 5
        }.get(key, default)
        
        # Set current depth to 5 (equal to max)
        target_module._dispatch_depth_var.set(5)
        
        cfg = {"vram_mb": 0}
        body = {"messages": [{"role": "user", "content": "hello"}]}
        
        with self.assertRaises(RecursionError) as ctx:
            await target_module._call_agent_complete(
                "test-agent", cfg, body, {}, MagicMock(), priority=1.0
            )
        self.assertIn("Max dispatch depth exceeded", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
