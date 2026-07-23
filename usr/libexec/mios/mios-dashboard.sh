#!/usr/bin/env bash
# AI-hint: MiOS live system dashboard shim. Forwards to the unified Python TUI.
if ! python3 -c "import rich, textual, psutil" 2>/dev/null; then
    echo "Bootstrapping required python TUI libraries (rich, textual, psutil)..." >&2
    pip3 install --user --break-system-packages rich textual psutil >/dev/null 2>&1 || pip3 install --user rich textual psutil >/dev/null 2>&1
fi
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
exec python3 /usr/libexec/mios/MiOS-Mon.py "$@"
