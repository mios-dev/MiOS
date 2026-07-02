#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_compact (WS-A5 rolling-summary compaction planner). Pure stdlib, no server.py/DB/pytest. Verifies plan_compaction is a no-op when history fits, always keeps the last keep_recent non-system messages + system messages verbatim, marks the OLDEST overflow for summarization, and the kept set stays within budget.
# AI-related: ./mios_compact.py, ./mios_tokenize.py
# AI-functions: check, main
"""Unit tests for mios_compact (WS-A5)."""

import sys

import mios_compact as cmp

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def m(role, content):
    return {"role": role, "content": content}


def t_noop():
    msgs = [m("user", "a" * 20), m("assistant", "b" * 20)]  # 5+5 tokens
    plan = cmp.plan_compaction(msgs, budget=1000)
    check("noop: fits -> needed False", plan.needed is False)
    check("noop: keeps everything", len(plan.to_keep) == 2 and not plan.to_summarize)


def t_summarize_oldest():
    # 10 user turns of 40 chars (10 tokens) each = 100 tokens; budget 40.
    msgs = [m("user", f"turn{i} " + "x" * 33) for i in range(10)]
    plan = cmp.plan_compaction(msgs, budget=40, keep_recent=2)
    check("compact: needed True (over budget)", plan.needed is True)
    check("compact: keeps within budget", plan.kept_tokens <= 40, f"{plan.to_dict()}")
    # The last 2 turns are always kept.
    kept_texts = [x["content"] for x in plan.to_keep]
    check("compact: last keep_recent kept", msgs[-1]["content"] in kept_texts and msgs[-2]["content"] in kept_texts)
    # The oldest turn is summarized, not kept.
    check("compact: oldest folded into summary", msgs[0] in plan.to_summarize)
    check("compact: split is a partition", len(plan.to_keep) + len(plan.to_summarize) == 10)


def t_keep_system():
    msgs = [m("system", "S" * 200)] + [m("user", "u" * 40) for _ in range(6)]
    plan = cmp.plan_compaction(msgs, budget=30, keep_recent=1)
    check("system: system message kept verbatim",
          any(x["role"] == "system" for x in plan.to_keep))
    check("system: never summarized",
          not any(x["role"] == "system" for x in plan.to_summarize))


def t_order_preserved():
    msgs = [m("user", "u" * 40) for _ in range(8)]
    plan = cmp.plan_compaction(msgs, budget=25, keep_recent=2)
    idx = [msgs.index(x) for x in plan.to_keep]
    check("order: kept messages in original order", idx == sorted(idx), f"{idx}")


def t_drop_stale_tool_results():
    from mios_pipe.routing.chat import _drop_stale_tool_results
    msgs = [
        m("user", "turn 1"),
        m("assistant", "response 1"),
        m("user", "turn 2"),
        m("assistant", "call tool"),
        m("tool", "result 2"),
        m("assistant", "response 2"),
        m("user", "turn 3"),
        m("assistant", "response 3")
    ]
    res = _drop_stale_tool_results(msgs, ttl_turns=1)
    check("drop_tool: drops old tool message", not any(x.get("role") == "tool" for x in res))
    
    res2 = _drop_stale_tool_results(msgs, ttl_turns=2)
    check("drop_tool: keeps recent tool message", any(x.get("role") == "tool" for x in res2))


def main():
    t_noop()
    t_summarize_oldest()
    t_keep_system()
    t_order_preserved()
    t_drop_stale_tool_results()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
