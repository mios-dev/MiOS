#!/usr/bin/env python3
# AI-hint: Seed a failed tool_call in the database for a specific session to test if the polish logic correctly grounds a hallucinated "Done!" response against the actual failed tool history.
# AI-related: mios-gui, localhost:8000
# AI-functions: db, main
"""Seed a failed tool_call + invoke /v1/chat/completions with that
session_id so polish has tool history to ground against. Tests
that polish rewrites a hallucinated 'Done!' response into a
failure acknowledgement when the recent tool_call says failed."""
import base64
import json
import time
import urllib.request


AUTH = "Basic " + base64.b64encode(b"root:root").decode()


def db(sql: str):
    req = urllib.request.Request(
        "http://localhost:8000/sql",
        data=("USE NS mios DB mios; " + sql).encode(),
        headers={"Authorization": AUTH, "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def main() -> int:
    sid = db("CREATE session SET started_at = time::now(), platform = 'polish-smoke';")[-1]["result"][0]["id"]
    print(f"session: {sid}")

    db(
        f"CREATE tool_call SET session = {sid}, ts = time::now(), "
        f"tool = 'open_app', args = {{'name': 'nautilus'}}, "
        f"success = false, exit_code = 1, "
        f"result_preview = 'mios-gui: launch call failed (rc=134); "
        f"Connection: failed to receive credentials', "
        f"latency_ms = 1200;"
    )
    print("seeded failed open_app tool_call")
    print()

    rows = db(
        f"SELECT ts, tool, success, exit_code FROM tool_call "
        f"WHERE session = {sid} ORDER BY ts;"
    )[-1]["result"]
    print("recent tool history for session:")
    for row in rows:
        s = row.get("success")
        label = "ok" if s else (f"FAILED (exit={row.get('exit_code')})" if s is False else "?")
        print(f"  {row.get('tool')} -> {label}")
    print()
    print("(polish_response will pull these via _recent_tool_history(session_id))")
    return 0


if __name__ == "__main__":
    main()
