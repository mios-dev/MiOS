<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=bake-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=bake-only
AI-hint: Configures the `prepare-root.conf` file by reading the `[security].composefs_mode` setting from `mios.toml` to enable/disable fs-verity or standard composefs for the root filesystem.
AI-related: systemd-remount-fs.service
AI-functions: _read_mios_scalar

<!-- mios-src:045a91dfb64b from automation/77-composefs-verity.sh:1-5 -->

