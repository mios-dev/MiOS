#!/usr/bin/env python3
"""
Controls for the binding rules in a rendered lane prompt (adapters.lane_prompt).

Why the foreground rule exists
------------------------------
The MANAGER prompt has always forbidden backgrounding: a headless manager that launches
`devloop.sh` and answers before it finishes kills every child lane with its own process. The
LANE prompt never carried the equivalent rule, and on 2026-09-19 a worker showed exactly why.
Lane t1001-gate05 launched three commands and announced each time:

    "I have launched `python3 tools/drift-checks.py no-inert-ssot-tables` ... and will wait"
    "I will wait for the background command to finish execution."

then ended its single turn. adapters.py recorded the honest outcome -- status partial,
changed_paths empty, full_gate exit -1, "no devloop_report block emitted by the lane" -- and
the row it was measuring went unmeasured. Same shape as the manager failure, one level down:
a worker that treats ending a turn as waiting.

Antigravity makes this easy to fall into: run_command auto-backgrounds anything still running
after its WaitMsBeforeAsync parameter, so a slow command becomes a background command without
the worker choosing it.

These are string assertions on a generated prompt, which is a weak form of test -- so each one
names the specific rule it guards rather than matching a blob, and the negative control deletes
the rule to prove the suite notices.

Run: python3 tests/test_lane_prompt.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "dev-loop" / "scripts"))

import adapters  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def render() -> str:
    """Render through merged_lane, the path devloop.sh actually uses — a lane dict straight
    from the plan has no worker defaults merged and would raise."""
    spec = json.loads((ROOT / "skills" / "dev-loop" / "assets" / "lanes.example.json").read_text())
    lane = adapters.merged_lane(spec, spec["lanes"][0]["id"])
    return adapters.lane_prompt(lane, Path("/wt"), Path("/skill/SKILL.md"))


def test_foreground_rule() -> None:
    print("foreground rule (the t1001 failure):")
    p = render()
    check("commands must run synchronously in the foreground",
          "SYNCHRONOUSLY IN THE FOREGROUND" in p)
    check("backgrounding is forbidden outright", "Never background a command" in p)
    check("ending a turn is not waiting", "end a turn saying you will wait" in p,
          "the worker's exact failure was announcing a wait and then ending its turn")
    check("says WHY: the process dies with the turn",
          "your process ends when your turn ends" in p)
    check("names agy's auto-background parameter", "WaitMsBeforeAsync" in p,
          "a slow command becomes a background command without the worker choosing it")
    check("cites the observed failure rather than asserting a rule",
          "having measured nothing" in p)


def test_other_binding_rules_survive() -> None:
    """The foreground rule was inserted next to these; a careless edit could displace one."""
    print("the rules it was inserted beside:")
    p = render()
    check("lane may not git add/commit/push", "git add/commit/push" in p)
    check("lane must run both controls itself", "Run both controls yourself" in p)
    check("status=done requires both controls held", "status=done only if both held" in p)
    check("report block is required", "devloop_report" in p)
    check("owned_paths is stated as binding", "modify ONLY these" in p)


def test_rule_is_not_vacuous() -> None:
    """NEGATIVE CONTROL. Remove the rule from the source and the suite must go red — otherwise
    these assertions are matching something incidental and would survive its deletion."""
    print("negative control (rule deleted):")
    src = (ROOT / "skills" / "dev-loop" / "scripts" / "adapters.py").read_text()
    start = src.find("        \"- RUN EVERY COMMAND SYNCHRONOUSLY IN THE FOREGROUND")
    if start < 0:
        check("rule block locatable in source", False, "cannot run the negative control")
        return
    end = src.find("        \"- Run both controls yourself", start)
    mutated = src[:start] + src[end:]
    # adapters.py resolves paths from __file__, which exec() does not supply; point the mutant
    # at the real module path so it resolves its assets exactly as the original does.
    real = ROOT / "skills" / "dev-loop" / "scripts" / "adapters.py"
    ns: dict = {"__file__": str(real), "__name__": "adapters_mutant"}
    exec(compile(mutated, str(real), "exec"), ns)
    lane = ns["merged_lane"](
        json.loads((ROOT / "skills" / "dev-loop" / "assets" / "lanes.example.json").read_text()),
        "be-async")
    p = ns["lane_prompt"](lane, Path("/wt"), Path("/skill/SKILL.md"))
    check("deleting the rule removes it from the prompt",
          "SYNCHRONOUSLY IN THE FOREGROUND" not in p,
          "the assertions above would pass without the rule — they are matching something else")
    check("and the surrounding rules still render",
          "Run both controls yourself" in p,
          "the mutation must remove only the rule, or this control proves nothing")


def main() -> int:
    for t in (test_foreground_rule, test_other_binding_rules_survive, test_rule_is_not_vacuous):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all lane-prompt controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
