<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Self-contained test harness for...

!/usr/bin/env bash
AI-hint: Self-contained test harness for automation/97-ssot-lint.sh -- builds throwaway fixture trees (a fully-wired key, a both-sides orphan, a userenv-only and a render-only half-orphan) to assert the lint's PASS/FAIL exit codes and orphan detection, then asserts it flags the real known dead key (MIOS_SGLANG_TOOL_PARSER) in the live repo tree.
AI-related: ../97-ssot-lint.sh, ../34-render-quadlets.sh, ../../tools/lib/userenv.sh, ../../usr/share/containers/systemd
AI-functions: _mk_fixture, _expect, main

<!-- mios-src:a64282216d09 from automation/tests/test-97-ssot-lint.sh:1-4 -->

