#!/usr/bin/env python3
"""Diagnostic: can the qwen3 micro emit JSON to content (not reasoning)
when thinking is disabled via ollama /api/chat "think": false?
Run in dev VM: python3 /mnt/c/MiOS/automation/support/refine-model-probe.py
"""
import json
import time
import urllib.request

SYS = 'Reply ONLY with JSON {"route":"agent"} or {"route":"chat"}.'
Q = "what are the latest trending technology topics today?"


def native_chat(model, think):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": Q},
        ],
        "stream": False,
        "think": think,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 80},
    }
    req = urllib.request.Request(
        "http://localhost:11435/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t = time.time()
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    dt = time.time() - t
    msg = r.get("message", {})
    return dt, repr(msg.get("content"))[:120], repr(msg.get("thinking"))[:80]


for m in ("qwen3:0.6b-cpu", "qwen3:1.7b"):
    for think in (False, True):
        try:
            dt, content, thinking = native_chat(m, think)
            print(f"{m:14} think={str(think):5} {dt:5.1f}s  content={content}")
        except Exception as e:
            print(f"{m:14} think={think} ERROR: {e}")
