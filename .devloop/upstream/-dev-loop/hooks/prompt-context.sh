#!/bin/sh
# UserPromptSubmit: attach the in-progress task (if any) so work stays scoped
R=$(git rev-parse --show-toplevel 2>/dev/null || pwd); F="$R/.devloop/tasks.jsonl"; [ -f "$F" ] || exit 0
python3 - "$F" <<'PY' 2>/dev/null
import json, sys
ts = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
cur = "; ".join(f"{t['id']} {t['title']}" for t in ts if t.get("status") == "in_progress")[:400]
if cur:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "dev-loop in-progress task(s): " + cur}}))
PY
exit 0
