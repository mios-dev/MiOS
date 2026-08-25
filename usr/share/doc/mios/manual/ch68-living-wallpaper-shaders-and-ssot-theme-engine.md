<!-- AI-hint: Chapter 68: Living Wallpaper WebGL Shaders, FOSS Licensing & Real-Time Theme Synchronization. -->
# <a name="68_living_wallpaper_shaders_and_ssot_theme_engine"></a>Chapter 68: Living Wallpaper WebGL Shaders, FOSS Licensing & Real-Time Theme Synchronization

> Part I: User Experience & Theming of the [MiOS manual](../manual.md).
> Path Reference: `/usr/share/doc/mios/manual.md#68_living_wallpaper_shaders_and_ssot_theme_engine`

#### Overview

Under Architectural Law 8 (SSOT-AS-SYSTEM-DOTFILES / ADR-0010), `mios.toml` is the single source of truth projecting visual appearance, palettes, and dotfiles across Linux, Windows, and virtualized surfaces.

#### <a name="68_living_wallpaper_shader"></a>68.1 GPU-Accelerated Living Wallpaper Shaders

* **Self-Authored Shaders**: 40-line zero-dependency WebGL/WGSL shaders running on Mesa Vulkan iGPUs.
* **FOSS License Filter**: Strictly enforces OSI compliance; packages with Commons Clause or commercial restrictions (e.g. `neat`) are disqualified.
* **System Load Adaptation**: Wallpaper wave velocity and particle dynamics adapt in real-time to host CPU and GPU utilization uniforms (`u_load`, `u_speed`).
* **Degrade-Open Ladder**: Animated GPU shader $	o$ static SSOT gradient JPG $	o$ solid accent color.

#### <a name="68_live_theme_sync"></a>68.2 Real-Time Multi-Surface Theme Synchronization

When the operator changes palette colors in the Portal (`:8640/`):
1. Updates write to PostgreSQL and materialize `mios.toml`.
2. `mios-theme-render` projects GTK CSS, Windows Registry entries, and terminal configs.
3. SIGHUP signals reload running daemons (tmux, btop, Hyprland).
4. WebGL uniform updates stream over IPC to `mios-wallpaperd` for instant visual transition with zero application restarts.
