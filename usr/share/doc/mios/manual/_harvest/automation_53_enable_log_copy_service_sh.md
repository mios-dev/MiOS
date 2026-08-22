<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=bake-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=bake-only
AI-hint: Enables the mios-copy-build-log.service systemd unit by creating a symbolic link in multi-user.target.wants to ensure build logs are automatically copied during system startup.
AI-related: mios-copy-build-log, mios-copy-build-log.service, multi-user.target

<!-- mios-src:b44595063196 from automation/53-enable-log-copy-service.sh:1-4 -->

