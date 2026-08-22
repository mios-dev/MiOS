<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: The MISSING USB staging bridge...

!/usr/bin/env bash
AI-hint: The MISSING USB staging bridge -- stages every built immutable-MiOS artifact (oci-archive tar, Anaconda-bootc installer ISO, raw/qcow2/vhdx disk images, the mios.toml brain) onto a MiOS-Cat-prepared Ventoy USB (MiOS-Repo + MiOS-Data), resolving partition labels from mios.toml [cat.*] via the shared mios-common.sh resolver, and renders the from-SSOT loopback boot menu so one USB offline-installs the REAL bootc image. Zero-network; idempotent; degrade-open on single-partition sticks. Companion/caller-restorer for tools/install.sh + usr/libexec/mios/mios-stage-oci-archive.
AI-related: installation/mios-common.sh, tools/install.sh, usr/libexec/mios/mios-stage-oci-archive, cat/loopback.cfg, usr/share/mios/ventoy/ventoy.json, Justfile, usr/share/mios/mios.toml [cat.repo_partition]/[cat.data_partition]/[deploy.artifacts]
MIOS_INSTALLER_ROLE=usb-artifact-stager

<!-- mios-src:f408d46a2d55 from installation/stage-mios-repo.sh:1-4 -->

