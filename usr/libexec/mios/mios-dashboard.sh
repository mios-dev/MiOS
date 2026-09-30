#!/usr/bin/env bash
# AI-hint: MiOS live system dashboard shim. Forwards to the unified Python TUI.
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
exec python3 /usr/libexec/mios/mios-mon.py "$@"
