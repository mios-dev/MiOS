<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for service...

!/usr/bin/env python3
AI-hint: Drift gate for service addressing. Every numeric [ports] key must resolve to exactly one canonical address -- either a [urls] entry that templates its ${MIOS_PORT_*}, or membership of the shrink-only [urls].non_addressable register. A port in NEITHER fails the gate, so a new service cannot be added without stating how it is addressed; a port in BOTH fails too, because two answers is the problem this exists to prevent. The register only shrinks: a key leaves it by gaining a [urls] entry and can never be added back silently.
AI-related: usr/share/mios/mios.toml, tools/test_check-service-urls.py, automation/98-drift-checks.sh, usr/share/doc/mios/adr/0016-blade-node-topology.md
AI-functions: browser_openable, bare_port_addresses, covered_ports, port_keys, register, classify, main

<!-- mios-src:3e726a756332 from tools/check-service-urls.py:1-4 -->

