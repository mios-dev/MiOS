#!/usr/bin/env bash
# AI-hint: Verification wrapper for WebRTC streaming audio ingress and streaming Whisper STT bridge (T-533, AGY-2131).
# AI-doc: usr/share/doc/mios/manual/ch78-streaming-audio-whisper.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_TEST="${SCRIPT_DIR}/test-audio-stream-whisper.py"

if [[ ! -f "${PYTHON_TEST}" ]]; then
    echo "[TEST] Error: ${PYTHON_TEST} not found" >&2
    exit 1
fi

exec python3 "${PYTHON_TEST}" "$@"
