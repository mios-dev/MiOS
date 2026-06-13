#!/usr/bin/env python3
# AI-hint: Verifies Phase C.3 integrity by querying the local SurrealDB instance to count and sample rows in tool_call, event, and skill_invocation tables that contain non-null passport signatures.
# AI-related: localhost:8000
# AI-functions: post, main
"""Helper: count tables with at least one passport-bearing row.
Used during Phase C.3 verification to make sure the signing
default is actually attaching envelopes to every write site."""
import base64
import json
import urllib.request

AUTH = "Basic " + base64.b64encode(b"root:root").decode()


def post(sql: str) -> list:
    req = urllib.request.Request(
        "http://localhost:8000/sql",
        data=(f"USE NS mios DB mios; {sql}").encode(),
        headers={"Authorization": AUTH,
                 "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def main() -> int:
    for table in ("tool_call", "event", "skill_invocation"):
        r = post(f"SELECT count() FROM {table} WHERE passport != NONE GROUP ALL;")
        rows = r[-1].get("result") or []
        signed = rows[0]["count"] if rows else 0
        r = post(f"SELECT count() FROM {table} GROUP ALL;")
        rows = r[-1].get("result") or []
        total = rows[0]["count"] if rows else 0
        print(f"  {table:<18} signed: {signed}/{total}")
    print()
    # Show 1 example envelope from each. SurrealDB 3 requires ORDER BY
    # fields to be in the SELECT projection -- include the order key.
    ts_field = {
        "tool_call": "ts", "event": "ts", "skill_invocation": "started_at",
    }
    for table in ("tool_call", "event", "skill_invocation"):
        order = ts_field[table]
        r = post(
            f"SELECT {order}, passport FROM {table} WHERE passport != NONE "
            f"ORDER BY {order} DESC LIMIT 1;")
        rows = r[-1].get("result") or []
        if not rows:
            print(f"  {table}: no signed rows yet")
            continue
        p = rows[0].get("passport") or {}
        agent = p.get("agent")
        kid = p.get("kid")
        sig = (p.get("sig") or "")[:24]
        print(f"  {table}: agent={agent} kid={kid} sig={sig}...")
    return 0


if __name__ == "__main__":
    main()
