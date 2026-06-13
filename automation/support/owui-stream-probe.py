#!/usr/bin/env python3
# AI-hint: A diagnostic script used to determine if the Open WebUI (OWUI) backend streams SSE chunks in real-time or buffers them before delivery by timing and logging the arrival of chunks from the chat API.
# AI-related: mios-agent, localhost:3030
"""Throwaway: does OWUI stream the pipe's SSE to the client, or buffer it?
Fires a real query through OWUI's chat API and timestamps each chunk.
Trickle = OWUI streams (browser-render issue). Dump-at-end = OWUI buffers."""
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request

DB = "/var/lib/mios/open-webui/webui.db"
try:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    row = c.execute(
        "SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id "
        "WHERE u.role='admin' ORDER BY a.created_at DESC LIMIT 1").fetchone()
    c.close()
    token = row[0] if row else ""
except Exception as e:
    print("token error:", e); sys.exit(1)
print("token_len:", len(token), flush=True)
if not token:
    sys.exit(1)

body = {
    "model": "mios_agent.mios-agent",
    "messages": [{"role": "user",
                  "content": "what are the latest trending technology topics today"}],
    "stream": True,
}
req = urllib.request.Request(
    "http://localhost:3030/api/chat/completions",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {token}",
             "Content-Type": "application/json", "Accept": "text/event-stream"},
)
t0 = time.time()
n = 0
last = t0
try:
    resp = urllib.request.urlopen(req, timeout=180)
    print("HTTP", resp.status, "ct=", resp.headers.get("content-type"), flush=True)
    for raw in resp:
        dt = time.time() - t0
        n += 1
        # print first few + then only when >1.5s since last print (to show cadence)
        if n <= 6 or dt - last >= 1.5:
            line = raw.decode("utf-8", "replace").rstrip()
            print(f"  +{dt:6.1f}s chunk#{n}: {line[:80]}", flush=True)
            last = dt
    print(f"  DONE +{time.time()-t0:.1f}s total chunks={n}", flush=True)
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.read().decode()[:300], flush=True)
except Exception as e:
    print(f"ERROR after +{time.time()-t0:.1f}s: {e}", flush=True)
