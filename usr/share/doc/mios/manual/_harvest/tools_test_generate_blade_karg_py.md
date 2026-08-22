<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for...

!/usr/bin/env python3
AI-hint: Unit tests for tools/generate-blade-karg.py. Assert the projection refuses an empty [blade].type and a type naming no archetype -- both would emit a karg selecting nothing -- and that the shipped file matches what render() produces, which is what makes it a projection rather than a hand-edited drop-in.
AI-related: tools/generate-blade-karg.py, usr/lib/bootc/kargs.d/05-mios-blade.toml, usr/share/mios/mios.toml

<!-- mios-src:2988a9f741db from tools/test_generate-blade-karg.py:1-3 -->

