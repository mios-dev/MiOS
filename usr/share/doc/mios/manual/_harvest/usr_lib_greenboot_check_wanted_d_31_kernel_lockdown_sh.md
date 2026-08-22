<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/bash AI-hint: Verifies the booted kernel enforces...

!/usr/bin/bash
AI-hint: Verifies the booted kernel enforces the lockdown mode the image kargs declare (`lockdown=integrity` in usr/lib/bootc/kargs.d), closing the gap where the karg is projection-checked at build but never confirmed on the running host; degrades open on kernels without the lockdown LSM (e.g. WSL2).

<!-- mios-src:fd3b3bf79803 from usr/lib/greenboot/check/wanted.d/31-kernel-lockdown.sh:1-2 -->

