#!/bin/sh
# SessionStart: inject the constitution pointer, last ledger entry, and unblocked tasks (stdout becomes context)
R=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
[ -f "$R/AGENTS.md" ] && printf 'dev-loop: project constitution is %s/AGENTS.md (read it before acting).\n' "$R"
[ -f "$R/.devloop/LEDGER.md" ] && { printf '\n## Last dev-loop ledger entry\n'; awk '/^## /{b=""} {b=b $0 "\n"} END{printf "%s", b}' "$R/.devloop/LEDGER.md" | tail -n 12; }
[ -f "$R/.devloop/tasks.jsonl" ] && command -v python3 >/dev/null && { printf '\n## Unblocked tasks\n'; python3 "${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/dev-loop/scripts/artifacts.py" tasks next --root "$R" 2>/dev/null | head -10; }
exit 0
