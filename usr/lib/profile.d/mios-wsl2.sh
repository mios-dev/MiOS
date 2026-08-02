#!/bin/bash
# AI-hint: Configures WSL2 graphics environment variables (DISPLAY, WAYLAND_DISPLAY, XDG_SESSION_TYPE) and XDG_RUNTIME_DIR to enable GUI application support and X11/Wayland compatibility for MiOS on WSLg.
[[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi "microsoft" /proc/version 2>/dev/null || return 0
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-wayland}"
if [[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/$(id -u)" ]]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi
if [[ -d /mnt/wslg/.X11-unix && ! -e /tmp/.X11-unix ]]; then
    ln -sf /mnt/wslg/.X11-unix /tmp/.X11-unix 2>/dev/null || true
fi
