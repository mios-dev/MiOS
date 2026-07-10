#!/usr/bin/env python3
"""Isolation tests for the web-research SSE applet (mios_pipe.routing.applet_webresearch)."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mios_pipe.routing import applet_webresearch as wr  # noqa: E402

_fails = 0


def check(cond, msg):
    global _fails
    print(("[PASS] " if cond else "[FAIL] ") + msg)
    if not cond:
        _fails += 1


async def _collect(query, dispatch, **kw):
    frames = []
    async for f in wr.stream_webresearch(query, dispatch, **kw):
        frames.append(f)
    return frames


def _events(frames):
    return [f.split("\n", 1)[0].replace("event: ", "") for f in frames]


async def main_async():
    # 1. happy path: envelope dict with 'results'
    async def d_ok(tool, args):
        check(tool == "web_search", "dispatch invoked with web_search verb")
        check(args.get("query") == "langs", "query forwarded to dispatch args")
        return {"results": [
            {"title": "Rust", "url": "https://rust-lang.org", "snippet": "systems lang"},
            {"title": "Zig", "url": "https://ziglang.org"},
        ]}
    fr = await _collect("langs", d_ok, limit=5)
    ev = _events(fr)
    check(ev[0] == "status", f"first frame is status ({ev[:1]})")
    check(ev.count("result") == 2, f"two result frames ({ev.count('result')})")
    check(ev[-1] == "done", "last frame is done")
    body = "".join(fr)
    check("https://rust-lang.org" in body and ">Rust<" in body, "result html carries url+title")
    check(all(f.endswith("\n\n") for f in fr), "every SSE frame terminates with a blank line")

    # 2. empty query -> error,done and dispatch is NOT called
    called = {"n": 0}
    async def d_never(t, a):
        called["n"] += 1
        return {}
    fr = await _collect("   ", d_never)
    check(_events(fr) == ["error", "done"], "empty query -> error,done")
    check(called["n"] == 0, "dispatch NOT called on empty query")

    # 3. dispatch raises -> error,done carrying the message
    async def d_boom(t, a):
        raise RuntimeError("boom-net")
    fr = await _collect("x", d_boom)
    check(_events(fr)[-1] == "done" and "error" in _events(fr), "dispatch error -> error,done")
    check("boom-net" in "".join(fr), "error frame carries the failure message")

    # 4. XSS: untrusted scraped title must be HTML-escaped, never streamed raw
    async def d_xss(t, a):
        return {"results": [{"title": "<script>alert(1)</script>", "url": "https://x/"}]}
    body = "".join(await _collect("x", d_xss))
    check("<script>alert" not in body and "&lt;script&gt;" in body, "title HTML-escaped (no raw <script>)")

    # 5. result-shape normalization
    check(len(wr._extract_results({"data": [{"a": 1}]})) == 1, "extract: dict.data list")
    check(len(wr._extract_results([{"a": 1}, {"b": 2}])) == 2, "extract: bare list")
    check(len(wr._extract_results({"stdout": json.dumps({"hits": [{"x": 1}]})})) == 1, "extract: json-in-stdout")
    check(wr._extract_results("garbage") == [], "extract: unknown -> []")


def main():
    asyncio.run(main_async())
    # 6. build_router (requires fastapi)
    try:
        r = wr.build_router()
        paths = {getattr(rt, "path", None) for rt in r.routes}
        check("/portal/app/webresearch" in paths, "router exposes the applet page route")
        check("/portal/app/webresearch/stream" in paths, "router exposes the SSE stream route")
    except Exception as e:  # noqa: BLE001
        check(False, f"build_router() failed: {e}")
    print("ALL PASS" if _fails == 0 else f"{_fails} FAILED")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
