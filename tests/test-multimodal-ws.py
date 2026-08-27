#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Multi-modal WebSocket Streaming & Sub-100ms Latency (T-671, T-672).
# AI-related: usr/lib/mios/agent-pipe/multimodal_ws.py, tests/test-multimodal-ws.py
"""Automated unit test suite for MiOS Multi-modal WebSocket Pipeline."""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "agent-pipe"))

from multimodal_ws import MAX_VOICE_LATENCY_MS, MultiModalStreamingPipeline


class TestMultiModalWS(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pipe = MultiModalStreamingPipeline(dry_run=True)

    async def test_sub_100ms_conversational_voice_latency(self):
        """Test concurrent audio and vision processing maintains <100ms voice response latency."""
        turn = await self.pipe.process_multimodal_turn("turn_test_01", audio_frames=10, video_frames=3)
        self.assertIsNotNone(turn)
        self.assertEqual(turn.audio_frames_in, 10)
        self.assertEqual(turn.video_frames_in, 3)
        self.assertLess(turn.voice_latency_ms, MAX_VOICE_LATENCY_MS)

    async def test_heavy_vision_load_does_not_starve_audio(self):
        """Test heavy background vision stream does not push voice latency above 100ms."""
        turn = await self.pipe.process_multimodal_turn("turn_heavy_vis", audio_frames=5, video_frames=10)
        self.assertLess(turn.voice_latency_ms, MAX_VOICE_LATENCY_MS)


if __name__ == "__main__":
    unittest.main()
