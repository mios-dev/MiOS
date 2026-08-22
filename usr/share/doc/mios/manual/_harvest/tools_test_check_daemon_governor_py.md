<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-daemon-governor.py: builds throwaway daemon/SSOT/chat trees in a temp dir and asserts the gate passes a complete governor and fails an ungated autonomous loop, a declared-but-unconsumed SSOT knob, a knob only NAMED in a comment or a test file, and a budget fallback that drifted more permissive than the SSOT.
AI-related: tools/check-daemon-governor.py, usr/libexec/mios/mios-daemon, usr/share/mios/mios.toml

<!-- mios-src:5251a939ae2b from tools/test_check-daemon-governor.py:1-3 -->

