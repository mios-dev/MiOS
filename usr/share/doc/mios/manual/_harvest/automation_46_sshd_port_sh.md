<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: Configures the host's admin sshd to bind to the SSOT port defined in mios.toml by creating a drop-in config in /etc/ssh/sshd_config.d/ to avoid port conflicts with Forgejo's git-ssh.
AI-related: mios-forge, mios-ssh-port, mios-forge.container

<!-- mios-src:7bd4f590f328 from automation/46-sshd-port.sh:1-4 -->

