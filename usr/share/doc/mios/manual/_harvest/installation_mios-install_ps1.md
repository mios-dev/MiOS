<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Consolidated installer surface

Consolidated installer surface: EVERY install/build target comes WITH the live monitor.
Launch mios mon (the unified TUI) in its own window so the operator watches the whole
pipeline live -- matches MiOS-Cat.bat's ensure_live_monitor. The 'monitor' target itself and
the early-exit special targets (configure/repos/update) never reach here. Suppressed by
MIOS_NO_MONITOR=1 (headless/CI/nested).

<!-- mios-src:609860203db5 from installation/mios-install.ps1:255-259 -->
