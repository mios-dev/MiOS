<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the WSL2-specific artifact configuration for the MiOS build system, specifying user account defaults and kernel parameters for the `wsl --import` workflow.
bib-configs/wsl2.toml - 'MiOS' v0.3.0
Target: Windows Subsystem for Linux 2 (WSL2)
Import with: wsl --import 'MiOS' <install-dir> output/disk.wsl2
BIB --type wsl2 emits a .tar.gz suitable for wsl --import.

<!-- mios-src:b0172e0c6d00 from config/artifacts/wsl2.toml:1-5 -->

