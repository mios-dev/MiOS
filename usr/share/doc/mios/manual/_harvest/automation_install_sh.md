<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash...

!/usr/bin/env bash
MIOS_INSTALLER_ROLE=container-build-installer
AI-hint: Thin redirector to install-fhs.sh -- the single FHS-overlay installer for non-bootc Fedora hosts (rsyncs usr/etc/var/srv onto /, materializes /v1, runs sysusers/tmpfiles, reloads systemd). install.sh and install-fhs.sh were byte-identical; deduped to ONE implementation. Superseded by `mios-apply fhs-host` once the unified git=$ROOT engine lands.

<!-- mios-src:3b89614343c1 from automation/install.sh:1-3 -->

