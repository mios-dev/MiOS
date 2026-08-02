# AI-hint: Configures Mesa and GTK4 rendering paths for WSLg environments, forcing software fallback or d3d12 Gallium acceleration to ensure stable window rendering when the default Vulkan-via-Zink path fails.
# AI-related: mios-wslg-gpu

[ -d /mnt/wslg ] || return 0

if [ "${MIOS_GPU_HARDWARE:-0}" = "1" ]; then
    export LIBGL_KOPPER_DISABLE="${LIBGL_KOPPER_DISABLE:-1}"
else
    export GSK_RENDERER="${GSK_RENDERER:-cairo}"
    export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
    export GALLIUM_DRIVER="${GALLIUM_DRIVER:-llvmpipe}"
    export LIBGL_KOPPER_DISABLE="${LIBGL_KOPPER_DISABLE:-1}"
fi

export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
[ -n "${XDG_RUNTIME_DIR:-}" ] || export XDG_RUNTIME_DIR="/run/user/$(id -u 2>/dev/null || echo 1000)"

export DISPLAY="${DISPLAY:-:0}"

export GDK_DPI_SCALE="${GDK_DPI_SCALE:-0.60}"
export QT_FONT_DPI="${QT_FONT_DPI:-58}"
export XCURSOR_SIZE="${XCURSOR_SIZE:-16}"
export XCURSOR_THEME="${XCURSOR_THEME:-Bibata-Modern-Classic}"

:
