#!/usr/bin/env python3
# AI-hint: Automated unit test suite for offline procedural focus audio synthesizer.
# AI-related: usr/libexec/mios/ux/focus_audio.py, usr/share/mios/mios.toml
"""Unit and integration test suite for FocusAudioSynthesizer and focus_audio CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ux", "focus_audio.py")

spec = importlib.util.spec_from_file_location("focus_audio", _TARGET_PATH)
if spec and spec.loader:
    focus_audio = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = focus_audio
    spec.loader.exec_module(focus_audio)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestFocusAudio(unittest.TestCase):
    """Test suite for offline ambient soundscapes and binaural beat PCM synthesis."""

    def test_available_presets(self):
        presets = focus_audio.AVAILABLE_PRESETS
        self.assertIn("pink_noise", presets)
        self.assertIn("brown_noise", presets)
        self.assertIn("white_noise", presets)
        self.assertIn("rain", presets)
        self.assertIn("ocean", presets)
        self.assertIn("binaural_alpha", presets)
        self.assertIn("binaural_theta", presets)

        # Binaural presets must be stereo (2 channels)
        self.assertEqual(presets["binaural_alpha"].channels, 2)
        self.assertEqual(presets["binaural_theta"].channels, 2)
        # Noise presets are mono (1 channel)
        self.assertEqual(presets["pink_noise"].channels, 1)

    def test_synthesize_pcm_mono_and_stereo(self):
        synth = focus_audio.FocusAudioSynthesizer(sample_rate=22050, mock=True)

        # Mono test
        mono_pcm, mono_ch = synth.synthesize_pcm("pink_noise", duration_sec=0.5, volume_pct=50)
        self.assertEqual(mono_ch, 1)
        self.assertEqual(len(mono_pcm), int(22050 * 0.5 * 1 * 2))

        # Stereo test
        stereo_pcm, stereo_ch = synth.synthesize_pcm("binaural_alpha", duration_sec=0.5, volume_pct=50)
        self.assertEqual(stereo_ch, 2)
        self.assertEqual(len(stereo_pcm), int(22050 * 0.5 * 2 * 2))

    def test_export_wav_real_and_mock(self):
        # Real write test
        synth_real = focus_audio.FocusAudioSynthesizer(sample_rate=22050, mock=False)
        with tempfile.TemporaryDirectory(prefix="mios-focus-test-") as tmpdir:
            wav_path = os.path.join(tmpdir, "pink.wav")
            res = synth_real.export_wav("pink_noise", wav_path, duration_sec=0.2)
            self.assertEqual(res["status"], "success")
            self.assertTrue(os.path.isfile(wav_path))
            self.assertGreater(os.path.getsize(wav_path), 500)

        # Mock test
        synth_mock = focus_audio.FocusAudioSynthesizer(sample_rate=22050, mock=True)
        res_mock = synth_mock.export_wav("pink_noise", "/tmp/mock.wav", duration_sec=0.2)
        self.assertEqual(res_mock["status"], "success")
        self.assertTrue(res_mock["mock"])

    def test_play_mock(self):
        synth = focus_audio.FocusAudioSynthesizer(mock=True)
        res = synth.play("rain", duration_sec=1.0)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["backend"], "mock")

    def test_cli_list_presets(self):
        test_args = ["focus_audio.py", "--list-presets", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = focus_audio.main()
            self.assertEqual(exit_code, 0)

    def test_cli_synthesize_preset_mock(self):
        test_args = ["focus_audio.py", "--preset", "brown_noise", "--duration", "0.5", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = focus_audio.main()
            self.assertEqual(exit_code, 0)

    def test_cli_export_wav_mock(self):
        with tempfile.TemporaryDirectory(prefix="mios-focus-cli-") as tmpdir:
            out_file = os.path.join(tmpdir, "ocean.wav")
            test_args = ["focus_audio.py", "--preset", "ocean", "--out", out_file, "--mock", "--json"]
            with patch.object(sys, "argv", test_args):
                exit_code = focus_audio.main()
                self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFocusAudio)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
