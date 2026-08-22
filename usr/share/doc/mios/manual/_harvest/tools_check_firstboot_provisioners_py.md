<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for the...

!/usr/bin/env python3
AI-hint: Drift gate for the first-boot provisioner triples (FBM T-200/T-202). Each provisioner must be WHOLE: the libexec fetcher exists and is the unit's ExecStart, the unit gates on the sentinel that fetcher writes (ConditionPathExists=!<sentinel>, spelled identically on both sides), a preset line enables it, and the /var dirs it writes are declared in tmpfiles.d rather than mkdir'd (Architectural Law 2). A half-wired triple looks installed and never runs -- the unit enabled with no fetcher, or a fetcher whose sentinel path the unit does not gate on, both fail silently at boot.
AI-related: usr/lib/systemd/system/mios-models-firstboot.service, usr/libexec/mios/mios-models-firstboot, usr/lib/systemd/system-preset/90-mios.preset, usr/lib/tmpfiles.d/, tools/test_check-firstboot-provisioners.py
AI-functions: tmpfiles_dirs, unit_field, check_one, main

<!-- mios-src:7908dbda9350 from tools/check-firstboot-provisioners.py:1-4 -->

