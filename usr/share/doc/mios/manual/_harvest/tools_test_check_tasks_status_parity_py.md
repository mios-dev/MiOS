<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-tasks-status-parity.py. Builds throwaway TASKS.md files and asserts every direction the real drift produced: agreeing surfaces pass, a table cell that disagrees with the task section FAILS, a '?' placeholder fails whenever a section can answer it, both `## T-1 -- Title` and `## T-1: Title` heading styles are parsed, a free-prose status is compared on its head token only (so `done -- long explanation` still matches `done`), an unknown status word fails on either surface, and a task section with no summary row fails. Run: python3 test_check-tasks-status-parity.py
AI-related: ./check-tasks-status-parity.py, TASKS.md
AI-functions: check, mkrepo, run, main

<!-- mios-src:83b0bb23f630 from tools/test_check-tasks-status-parity.py:1-4 -->

