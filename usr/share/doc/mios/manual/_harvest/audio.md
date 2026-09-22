<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Three-stage acoustic filter...

!/usr/bin/env python3
AI-hint: Three-stage acoustic filter chain (RNNoise denoiser, Silero VAD, OpenWakeWord phrase detector) for hands-free activation
AI-related: tests/test-acoustic-wakeword-pipeline.py, usr/lib/systemd/user/mios-wakeword.service, usr/share/mios/mios.toml
AI-functions: RNNoiseSuppressor, SileroVAD, OpenWakeWordDetector, AcousticWakePipeline, process_pcm_file, synthesize_test_audio, main

<!-- mios-src:2e7a147930e6 from usr/libexec/mios/audio/wakeword.py:1-4 -->
