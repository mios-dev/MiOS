<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Proves ADR-0016 D5 -- a seat's...

!/usr/bin/env bash
AI-hint: Proves ADR-0016 D5 -- a seat's front door is off-box by design, so that is where [security].api_require_auth and principal_bind_mode stop being optional. Runs the real _auth_posture from blade.sh against fixture /etc overlays, so no host and no live endpoint are needed. Pins that the verdict is DEGRADE-OPEN: an exposed seat still resolves a role and boots, it is merely told. Also pins that a loopback front door is 'local' regardless of the flags, because a hosted single-tenant blade needs no key -- turning the controls on by default there would demand a caller key nothing has provisioned.
AI-related: usr/lib/mios/blade.sh, usr/libexec/mios/role-apply, usr/share/mios/mios.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md, tests/test-offload-overlay.py
AI-functions: log, die, ok, posture, verdict, detail

<!-- mios-src:badcba5a798a from tests/test-seat-auth-posture.sh:1-4 -->

