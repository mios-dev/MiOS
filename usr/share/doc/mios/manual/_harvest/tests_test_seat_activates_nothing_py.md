<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: The executable definition of...

!/usr/bin/env python3
AI-hint: The executable definition of MiOS-Mini. A seat is [blade].type = "endpoint", an archetype granting NO capabilities, so it must activate ZERO of the declared containers while every other archetype keeps exactly what it had. Resolves capability sets the way the drop-in fanout does -- a unit runs when its required markers are all present, since repeated ConditionPathExists is an AND -- and asserts the seat starts nothing, the non-seat roles are unchanged, and every capability a service requires is grantable by some archetype.
AI-related: usr/share/mios/mios.toml, tools/generate-blade-dropins.py, automation/48-mios-dropin-fanout.sh, usr/share/doc/mios/adr/0016-blade-node-topology.md

<!-- mios-src:304a5b44842e from tests/test-seat-activates-nothing.py:1-3 -->

