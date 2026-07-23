#!/usr/bin/env bash
# AI-hint: MiOS live system dashboard shim. Forwards to the unified Python TUI.
if ! python3 -c "import rich" 2>/dev/null; then
    echo "Bootstrapping required python TUI library 'rich'..." >&2
    pip3 install --user --break-system-packages rich >/dev/null 2>&1 || pip3 install --user rich >/dev/null 2>&1
fi
exec python3 /usr/libexec/mios/MiOS-Mon.py "$@"
