# /etc/profile.d/mios-wslg.sh
#
# Exports the env vars Wayland/X11 clients need to reach WSLg's compositor
# socket on Windows. Required because podman-machine WSL distros run a
# NESTED systemd namespace (per the welcome banner) -- the outer namespace
# mounts /mnt/wslg/, but the nested ns where the user's interactive shell
# lives doesn't auto-inherit DISPLAY/WAYLAND_DISPLAY/XDG_RUNTIME_DIR.
# Without this, flatpak GUI apps (Ptyxis, Nautilus, Epiphany, etc.) error
# with "Gdk-CRITICAL ... 'GDK_IS_DISPLAY (self)' failed" or "cannot open
# display:" the moment the operator launches them.
#
# Detection: /mnt/wslg/ is mounted by WSL2 host on every distro that has
# `guiApplications=true` in .wslconfig. Its presence is the unambiguous
# signal that we're running in a WSLg-capable distro and should wire the
# socket env. Inert on bare-metal / Hyper-V / QEMU MiOS hosts where that
# path doesn't exist.

[ -d /mnt/wslg ] || return 0

# Wayland socket: WSLg publishes wayland-0 inside /mnt/wslg/ which itself
# becomes XDG_RUNTIME_DIR's source. Some flatpak runtimes also need
# WAYLAND_DISPLAY pointing at the bare socket name.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/mnt/wslg/runtime-dir}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DISPLAY="${DISPLAY:-:0}"
export PULSE_SERVER="${PULSE_SERVER:-/mnt/wslg/PulseServer}"

# WSLg sets WSL_INTEROP via /init for the outer ns; the nested ns may
# lose it. Re-derive from /run/WSL/<pid>_interop if present so
# explorer.exe / wslpath etc. still work from the nested shell.
if [ -z "${WSL_INTEROP:-}" ]; then
    _wsl_interop="$(find /run/WSL/ -maxdepth 1 -name '*_interop' 2>/dev/null | head -n1)"
    [ -n "$_wsl_interop" ] && export WSL_INTEROP="$_wsl_interop"
    unset _wsl_interop
fi
