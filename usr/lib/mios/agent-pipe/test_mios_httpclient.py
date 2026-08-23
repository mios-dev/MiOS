#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_pipe.kernel.httpclient -- the ONE shared outbound AsyncClient and the T-226 b...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_httpclient_py.md

"""Unit tests for the shared http client + the T-226 coalescing chokepoint."""

import asyncio
import os
import sys
import time

try:
    import httpx
except ModuleNotFoundError:                      # pragma: no cover
    print("[SKIP] httpx absent -- the shared client cannot be exercised")
    sys.exit(0)

from mios_pipe.kernel import httpclient as hc

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _req(url="http://remote:9999/v1/chat/completions", method="POST", model="m"):
    if method == "GET":
        return httpx.Request(method, url)
    return httpx.Request(method, url, json={"model": model})


def t_default_off():
    async def run():
        await hc.reset()
        hc.configure(batch_enable=False)
        client = await hc._get_client()
        hooks = list(client.event_hooks.get("request") or [])
        t0 = time.perf_counter()
        await hc._batch_request_hook(_req())
        ms = (time.perf_counter() - t0) * 1000
        await hc.reset()
        return hooks, ms
    hooks, ms = asyncio.run(run())
    check("default: NO request hook is registered at all", hooks == [], repr(hooks))
    check("default: no coalescer is built", hc.get_coalescer() is None)
    check("default: the hook is a no-op even if called directly", ms < 50, f"{ms:.1f}ms")


def t_flag_on():
    async def run():
        await hc.reset()
        hc.configure(batch_enable=True, batch_interval_s=0.12, batch_max_size=8,
                     batch_native_hints=["8500"])
        client = await hc._get_client()
        hooks = list(client.event_hooks.get("request") or [])

        t0 = time.perf_counter()
        await hc._batch_request_hook(_req("http://localhost:8500/v1/chat/completions"))
        native_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        await asyncio.gather(*[hc._batch_request_hook(_req()) for _ in range(3)])
        remote_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        await hc._batch_request_hook(_req("http://remote:9999/v1/models", method="GET"))
        get_ms = (time.perf_counter() - t0) * 1000

        groups = hc.get_coalescer().open_groups
        await hc.reset()
        hc.configure(batch_enable=False)
        return hooks, native_ms, remote_s, get_ms, groups

    hooks, native_ms, remote_s, get_ms, groups = asyncio.run(run())
    check("flag on: the hook is registered on the shared client",
          len(hooks) == 1 and hooks[0] is hc._batch_request_hook, repr(hooks))
    check("flag on: a native lane is not held", native_ms < 50, f"{native_ms:.1f}ms")
    check("flag on: concurrent non-native POSTs are held together",
          remote_s >= 0.10, f"{remote_s:.3f}s")
    check("flag on: the hold is bounded by the window", remote_s < 1.0, f"{remote_s:.3f}s")
    check("flag on: a GET is never held", get_ms < 50, f"{get_ms:.1f}ms")
    check("flag on: no window is left behind", groups == 0, str(groups))


def t_degrades_open():
    class _Boom:
        method = "POST"

        @property
        def content(self):
            raise RuntimeError("streaming body")

        @property
        def url(self):
            raise RuntimeError("no url")

    async def run():
        await hc.reset()
        hc.configure(batch_enable=True, batch_interval_s=5.0)
        await hc._get_client()
        t0 = time.perf_counter()
        await hc._batch_request_hook(_Boom())      # must not raise, must not hold
        ms = (time.perf_counter() - t0) * 1000
        await hc.reset()
        hc.configure(batch_enable=False)
        return ms
    ms = asyncio.run(run())
    check("degrade-open: an unreadable request is sent unheld", ms < 50, f"{ms:.1f}ms")


def t_server_reexport():
    try:
        import server
    except ModuleNotFoundError as exc:
        name = getattr(exc, "name", "") or ""
        here = os.path.dirname(os.path.abspath(__file__))
        if name.startswith("mios") or os.path.exists(os.path.join(here, f"{name}.py")):
            check(f"reexport: repo module {name} must import", False, repr(exc))
            return
        print(f"[SKIP] reexport: third-party dependency absent ({name})")
        return
    except (ImportError, NameError, AttributeError) as exc:
        check("reexport: server.py must be importable", False, repr(exc))
        return
    check("reexport: server._get_client IS the extracted one",
          server._get_client is hc._get_client)
    check("reexport: server._batch_request_hook IS the extracted one",
          server._batch_request_hook is hc._batch_request_hook)


def main():
    t_default_off()
    t_flag_on()
    t_degrades_open()
    t_server_reexport()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
