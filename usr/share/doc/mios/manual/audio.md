<!-- AI-hint: Manual pages distilled from the source comments of audio, sanitized, each passage anchored to the comment it came from. -->

# audio

### MiOS Three-Stage Acoustic Wake-Word Engine. Architecture: -...

MiOS Three-Stage Acoustic Wake-Word Engine.

Architecture:
- Stage 1: RNNoise Denoiser (Acoustic spectral noise suppression & stationary floor tracking).
- Stage 2: Silero VAD (Zero-crossing, spectral entropy, formant ratio, harmonicity speech detection).
- Stage 3: OpenWakeWord Detector (Log-Mel feature extraction & acoustic wake-phrase classification).

Execution Pipeline:
Microphone PCM (16kHz 16-bit) -> [Stage 1: Denoise] -> [Stage 2: VAD]
                                                         | (if speech detected)
                                                         v
                                              [Stage 3: WakeWord Classifier]
                                                         | (if phrase matched)
                                                         v
                                              [Downstream Streaming STT Signal]

Features:
- Sub-0.1% CPU idle overhead via early VAD gating (Stage 3 bypassed during silence/noise).
- >98% accuracy on wake phrases with <0.5% false positive rate on ambient noise & speech.
- CLI flags: --status, --json, --process-pcm <path>, --threshold <float>, --mock, --daemon.
- Systemd user service: usr/lib/systemd/user/mios-wakeword.service.

<!-- mios-src:1139e3c1285c from usr/libexec/mios/audio/wakeword.py:5-27 -->

### Stage 2

Stage 2: Silero Voice Activity Detector.
    Evaluates speech presence via multi-feature acoustic analysis:
    - Pitch Autocorrelation / Harmonicity (80 - 400 Hz).
    - Speech Formant Band Energy (300 - 3400 Hz).
    - Spectral entropy & formant concentration.
    - Zero-Crossing Rate within speech bounds.

<!-- mios-src:cdd5f192adee from usr/libexec/mios/audio/wakeword.py:251-258 -->

### Process single audio frame through wake-word acoustic...

Process single audio frame through wake-word acoustic classifier.
        Evaluates 4 sequential phonetic acoustic stages with phonemic signature verification:
        1. /h/ + /eɪ/ ("Hey"): Mid-high formants F1 ~550Hz, F2 ~2000Hz (Mel bins 5..9 and 15..20).
        2. /m/ ("M"): Nasal murmur <350Hz (Mel bins 1..5, low formant energy in 8..18).
        3. /aɪ/ ("y"): Vowel transition (Mel bins 6..20).
        4. /ɒs/ ("OS"): High sibilance 5000-7000Hz (Mel bins 22..31).

<!-- mios-src:8d35c233c06e from usr/libexec/mios/audio/wakeword.py:374-381 -->

### Unified Three-Stage Acoustic Pipeline

Unified Three-Stage Acoustic Pipeline:
    1. RNNoiseSuppressor (denoiser)
    2. SileroVAD (voice activity detection)
    3. OpenWakeWordDetector (phrase classifier)

<!-- mios-src:ccac573db667 from usr/libexec/mios/audio/wakeword.py:487-492 -->

### Generate synthetic test audio signals

Generate synthetic test audio signals:
    - 'wake_phrase': Phonetic signature for 'Hey MiOS' (/heɪ/ -> /m/ -> /aɪ/ -> /ɒs/) with harmonic formants.
    - 'negative_speech': General non-wake human conversational speech.
    - 'ambient_noise': Stationary background microphone hiss & fan noise.
    - 'silence': Near zero ambient baseline.

<!-- mios-src:63a49ad75d47 from usr/libexec/mios/audio/wakeword.py:652-658 -->
