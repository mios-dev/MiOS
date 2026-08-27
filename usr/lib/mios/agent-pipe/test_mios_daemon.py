# AI-hint: stdlib unit test for mios_agent_call daemon runaway controls.
import unittest
import asyncio
import time
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

class TestMiosDaemonGateAndDedup(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        target_module._IN_FLIGHT_PROMPTS.clear()
        target_module._SESSION_TOKENS.clear()
        target_module._AUTONOMOUS_SOURCE_TOKENS.clear()
        target_module._dispatch_depth_var.set(0)
        target_module._opt_int_mb = lambda x: int(x or 0)
        target_module._lane_sem_key = lambda cfg: "test-lane"
        target_module._strip_agent_chrome = lambda text: text

        self.old_rr_enable = target_module.RR_ENABLE
        target_module.RR_ENABLE = False

        class MockSloShed(Exception):
            pass
        target_module._SloShed = MockSloShed

    async def asyncTearDown(self):
        target_module.RR_ENABLE = self.old_rr_enable

    @patch("mios_pipe.routing.agent_call._get_cpu_load")
    @patch("mios_pipe.routing.agent_call._get_gpu_vram_usage")
    @patch("mios_pipe.routing.agent_call._host_threshold_val")
    @patch("mios_pipe.routing.agent_call._agent_binding")
    @patch("mios_pipe.routing.agent_call._agent_offload_engine")
    async def test_host_pressure_gate_degrades_to_cpu(self, mock_offload, mock_binding, mock_threshold, mock_vram, mock_cpu):
        mock_cpu.return_value = 10.0
        mock_vram.return_value = 95.0 # above 90% threshold
        mock_offload.return_value = None

        mock_threshold.side_effect = lambda key, default: {
            "big_ram_model": "mistral-magistral-small-2509",
            "max_cpu_percent": 85.0,
            "max_vram_percent": 90.0,
            "small_ram_model": "granite4.1:8b"
        }.get(key, default)

        mock_binding.side_effect = [
            ("http://localhost:8640/v1", "mistral-magistral-small-2509"), # heavy
            ("http://localhost:8450/v1", "granite4.1:8b"), # degraded cpu
        ]

        cfg = {"vram_mb": 4096}
        body = {"messages": [{"role": "user", "content": "hello"}]}

        called_with_cpu = False
        async def mock_inner(name, cfg, body, headers, client, prefer_cpu=True):
            nonlocal called_with_cpu
            called_with_cpu = True
            return name, "degraded response"

        with patch("mios_pipe.routing.agent_call._call_agent_complete_inner", mock_inner), \
             patch("mios_pipe.routing.agent_call._admit", dummy_async), \
             patch("mios_pipe.routing.agent_call._priority_gate", AsyncContextMock), \
             patch("mios_pipe.routing.agent_call._endpoint_sem", AsyncContextMock), \
             patch("mios_pipe.routing.agent_call._lane_sem", AsyncContextMock), \
             patch("mios_pipe.routing.agent_call._model_active", dummy_async), \
             patch("mios_pipe.routing.agent_call._record_cost", MagicMock()):

            name, text = await target_module._call_agent_complete(
                "test-agent", cfg, body, {}, MagicMock(), prefer_cpu=False, priority=1.0
            )

        self.assertTrue(called_with_cpu)
        self.assertEqual(text, "degraded response")

    @patch("mios_pipe.routing.agent_call._agent_offload_engine")
    async def test_request_dedup_collapses_inflight(self, mock_offload):
        cfg = {"vram_mb": 0}
        body = {"messages": [{"role": "user", "content": "hello"}]}
        mock_offload.return_value = None

        inner_calls = 0
        async def mock_inner(name, cfg, body, headers, client, prefer_cpu=True):
            nonlocal inner_calls
            inner_calls += 1
            await asyncio.sleep(0.1) # yield control so concurrent task can enter
            return name, f"response {inner_calls}"

        with patch("mios_pipe.routing.agent_call._call_agent_complete_inner", mock_inner), \
             patch("mios_pipe.routing.agent_call._admit", dummy_async), \
             patch("mios_pipe.routing.agent_call._priority_gate", AsyncContextMock), \
             patch("mios_pipe.routing.agent_call._endpoint_sem", AsyncContextMock), \
             patch("mios_pipe.routing.agent_call._lane_sem", AsyncContextMock), \
             patch("mios_pipe.routing.agent_call._model_active", dummy_async), \
             patch("mios_pipe.routing.agent_call._record_cost", MagicMock()), \
             patch("mios_pipe.routing.agent_call._agent_binding", lambda c, e: ("http://localhost:8450/v1", "granite4.1:8b")):

            t1 = asyncio.create_task(
                target_module._call_agent_complete("agent1", cfg, body, {}, MagicMock(), priority=1.0)
            )
            t2 = asyncio.create_task(
                target_module._call_agent_complete("agent1", cfg, body, {}, MagicMock(), priority=1.0)
            )

            res1 = await t1
            res2 = await t2

        self.assertEqual(inner_calls, 1)
        self.assertEqual(res1, res2)
        self.assertEqual(res1[1], "response 1")

if __name__ == "__main__":
    unittest.main()
