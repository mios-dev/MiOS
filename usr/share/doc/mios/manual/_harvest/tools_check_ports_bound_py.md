<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for...

!/usr/bin/env python3
AI-hint: Drift gate for allocated-but-unbound ports. Every numeric [ports] key must be referenced as MIOS_PORT_<KEY> by a non-SSOT, non-doc, non-generated file, or sit in the shrink-only [ports].unbound register; a key in neither fails, and a registered key that IS referenced fails too, so the register only shrinks. An unbound key means the collision checker guards a number nothing binds while the bound number sits outside the SSOT.
AI-related: usr/share/mios/mios.toml, tools/test_check-ports-bound.py, automation/98-drift-checks.sh, tools/check-service-urls.py
AI-functions: port_keys, register, referenced_ports, classify, main

<!-- mios-src:e864071672de from tools/check-ports-bound.py:1-4 -->

