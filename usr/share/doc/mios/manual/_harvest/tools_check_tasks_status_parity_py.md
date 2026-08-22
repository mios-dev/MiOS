<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Drift gate for a lying...

!/usr/bin/env python3
AI-hint: Drift gate for a lying roadmap. TASKS.md carries every task twice -- once as a row in the summary table and once as a `**Status:**` line in the task's own section -- and the two silently diverged in 49 places, including seven rows the table called done-by-code while the detail still said open and three P0 rows the table called done while the detail said planned. Whoever reads only one surface gets a different answer about what is left. This gate requires the table cell to equal the head token of the detail status (the text before the first ` -- ` or ` (`), so the two can never disagree again, and rejects the `?` placeholder outright wherever a detail section exists to answer it.
AI-related: TASKS.md, tools/test_check-tasks-status-parity.py, automation/98-drift-checks.sh
AI-functions: detail_statuses, table_rows, head_token, main

<!-- mios-src:82625fb69963 from tools/check-tasks-status-parity.py:1-4 -->

