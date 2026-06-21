#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_kernel (WS-A11/WS-3 decomposition Stage 1b: the pure Kernel facade). Pure stdlib + asyncio, no server.py/DB/pytest. Verifies Kernel.handle routes via the injected router then runs via the injected dispatcher (passing the decision + refined + ctx through), requires both router+dispatcher (ValueError otherwise), and managers() reports which seams are wired. Uses the real mios_router + a fake dispatcher.
# AI-related: ./mios_kernel.py, ./mios_router.py
# AI-functions: check, main, class FakeDispatcher
"""Unit tests for mios_kernel (WS-A11/WS-3 Stage 1b)."""

import asyncio
import sys

import mios_kernel as mk
import mios_router as mr

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


class FakeDispatcher:
    def __init__(self):
        self.last = None

    async def run(self, decision, **ctx):
        self.last = (decision, ctx)
        return {"mode": decision.mode, "tool": decision.tool, "ctx": ctx}


def t_handle_flow():
    disp = FakeDispatcher()
    k = mk.Kernel(router=mr.Router(), dispatcher=disp)
    res = asyncio.run(k.handle({"intent": "dispatch", "tool": "open_app"}, chat_id="c1"))
    check("handle: routed to dispatch mode", res["mode"] == "dispatch")
    check("handle: decision carried the tool", res["tool"] == "open_app")
    check("handle: ctx forwarded to dispatcher", res["ctx"] == {"chat_id": "c1", "refined": {"intent": "dispatch", "tool": "open_app"}})
    check("handle: dispatcher saw the RouteDecision", disp.last[0].mode == "dispatch")


def t_handle_chat():
    k = mk.Kernel(router=mr.Router(), dispatcher=FakeDispatcher())
    res = asyncio.run(k.handle({"intent": "chat"}))
    check("handle: chat intent -> chat mode", res["mode"] == "chat")


def t_requires():
    raised = 0
    for kwargs in ({"router": mr.Router(), "dispatcher": None},
                   {"router": None, "dispatcher": FakeDispatcher()}):
        try:
            mk.Kernel(**kwargs)
        except ValueError:
            raised += 1
    check("requires: both router+dispatcher mandatory", raised == 2)


def t_managers():
    k = mk.Kernel(router=mr.Router(), dispatcher=FakeDispatcher(),
                  memory="m", access="a")
    m = k.managers()
    check("managers: wired seams True", m["memory"] is True and m["access"] is True)
    check("managers: unwired seams False", m["scheduler"] is False and m["context"] is False and m["tools"] is False)


def main():
    t_handle_flow()
    t_handle_chat()
    t_requires()
    t_managers()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
