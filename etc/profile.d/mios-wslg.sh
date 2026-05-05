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

# XDG_RUNTIME_DIR: WSLg's default of /mnt/wslg/runtime-dir is a 9p mount
# from the Windows host and does not support sticky-bit chmod. Rootless
# podman creates $XDG_RUNTIME_DIR/libpod with the sticky bit and crashes
# with "set sticky bit on: chmod ... operation not permitted" if pointed
# there. mios-wsl-runtime-dir.service pre-creates /run/user/$UID on a
# real tmpfs; prefer it when present, fall back to the WSLg dir only if
# the service hasn't run (early-boot interactive shells).
if [ -d "/run/user/$(id -u)" ]; then
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    # If we landed in /mnt/wslg/runtime-dir from an outer login that
    # exported it before this script ran, swap it out -- podman will
    # crash otherwise.
    case "$XDG_RUNTIME_DIR" in
        /mnt/wslg/*) export XDG_RUNTIME_DIR="/run/user/$(id -u)" ;;
    esac
else
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/mnt/wslg/runtime-dir}"
fi
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DISPLAY="${DISPLAY:-:0}"
export PULSE_SERVER="${PULSE_SERVER:-/mnt/wslg/PulseServer}"

# DBUS_SESSION_BUS_ADDRESS: pam_systemd would normally set this to the
# user@$UID.service bus socket on a real login. WSL's `wsl -u root` ->
# `su - mios` chain bypasses PAM so the var is unset. libportal then
# tries to autolaunch a session bus via the X11 cookie, which fails with
# "Cannot autolaunch D-Bus without X11 $DISPLAY", taking down xdg-desktop-
# portal (and dconf-service, which is dbus-activated through the same
# bus) for every flatpak / GTK app. mios-wsl-runtime-dir.service starts
# user@$UID.service so the bus socket exists -- this just exports the
# address so apps can find it.
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

# WSLg sets WSL_INTEROP via /init for the outer ns; the nested ns may
# lose it. Re-derive from /run/WSL/<pid>_interop if present so
# explorer.exe / wslpath etc. still work from the nested shell.
if [ -z "${WSL_INTEROP:-}" ]; then
    _wsl_interop="$(find /run/WSL/ -maxdepth 1 -name '*_interop' 2>/dev/null | head -n1)"
    [ -n "$_wsl_interop" ] && export WSL_INTEROP="$_wsl_interop"
    unset _wsl_interop
fi
