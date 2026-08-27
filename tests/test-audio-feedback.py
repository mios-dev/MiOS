#!/usr/bin/env python3
# AI-hint: Automated unit test suite for audio feedback daemon and harmonic PCM synthesizer.
# AI-related: usr/libexec/mios/ux/audio_feedback.py, usr/share/mios/mios.toml
"""Unit and integration test suite for AudioFeedbackEngine and audio_feedback CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "audio_feedback.py")

spec = importlib.util.spec_from_file_location("audio_feedback", _TARGET_PATH)
if spec and spec.loader:
    audio_feedback = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = audio_feedback
    spec.loader.exec_module(audio_feedback)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestAudioFeedback(unittest.TestCase):
    """Test suite for event chord synthesis, PCM rendering, and audio feedback cues."""

    def test_event_chord_map_completeness(self):
        self.assertIn("completed", audio_feedback.EVENT_CHORD_MAP)
        self.assertIn("started", audio_feedback.EVENT_CHORD_MAP)
        self.assertIn("requires_input", audio_feedback.EVENT_CHORD_MAP)
        self.assertIn("warning", audio_feedback.EVENT_CHORD_MAP)
        self.assertIn("failed", audio_feedback.EVENT_CHORD_MAP)
        for name, data in audio_feedback.EVENT_CHORD_MAP.items():
            self.assertIn("freqs", data)
            self.assertIn("duration", data)
            self.assertIn("decay", data)

    def test_synthesize_event_pcm(self):
        with tempfile.TemporaryDirectory(prefix="mios-audio-test-") as tmpdir:
            wav_path = os.path.join(tmpdir, "completed.wav")
            samples = audio_feedback.synthesize_event_pcm("completed", wav_path, volume=0.5, sample_rate=22050)
            self.assertGreater(samples, 100)
            self.assertTrue(os.path.isfile(wav_path))
            self.assertGreater(os.path.getsize(wav_path), 200)

    def test_engine_synthesize_all_mock(self):
        engine = audio_feedback.AudioFeedbackEngine(volume_pct=60, mock=True)
        res = engine.synthesize_all("/tmp/sounds")
        self.assertEqual(len(res), len(audio_feedback.EVENT_CHORD_MAP))
        self.assertIn("completed", res)

    def test_play_cue_mock(self):
        engine = audio_feedback.AudioFeedbackEngine(volume_pct=75, mock=True)
        res = engine.play_cue("started")
        self.assertTrue(res["played"])
        self.assertEqual(res["event"], "started")
        self.assertEqual(res["backend"], "mock_pcm")
        self.assertEqual(res["volume_pct"], 75)

    def test_play_cue_unknown_event_raises(self):
        engine = audio_feedback.AudioFeedbackEngine(mock=True)
        with self.assertRaises(ValueError):
            engine.play_cue("unknown_event_xyz")

    def test_cli_play_event_mock(self):
        test_args = ["audio_feedback.py", "--event", "completed", "--volume", "50", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = audio_feedback.main()
            self.assertEqual(exit_code, 0)

    def test_cli_synthesize_to_mock(self):
        test_args = ["audio_feedback.py", "--synthesize-to", "/tmp/mios-cues", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = audio_feedback.main()
            self.assertEqual(exit_code, 0)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAudioFeedback)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
