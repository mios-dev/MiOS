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
# Mesa-25+ replaced the old DRI2 path with Kopper for X-on-Vulkan;
# Kopper on WSLg goes through Zink which goes through dzn (broken
# for many GTK4 features) -- disable Kopper unconditionally to
# keep apps off the Zink path. This alone is non-destructive.
export LIBGL_KOPPER_DISABLE="${LIBGL_KOPPER_DISABLE:-1}"

# d3d12 Gallium driver targets WSLg's WDDM via /dev/dxg.
# Operator-tested 2026-05-10: forcing GALLIUM_DRIVER=d3d12 +
# GSK_RENDERER=gl made GTK4 apps spawn windows but they crashed
# shortly after on GLib G_IS_OBJECT assertions (Zink / dzn
# inconsistency in the GTK4 GL renderer's surface handling).
# Defaulting to MESA's auto-detection has proved more stable --
# the loader picks llvmpipe (CPU) when no real GPU surfaces, and
# GTK4's NGL renderer falls back to its own GL implementation.
# Operators on hosts where d3d12 IS reliable can opt back in:
#   export GALLIUM_DRIVER=d3d12
#   export MESA_LOADER_DRIVER_OVERRIDE=d3d12
#   export GSK_RENDERER=gl

# ── GTK4 / GSK ───────────────────────────────────────────────────
# Don't force GSK_RENDERER -- let GTK4 auto-detect. On WSLg with
# Mesa 25 the auto path picks NGL which works for most apps.
# When NGL fails (operator sees app-crash-shortly-after-spawn),
# flip to MIOS_GPU_SOFTWARE=1 (block above) for cairo + llvmpipe.

# ── WebKit (Epiphany / GNOME-Web) ───────────────────────────────
# WebKit-on-WSLg works best with hardware compositing disabled --
# the dzn path can't reliably back WebKit's compositing layers.
# Operators with a stable hardware path can unset to re-enable.
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
