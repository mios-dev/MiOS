<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Audio feedback daemon...

!/usr/bin/env python3
AI-hint: Audio feedback daemon playing subtle non-intrusive sound cues with pure Python PCM synthesis
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: AudioFeedbackEngine, synthesize_event_pcm, play_audio_cue, main

<!-- mios-src:327419454e53 from usr/libexec/mios/ux/audio_feedback.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Secret-redacting...

!/usr/bin/env python3
AI-hint: Secret-redacting cross-platform clipboard synchronizer between host Wayland/X11 and guest VMs.
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/systemd/user/mios-clipboard-sync.service
AI-functions: ClipboardSyncEngine, RedactionRule, RedactionResult, main

<!-- mios-src:d1873e7db60f from usr/libexec/mios/ux/clipboard_sync.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Interactive CLI and...

!/usr/bin/env python3
AI-hint: Interactive CLI and Quickshell diff auditor enabling operator inspection, approval, rejection, and bake staging.
AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md, usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md, tests/test-ux.py
AI-functions: DiffAuditorEngine, atomic_write_json, main

<!-- mios-src:694128c0f3a1 from usr/libexec/mios/ux/diff_auditor.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Fastfetch configuration...

!/usr/bin/env python3
AI-hint: Fastfetch configuration generator projecting host hardware, bootc image and AI model specs into JSONC
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: FastfetchGenEngine, generate_fastfetch_jsonc, main

<!-- mios-src:bd0904636fa5 from usr/libexec/mios/ux/fastfetch_gen.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Interactive and headless...

!/usr/bin/env python3
AI-hint: Interactive and headless first-boot onboarding wizard for credentials, Wi-Fi & AI lanes
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/libexec/mios/net/nm_preseed.py
AI-functions: FirstBootWizardEngine, WizardState, WizardConfig, run_wizard

<!-- mios-src:57cf53b75b36 from usr/libexec/mios/ux/firstboot_wizard.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Dynamic font size scaler for...

!/usr/bin/env python3
AI-hint: Dynamic font size scaler for High-DPI displays calculating font metrics and fontconfig XML rules.
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, /usr/share/mios/themes/fonts.conf
AI-functions: FontScalerEngine, DisplayMetrics, ScaledFontConfig, main

<!-- mios-src:23f8f3682a5c from usr/libexec/mios/ux/font_scaler.py:1-4 -->

### !/usr/bin/env python3 AI-hint: GNOME Shell extension...

!/usr/bin/env python3
AI-hint: GNOME Shell extension generator, validator, and manager embedding MiOS agent status in the top panel.
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, /usr/share/gnome-shell/extensions/mios-status@mios-dev.org/
AI-functions: GnomeExtensionManager, main

<!-- mios-src:149c317f5fb0 from usr/libexec/mios/ux/gnome_extension.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Real-time living wallpaper...

!/usr/bin/env python3
AI-hint: Real-time living wallpaper GLSL/WGSL fragment shader renderer with CPU/GPU telemetry modulation
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: LivingWallpaperEngine, TelemetrySnapshot, hex_to_rgb_norm, main

<!-- mios-src:1a2267800c41 from usr/libexec/mios/ux/living_wallpaper.py:1-4 -->

### !/usr/bin/env python3 AI-hint: System notification daemon...

!/usr/bin/env python3
AI-hint: System notification daemon routing agent-pipe / Hermes alerts and HITL approvals to desktop toasts
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: NotificationDaemonEngine, NotificationMessage, send_desktop_notification, main

<!-- mios-src:5a3adc765247 from usr/libexec/mios/ux/notification_daemon.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Quickshell / QML system...

!/usr/bin/env python3
AI-hint: Quickshell / QML system status bar component streaming live LLM VRAM, tokens/sec and agent turns
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: StatusBarEngine, StatusBarState, generate_qml_component, main

<!-- mios-src:a15a7fe14813 from usr/libexec/mios/ux/status_bar.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Cross-platform palette...

!/usr/bin/env python3
AI-hint: Cross-platform palette synchronizer writing directly to Windows Registry (.reg) and GTK 3/4 CSS
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: ThemeSyncEngine, hex_to_dword_bgr, generate_reg_content, generate_gtk3_css, generate_gtk4_css, main

<!-- mios-src:c218fc91fed8 from usr/libexec/mios/ux/theme_sync.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Terminal multiplexer tmux...

!/usr/bin/env python3
AI-hint: Terminal multiplexer tmux theme generator deriving active pane styles and status bar formatting from SSOT
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: TmuxThemeEngine, generate_tmux_config, main

<!-- mios-src:a3d17ea3fd75 from usr/libexec/mios/ux/tmux_theme.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Window-occlusion aware...

!/usr/bin/env python3
AI-hint: Window-occlusion aware living wallpaper daemon with Vulkan compute priority queue and telemetry IPC socket.
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/libexec/mios/ux/living_wallpaper.py
AI-functions: WallpaperDaemonEngine, OcclusionDetector, VulkanComputeQueue, TelemetrySocketServer, send_socket_command, main

<!-- mios-src:446dfc0cf9a4 from usr/libexec/mios/ux/wallpaperd.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Hyprland and Sway tiling...

!/usr/bin/env python3
AI-hint: Hyprland and Sway tiling window manager configuration generator from SSOT with hot-reload support
AI-related: tests/test-ux.py, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py
AI-functions: WmConfigGenEngine, generate_hyprland_conf, generate_sway_config, trigger_wm_reload, main

<!-- mios-src:8a7d2c40bde7 from usr/libexec/mios/ux/wm_config_gen.py:1-4 -->
