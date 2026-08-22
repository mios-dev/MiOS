<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Proves role-apply's five-tier...

!/usr/bin/env bash
AI-hint: Proves role-apply's five-tier role ladder against fixtures, running the REAL functions extracted from the shipped script. Guards the regression the karg producer introduced: usr/lib/bootc/kargs.d/05-mios-blade.toml puts mios.blade= on EVERY cmdline, so the old `if [[ -z "$ROLE" ]]` guard made /etc/mios/role.conf, its FEATURES and the hardware demotion permanently unreachable -- `mios blade set` did nothing and `mios blade add-capability` was wiped on the next boot, because role-apply clears /etc/mios/blade.d each run.
AI-related: usr/libexec/mios/role-apply, usr/libexec/mios/mios-blade, usr/lib/bootc/kargs.d/05-mios-blade.toml, usr/share/mios/mios.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md

<!-- mios-src:ee6a04484404 from tests/test-role-apply-precedence.sh:1-3 -->

