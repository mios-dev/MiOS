<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd user service providing the dual MCP/A2A and HTTP-executor interface for the local Wayland session, enabling the agent-pipe to consume desktop capabilities like mouse/keyboard control and screen scraping.
AI-doc: usr/share/doc/mios/manual/user.md

<!-- mios-src:38a819dab796 from usr/lib/systemd/user/mios-computer-use-server.service:1-2 -->

### AI-hint

AI-hint: Systemd user unit for the mios-launcher-daemon; acts as a privileged broker that listens on a Unix socket to execute GUI applications with the operator's environment (WSLg/Wayland) for agents lacking execution rights.
AI-doc: usr/share/doc/mios/manual/user.md

<!-- mios-src:ddda916972e2 from usr/lib/systemd/user/mios-launcher.service:1-2 -->

### AI-hint

AI-hint: A systemd user service that imports WSLg environment variables (DISPLAY, WAYLAND_DISPLAY, XDG_SESSION_CLASS) into the systemd user-bus and dbus to enable GUI portal functionality and Flatpak integration in WSL.
AI-doc: usr/share/doc/mios/manual/user.md

<!-- mios-src:743aa5a4a788 from usr/lib/systemd/user/mios-wsl-env-import.service:1-2 -->

### !/usr/bin/env python3 AI-hint: Network-wide roaming...

!/usr/bin/env python3
AI-hint: Network-wide roaming multi-seat session orchestrator and GPU assignment manager.
AI-related: tests/test-roaming-seat.py, usr/lib/systemd/system/mios-seat-router.service
AI-functions: GPUDevice, SeatAssignment, UserRegistry, GPUManager, LogindSeatManager, CephFSMountManager, RoamingSeatOrchestrator, main

<!-- mios-src:62912124168a from usr/libexec/mios/user/roaming_seat.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Dynamic cross-node Wayland...

!/usr/bin/env python3
AI-hint: Dynamic cross-node Wayland session checkpoint and migration protocol.
AI-related: tests/test-session-migrate.py
AI-functions: WindowDescriptor, SessionCheckpoint, WaylandCompositorBridge, SessionCheckpointStore, SessionMigrateEngine, main

<!-- mios-src:7ea515ee24dd from usr/libexec/mios/user/session_migrate.py:1-4 -->
