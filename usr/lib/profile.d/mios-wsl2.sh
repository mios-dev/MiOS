#!/bin/bash
# WSLg display environment for login shells in WSL2.
[[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi "microsoft" /proc/version 2>/dev/null || return 0
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
if [[ -d /mnt/wslg/.X11-unix && ! -e /tmp/.X11-unix ]]; then
    ln -sf /mnt/wslg/.X11-unix /tmp/.X11-unix 2>/dev/null || true
fi
