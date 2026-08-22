<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Initializes the Ceph cluster on...

!/usr/bin/env bash
AI-hint: Initializes the Ceph cluster on first boot by running cephadm bootstrap with single-host defaults and creating a sentinel file to prevent re-execution; use this to trigger or debug the initial Ceph cluster setup.
AI-related: mios-ceph-bootstrap, mios-ceph, ceph-bootstrap.service, mios-ceph-bootstrap.service
AI-functions: _log

<!-- mios-src:6223e75982b4 from usr/libexec/mios/ceph-bootstrap.sh:1-4 -->

