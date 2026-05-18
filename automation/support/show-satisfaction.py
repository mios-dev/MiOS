#!/usr/bin/env python3
"""Show recent satisfaction events written by mios-daemon's
satisfaction_loop. Operator-runnable post-hoc audit of which
user queries the daemon flagged satisfied vs unsatisfied."""
import base64
import json
import sys
import urllib.request


AUTH = "Basic " + base64.b64encode(b"root:root").decode()


def post(sql: str):
    req = urllib.request.Request(
        "http://localhost:8000/sql",
        data=("USE NS mios DB mios; " + sql).encode(),
        headers={"Authorization": AUTH, "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def main() -> int:
    sql = (
        'SELECT ts, kind, summary, payload FROM event '
        'WHERE kind = "user_query_satisfied" '
        '   OR kind = "user_query_unsatisfied" '
        'ORDER BY ts DESC LIMIT 10;'
    )
    data = post(sql)
    rows = data[-1].get("result") or []
    if not rows:
        print("(no satisfaction events yet)")
        return 0
    for row in rows:
        kind = row.get("kind", "")
        summary = (row.get("summary") or "")[:90]
        ts = (row.get("ts") or "")[:19]
        payload = row.get("payload") or {}
        marker = "✓" if kind == "user_query_satisfied" else "✗"
        print(f"  {marker} {ts}  {kind}")
        print(f"     summary: {summary}")
        if kind == "user_query_unsatisfied":
            failed = payload.get("failed_tools") or []
            for f in failed[:3]:
                print(
                    f"     failed:  {f.get('tool')}  "
                    f"exit={f.get('exit_code')}  "
                    f"err={(f.get('stderr_preview') or '')[:80]}"
                )
            if payload.get("reason"):
                print(f"     reason:  {payload['reason']}")
        elif payload.get("tools_checked"):
            print(f"     tools_checked: {payload['tools_checked']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
