<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Proves the greenboot AI-plane...

!/usr/bin/env bash
AI-hint: Proves the greenboot AI-plane check skips a unit this blade does not activate. `systemctl is-enabled` reports INSTALLATION, not whether a unit will start -- Condition* is evaluated at start time, so a capability-skipped unit still reads enabled (a Quadlet unit reads "generated", also exit 0). Without the marker guard a seat probes ports nothing is listening on, fails the required check and rolls itself back on every boot. Runs the real _blade_activates against a real fixture tree; no systemd needed.
AI-related: usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh, usr/libexec/mios/role-apply, usr/share/mios/mios.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md

<!-- mios-src:3a4fe7dab3fa from tests/test-greenboot-blade-guard.sh:1-3 -->

