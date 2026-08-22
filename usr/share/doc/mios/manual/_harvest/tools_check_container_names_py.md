<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for unmappable...

!/usr/bin/env python3
AI-hint: Drift gate for unmappable container names. Quadlet names a container `systemd-<unit>` when the unit does not declare ContainerName, so `podman ps` and `systemctl` disagree about what a thing is called -- during an incident that turns "which unit is this container?" into guesswork. Every [containers.<name>.Container] block must declare ContainerName equal to its own unit name; a TEMPLATE unit (`name@`) must instead name the instantiated form `<base>-%i`, because a template has no single container. Checks the SSOT and the rendered .container files together, so neither side can drift alone.
AI-related: usr/share/mios/mios.toml, usr/share/containers/systemd/*.container, tools/generate-pod-quadlets.py, tools/test_check-container-names.py
AI-functions: expected_name, ssot_containers, rendered_containers, main

<!-- mios-src:36ae1803350c from tools/check-container-names.py:1-4 -->

