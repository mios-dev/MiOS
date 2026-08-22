<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Proves ADR-0016 D8 -- a seat's...

!/usr/bin/env bash
AI-hint: Proves ADR-0016 D8 -- a seat's blade reachability is RECORDED on every boot and is not critical unless [greenboot].blade_reachability_critical says so. Extracts the real _blade_reachable/_endpoint_host_port from the shipped greenboot check and runs them against a REAL listening socket on an ephemeral port, plus a port nothing is on. The case that matters is the negative one: an unreachable blade must leave rc=0, because rolling a seat back over another machine's outage fixes nothing.
AI-related: usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh, usr/libexec/mios/role-apply, usr/share/mios/mios.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md
AI-functions: log, die, ok, hostport

<!-- mios-src:8213217871f5 from tests/test-greenboot-blade-reachability.sh:1-4 -->

