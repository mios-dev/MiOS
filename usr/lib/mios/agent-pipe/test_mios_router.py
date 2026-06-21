#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_router (WS-A11/WS-3 decomposition Stage 1: the pure Router). Pure stdlib, no server.py/DB/pytest. Verifies each intent (chat|dispatch|multi_task|agent|dag) maps to the right RouteDecision mode, dispatch carries the tool + deterministic flag, deep promotes an agent turn to broad/fanout, multi_task/dag fan out, an unknown/empty intent falls to the safe agent default, and the to_dict shape.
# AI-related: ./mios_router.py
# AI-functions: check, main
"""Unit tests for mios_router (WS-A11/WS-3 Stage 1)."""

import sys

import mios_router as r

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_chat():
    d = r.route({"intent": "chat"})
    check("chat: mode", d.mode == "chat")
    check("chat: no fanout", d.fanout is False)
    check("chat: no tool", d.tool == "")


def t_dispatch():
    d = r.route({"intent": "dispatch", "tool": "open_app", "_deterministic": True})
    check("dispatch: mode", d.mode == "dispatch")
    check("dispatch: carries tool", d.tool == "open_app")
    check("dispatch: deterministic flag", d.deterministic is True)
    check("dispatch: no fanout", d.fanout is False)
    # tool can come from 'verb' alias.
    check("dispatch: verb alias -> tool", r.route({"intent": "dispatch", "verb": "pc_type"}).tool == "pc_type")


def t_multitask_dag():
    mt = r.route({"intent": "multi_task"})
    check("multi_task: mode", mt.mode == "multi_task")
    check("multi_task: fans out", mt.fanout is True and mt.broad is True)
    dag = r.route({"intent": "dag"})
    check("dag: mode", dag.mode == "dag")
    check("dag: fans out", dag.fanout is True)


def t_agent_deep():
    a = r.route({"intent": "agent"})
    check("agent: mode", a.mode == "agent")
    check("agent: shallow -> no fanout", a.fanout is False and a.broad is False)
    ad = r.route({"intent": "agent", "deep": True})
    check("agent+deep: broad", ad.broad is True)
    check("agent+deep: fans out", ad.fanout is True)


def t_default():
    for bad in [{}, {"intent": ""}, {"intent": "weird"}, None, "notadict"]:
        d = r.route(bad)
        check(f"default: {bad!r} -> agent", d.mode == "agent", d.to_dict())
    check("default: helper should_fanout False for chat", r.should_fanout({"intent": "chat"}) is False)
    check("default: helper should_fanout True for multi_task", r.should_fanout({"intent": "multi_task"}) is True)


def t_shape():
    d = r.route({"intent": "dispatch", "tool": "x"}).to_dict()
    check("shape: keys", set(d) >= {"mode", "intent", "tool", "broad", "deterministic", "fanout", "reason"})


def main():
    t_chat()
    t_dispatch()
    t_multitask_dag()
    t_agent_deep()
    t_default()
    t_shape()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
