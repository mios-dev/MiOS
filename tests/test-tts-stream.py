#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Streaming TTS Latency & PipeWire Ring Buffer Feeding (T-687, T-688).
# AI-related: usr/libexec/mios/ai/tts_stream.py, tests/test-tts-stream.py
"""Automated unit test suite for MiOS Streaming TTS Pipeline."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from tts_stream import MAX_FIRST_PACKET_LATENCY_MS, StreamingTTSPipeline

class TestTTSStream(unittest.TestCase):
    def setUp(self):
        self.pipe = StreamingTTSPipeline(dry_run=True)

    def test_sub_50ms_first_packet_audio_latency(self):
        """Test streaming TTS delivers first audio chunk in <50ms."""
        res = self.pipe.stream_speech_synthesis("System ready. All agents synchronized.")
        self.assertLess(res.first_packet_latency_ms, MAX_FIRST_PACKET_LATENCY_MS)
        self.assertGreater(res.chunks_generated, 0)
        self.assertEqual(res.buffer_underruns_detected, 0)

    def test_multi_sentence_streaming_zero_underruns(self):
        """Test 20 sentence stream maintains 0 buffer underruns."""
        for i in range(20):
            res = self.pipe.stream_speech_synthesis(f"Sentence number {i} with audio chunks streaming.")
            self.assertEqual(res.buffer_underruns_detected, 0)
            self.assertLess(res.first_packet_latency_ms, MAX_FIRST_PACKET_LATENCY_MS)

if __name__ == "__main__":
    unittest.main()
