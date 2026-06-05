#!/bin/bash
set -euo pipefail
curl -s -u root:root \
    -H "NS: mios" -H "DB: agent" \
    -H "Accept: application/json" -H "Content-Type: text/plain" \
    --data 'SELECT ts, summary, payload FROM event WHERE kind = "refine" ORDER BY ts DESC LIMIT 5;' \
    http://127.0.0.1:8000/sql > /tmp/refines.json

python3 - <<'PYEOF'
import json
with open("/tmp/refines.json") as f:
    data = json.load(f)
if not isinstance(data, list) or not data:
    print("(no rows)")
    raise SystemExit(0)
rows = (data[-1] or {}).get("result") or []
for i, row in enumerate(rows):
    print(f"=== row {i+1} ===")
    print(f"  ts:      {row.get('ts')}")
    print(f"  summary: {row.get('summary')}")
    p = row.get("payload") or {}
    print(f"  intent:           {p.get('intent')}")
    print(f"  target_agent:     {p.get('target_agent')}")
    rt = (p.get('refined_text') or '')[:160]
    print(f"  refined_text:     {rt}")
    io = (p.get('intended_outcome') or '')[:160]
    print(f"  intended_outcome: {io}")
    print(f"  hint_tools:       {p.get('hint_tools')}")
    print(f"  hint_skills:      {p.get('hint_skills')}")
    tasks = p.get("tasks")
    if isinstance(tasks, list) and tasks:
        print(f"  tasks ({len(tasks)}):")
        for j, t in enumerate(tasks):
            title = (t.get('title') or '')[:100]
            print(f"    {j}. title: {title}")
            refined = (t.get('refined_text') or '')[:120]
            print(f"       refined: {refined}")
            print(f"       target_agent: {t.get('target_agent')}")
            print(f"       hint_tools: {t.get('hint_tools')}")
    print()
PYEOF
