# /etc/profile.d/mios-wslg-gpu.sh
#
# WSLg GUI rendering env. Without this, GTK4 + Mesa default to
# Vulkan-via-Zink-via-dzn (DirectX-to-Vulkan bridge on WSLg) --
# but dzn is non-conformant and missing features Zink requires
# (nullDescriptor, robustness2, descriptor pool memory). Result:
# the app's Wayland surface registers with weston RDP rail (the
# Windows taskbar shows the icon), but the frame buffer can never
# initialize. Operator-visible failure mode 2026-05-10: "the
# windows never render though--there's an icon on the windows
# taskbar but no actual window EVER rendered."
#
# Solution: force Mesa onto the d3d12 Gallium driver (translates
# OpenGL calls to Direct3D 12 -> goes through /dev/dxg -> real GPU
# acceleration on the Windows host), and tell GTK4's GSK to use
# its GL renderer instead of the Vulkan one. dzn stays available
# for apps that explicitly want it, but isn't the default.
#
# Gated on /mnt/wslg presence -- inert outside WSLg (bare-metal /
# Hyper-V / QEMU / OCI keep their canonical Mesa+Vulkan path).
#
# Compatible with bash, sh, zsh, dash login shells -- no bashisms.

[ -d /mnt/wslg ] || return 0

# ── Cairo / software-rendering fallback toggle ───────────────────
# Set MIOS_GPU_SOFTWARE=1 to force CPU-only rendering (cairo +
# llvmpipe). Slow but always produces visible content -- useful
# when dzn / d3d12 / NVIDIA paths are all failing for a specific
# app. Operator can flip per-shell or persist via
# ~/.config/environment.d/. Default (unset) = hardware-accelerated
# d3d12 path below.
if [ "${MIOS_GPU_SOFTWARE:-0}" = "1" ]; then
    export GALLIUM_DRIVER="${GALLIUM_DRIVER:-llvmpipe}"
    export LIBGL_ALWAYS_SOFTWARE=1
    export GSK_RENDERER="${GSK_RENDERER:-cairo}"
    return 0 2>/dev/null || exit 0
fi

# ── Mesa / GL ────────────────────────────────────────────────────
# d3d12 = the Mesa Gallium driver that targets WSLg's WDDM via
# /dev/dxg. Far more reliable than dzn (Vulkan) for typical GTK
# workloads. The MESA_LOADER override forces Mesa's loader to
# pick the d3d12 driver even when its auto-detection fails (which
# it does on WSLg because /dev/dri/* devices don't exist).
export GALLIUM_DRIVER="${GALLIUM_DRIVER:-d3d12}"
export MESA_LOADER_DRIVER_OVERRIDE="${MESA_LOADER_DRIVER_OVERRIDE:-d3d12}"
# Mesa-25+ replaced the old DRI2 path with Kopper for X-on-Vulkan;
# Kopper on WSLg goes through Zink which goes through dzn -- so
# disable Kopper to keep GL apps on the d3d12 path.
export LIBGL_KOPPER_DISABLE="${LIBGL_KOPPER_DISABLE:-1}"

# ── GTK4 ─────────────────────────────────────────────────────────
# GTK4's default GSK_RENDERER on >= 4.14 is "ngl" (preferring
# Vulkan). On WSLg with dzn broken that renders to a 0x0 surface.
# Force "gl" (the OpenGL renderer that uses GALLIUM_DRIVER=d3d12
# above). "cairo" is the software fallback if d3d12 also fails.
export GSK_RENDERER="${GSK_RENDERER:-gl}"

# ── WebKit (Epiphany / GNOME-Web) ───────────────────────────────
# WebKit's accelerated compositing path tries Vulkan first too.
# Disabling AC mode keeps WebKit on the GL path which honors
# GALLIUM_DRIVER=d3d12.
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"

# ── Wayland defaults ─────────────────────────────────────────────
# WSLg sets WAYLAND_DISPLAY=wayland-0 and stages the socket at
# /mnt/wslg/runtime-dir/wayland-0 (symlinked into $XDG_RUNTIME_DIR).
# These are usually already exported by WSL's init -- export them
# defensively so apps launched from non-login shells (cron, dbus
# activation) still find them.
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
[ -n "${XDG_RUNTIME_DIR:-}" ] || export XDG_RUNTIME_DIR="/run/user/$(id -u 2>/dev/null || echo 1000)"

# ── X11 fallback (XWayland) ──────────────────────────────────────
# Some apps (older Qt5 utilities) still want X11. WSLg provides
# XWayland at /tmp/.X11-unix/X0 -- ensure DISPLAY points there.
export DISPLAY="${DISPLAY:-:0}"

# ── Vulkan ICD ──────────────────────────────────────────────────
# WSLg ships dzn at /usr/share/vulkan/icd.d/dzn_icd.x86_64.json.
# We don't unset it -- apps that explicitly request Vulkan can
# still use it (and may work for compute / non-graphical workloads).
# But we don't make it the GTK / GL default.
:
