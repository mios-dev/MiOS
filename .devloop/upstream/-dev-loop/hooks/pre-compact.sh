#!/bin/sh
# PreCompact: write a handoff note so the post-compaction session starts from disk (SKILL §12 stop conditions)
R=$(git rev-parse --show-toplevel 2>/dev/null || pwd); [ -d "$R/.git" ] || [ -f "$R/.git" ] || exit 0
python3 "${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/dev-loop/scripts/adapters.py" ledger --root "$R" --status "pre-compact" \
  --objective "context compaction" --done "see git log -5" --next "re-read AGENTS.md, TASKS.md, this ledger; continue the in_progress task" \
  --unverified "anything not yet committed: $(git -C "$R" status --porcelain 2>/dev/null | wc -l | tr -d ' ') dirty path(s)" >/dev/null 2>&1
exit 0
