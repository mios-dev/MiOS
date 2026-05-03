#!/bin/bash
# WSLg display environment for login shells in WSL2.
[[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi "microsoft" /proc/version 2>/dev/null || return 0
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
# WSLg supplies a Wayland socket via /mnt/wslg/. GTK apps refuse to start
# without XDG_SESSION_TYPE set ("Unsupported or missing session type ''").
# pam_systemd would set this for a proper logind session; under WSLg there
# is no PAM session, so set it here as a fallback.
export XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-wayland}"
# logind creates /run/user/<uid> and pam_systemd exports XDG_RUNTIME_DIR.
# WSL bypasses PAM at login, so populate the var if logind made the dir
# but the env var is unset.
if [[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/$(id -u)" ]]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi
if [[ -d /mnt/wslg/.X11-unix && ! -e /tmp/.X11-unix ]]; then
    ln -sf /mnt/wslg/.X11-unix /tmp/.X11-unix 2>/dev/null || true
fi
