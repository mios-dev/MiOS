<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Coverage test for...

!/usr/bin/env bash
AI-hint: Coverage test for automation/lint-python.sh. Asserts the gate actually SEES a representative Python file from every payload area -- not that the tree is clean, but that the gate is looking at it. Enumerating directories one at a time is what left usr/share/mios unscanned while the canonical OWUI pipe did not import; this test fails if any area drops out of the file set again. Also asserts the two deliberate exclusions still hold: rendered templates (which carry {{placeholders}}) and the mios-dashboard zipapp (executable Python, not Python source).
AI-related: automation/lint-python.sh, usr/share/mios/owui/pipes/mios_agent_pipe.py, usr/libexec/mios/mios-dashboard

<!-- mios-src:d57249cc05c6 from tests/test-lint-python-coverage.sh:1-3 -->

