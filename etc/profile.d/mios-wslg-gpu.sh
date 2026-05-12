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

# ── Mesa / GTK4: cairo + llvmpipe is the WSLg default ────────────
# Operator-tested across multiple sessions 2026-05-10: every
# hardware path (dzn Vulkan, d3d12 Gallium, NGL, GL renderer)
# resulted in either:
#   (a) Apps spawning windows then crashing on GLib G_IS_OBJECT
#       assertions or "Could not initialize EGL display"
#   (b) WebKit "Web process crashed" in tight respawn loops
#   (c) Windows registering with weston RDP rail but never
#       displaying content on the Windows host
# Cairo + LIBGL_ALWAYS_SOFTWARE=1 + llvmpipe is the only combo
# that reliably produces stable, non-crashing GTK4 apps on WSLg
# with current Mesa 25 / dzn / GTK 4.16+ versions. Slow but
# correct. Per-flatpak overrides at /var/lib/flatpak/overrides/
# pin the same env inside flatpak sandboxes (which don't inherit
# this profile.d).
#
# When upstream WSLg + Mesa stabilize, flip MIOS_GPU_HARDWARE=1
# to opt back into the hardware path. Empty / unset = software.
if [ "${MIOS_GPU_HARDWARE:-0}" = "1" ]; then
    # Hardware-accelerated path: skip the software defaults and
    # let GTK4 / Mesa pick their own. Operator ack of expected
    # instability on current WSLg versions.
    export LIBGL_KOPPER_DISABLE="${LIBGL_KOPPER_DISABLE:-1}"
else
    # Software path -- the default.
    export GSK_RENDERER="${GSK_RENDERER:-cairo}"
    export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
    export GALLIUM_DRIVER="${GALLIUM_DRIVER:-llvmpipe}"
    export LIBGL_KOPPER_DISABLE="${LIBGL_KOPPER_DISABLE:-1}"
fi

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

# ── GTK / Qt scaling on 4K Windows hosts ──────────────────────────
# Restored 2026-05-12 after a regression: removing these broke the
# operator-tuned visual sizing that had previously been working.
# Per the original comment, WSLg compounds the Windows host's DPI
# scale (1.25-1.5 on 4K laptops) with its own scale, so without a
# fractional GDK_DPI_SCALE every GTK4 / libadwaita app renders ~25%
# too large vs the Windows-native baseline.
#
# Two cooperating knobs:
#   * GDK_DPI_SCALE -> 0.60: fractional DPI scale matching the
#     operator's visual benchmark
#   * QT_FONT_DPI   -> 58 (~60% of GDK's default 96 px-per-em)
export GDK_DPI_SCALE="${GDK_DPI_SCALE:-0.60}"
export QT_FONT_DPI="${QT_FONT_DPI:-58}"
export XCURSOR_SIZE="${XCURSOR_SIZE:-16}"
export XCURSOR_THEME="${XCURSOR_THEME:-Bibata-Modern-Classic}"

# ── Vulkan ICD ──────────────────────────────────────────────────
# WSLg ships dzn at /usr/share/vulkan/icd.d/dzn_icd.x86_64.json.
# We don't unset it -- apps that explicitly request Vulkan can
# still use it (and may work for compute / non-graphical workloads).
# But we don't make it the GTK / GL default.
:
