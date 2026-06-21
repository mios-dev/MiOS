#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_dispatcher (WS-A11/WS-3 decomposition Stage 1c: the pure mode Dispatcher) + its integration with mios_router + mios_kernel. Pure stdlib + asyncio, no server.py/DB/pytest. Verifies run() routes a RouteDecision.mode to the injected handler, forwards ctx, falls back to the default mode for an unknown mode, raises KeyError when neither handler nor fallback exists, modes()/can_handle introspection, and the full Router->Dispatcher flow via Kernel.
# AI-related: ./mios_dispatcher.py, ./mios_router.py, ./mios_kernel.py
# AI-functions: check, main
"""Unit tests for mios_dispatcher (WS-A11/WS-3 Stage 1c)."""

import asyncio
import sys

import mios_dispatcher as md
import mios_router as mr
import mios_kernel as mk

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _mk_handlers(log):
    async def make(mode):
        async def h(decision, **ctx):
            log.append((mode, ctx))
            return {"ran": mode, "tool": getattr(decision, "tool", "")}
        return h
    return make


def t_routes():
    log = []
    async def h(mode):
        async def f(decision, **ctx):
            log.append((mode, getattr(decision, "mode", None), ctx))
            return mode
        return f
    handlers = {m: asyncio.run(h(m)) for m in ("chat", "dispatch", "agent")}
    d = md.Dispatcher(handlers)
    dec = mr.route({"intent": "dispatch", "tool": "open_app"})
    res = asyncio.run(d.run(dec, chat_id="c1"))
    check("routes: dispatch mode -> dispatch handler", res == "dispatch")
    check("routes: forwarded ctx + decision", log[-1][1] == "dispatch" and log[-1][2] == {"chat_id": "c1"})


def t_fallback():
    async def agent_h(decision, **ctx):
        return "agent-fallback"
    d = md.Dispatcher({"agent": agent_h})
    # 'dag' mode has no handler -> falls back to 'agent'.
    res = asyncio.run(d.run(mr.route({"intent": "dag"})))
    check("fallback: unknown mode -> default 'agent'", res == "agent-fallback")


def t_no_handler():
    d = md.Dispatcher({"chat": None.__class__ and (lambda *a, **k: None)})  # no 'agent' default
    raised = False
    try:
        asyncio.run(d.run(mr.route({"intent": "dag"})))  # dag + no agent fallback
    except KeyError:
        raised = True
    check("no-handler: KeyError when no handler + no fallback (fail-loud)", raised)


def t_introspect():
    async def f(d, **k): return None
    d = md.Dispatcher({"chat": f, "agent": f})
    check("introspect: modes sorted", d.modes() == ["agent", "chat"])
    check("introspect: can_handle known", d.can_handle("chat") is True)
    check("introspect: can_handle unknown -> via default", d.can_handle("dag") is True)  # 'agent' default exists
    check("introspect: can_handle no-default", md.Dispatcher({"chat": f}, default_mode="x").can_handle("dag") is False)


def t_kernel_flow():
    ran = {}
    async def chat_h(decision, **ctx): ran["mode"] = decision.mode; return "ok-chat"
    async def agent_h(decision, **ctx): ran["mode"] = decision.mode; return "ok-agent"
    disp = md.Dispatcher({"chat": chat_h, "agent": agent_h})
    k = mk.Kernel(router=mr.Router(), dispatcher=disp)
    check("kernel: chat routes+runs", asyncio.run(k.handle({"intent": "chat"})) == "ok-chat")
    check("kernel: unknown intent -> agent runs", asyncio.run(k.handle({"intent": "weird"})) == "ok-agent")


def main():
    t_routes()
    t_fallback()
    t_no_handler()
    t_introspect()
    t_kernel_flow()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
