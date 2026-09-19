#!/usr/bin/env python3
"""
Two-sided controls for agy_host.sh's dispatch rule and agy_session.py's wire shape.

The rule these guard
--------------------
Which lanes a manager may run as NATIVE Antigravity subagents is decided by PROCESS
LIFETIME, not by whether a human is watching:

  interactive  -> native subagents allowed (a person waits for them)
  --headless   -> FORBIDDEN. `agy -p` is single-turn; the process exits when the turn
                  ends and an unfinished subagent dies with it. Not an availability
                  claim -- invoke_subagent works headlessly (measured) -- a lifetime one.
  --session    -> allowed. The held stream-json session outlives each turn, and
                  agy_session.py polls until every antigravity lane has reported.

Every assertion below fails loudly if those three collapse into each other, which is the
mutation this file exists to catch: if someone "simplifies" --session to reuse the
headless rule (or vice versa), the distinctness checks go red.

Run: python3 tests/test_agy_dispatch_rule.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = ROOT / "skills" / "dev-loop" / "scripts" / "agy_host.sh"
LANES = ROOT / "skills" / "dev-loop" / "assets" / "lanes.example.json"
sys.path.insert(0, str(ROOT / "skills" / "dev-loop" / "scripts"))

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def prompt_for(*flags: str) -> str:
    cp = subprocess.run(["sh", str(HOST), str(LANES), "--print-prompt", *flags],
                        capture_output=True, text=True, timeout=180)
    assert cp.returncode == 0, f"agy_host.sh --print-prompt {flags} exited {cp.returncode}: {cp.stderr[-400:]}"
    return cp.stdout


FORBID = "Do NOT use invoke_subagent"
NATIVE = "invoke_subagent with workspace: branch"


def test_rules() -> None:
    print("dispatch rules:")
    interactive, headless, session = prompt_for(), prompt_for("--headless"), prompt_for("--session")

    # Positive controls: each mode carries the rule its lifetime demands.
    check("interactive allows native subagents", NATIVE in interactive)
    check("interactive does not carry the ban", FORBID not in interactive)
    check("headless bans native subagents", FORBID in headless)
    check("headless routes the full plan through devloop.sh", "devloop.sh" in headless)
    check("session allows native subagents", NATIVE in session)
    check("session does not carry the ban", FORBID not in session)
    check("session announces the held lifetime", "HELD SESSION" in session)

    # The ban must be justified by LIFETIME, not by availability -- a future editor
    # rewriting it as "invoke_subagent is unavailable" would be reinstating a claim
    # three measurements refuted.
    check("headless ban is worded as a lifetime constraint, not availability",
          "it works" in headless and "process exits" in headless)

    # Negative controls: the three rules must stay DISTINCT. Collapsing any pair is the
    # regression this file is for; without these, copying one rule over another passes.
    check("headless != session rule", headless != session)
    check("headless != interactive rule", headless != interactive)
    check("session != interactive rule", session != interactive,
          "session must say more than interactive: it promises the host will poll")
    check("session tells the manager a turn end is not the run end",
          "Ending a turn does NOT end the run" in session)
    # The first --session run dropped lane-<id>.json into tracked .devloop/ space because the
    # rule never said where scratch goes; devloop.sh has always put it under the run dir.
    check("session pins per-lane scratch to .devloop/native/",
          ".devloop/native/ next to the reports" in session)
    check("session forbids scratch in tracked .devloop/ top level",
          "Do NOT write scratch at" in session and "tracked space" in session)


def test_print_only_is_sticky() -> None:
    """A dry-run flag that executes is the worst kind of surprise. --print-prompt must
    win in EVERY flag order; previously `--print-prompt --headless` launched the run."""
    print("--print-prompt stickiness:")
    for flags in (("--headless",), ("--session",)):
        after = subprocess.run(["sh", str(HOST), str(LANES), "--print-prompt", *flags],
                               capture_output=True, text=True, timeout=180)
        before = subprocess.run(["sh", str(HOST), str(LANES), *flags, "--print-prompt"],
                                capture_output=True, text=True, timeout=180)
        check(f"--print-prompt before {flags[0]} previews", after.returncode == 0 and after.stdout.strip() != "")
        check(f"--print-prompt after {flags[0]} previews (order-independent)",
              before.returncode == 0 and before.stdout.strip() != "",
              f"rc={before.returncode} — the flag order decided whether the manager RAN")
        check(f"both orders produce the same prompt for {flags[0]}", after.stdout == before.stdout)


def test_session_wire_shape() -> None:
    """agy_session.py's NDJSON shape and argv, both measured against agy 1.2.6."""
    print("agy_session wire shape:")
    import agy_session as S

    line = S.ndjson_user("hello")
    doc = json.loads(line)
    check("input event is 'user'", doc.get("event") == "user")
    check("message is TOP-LEVEL, not nested under 'user'",
          "message" in doc and "user" not in {k for k in doc if k != "event"},
          "agy rejects a nested form: 'stream input \"user\" message is missing the \"message\" field'")
    check("message carries role+content", doc["message"] == {"role": "user", "content": "hello"})
    check("exactly one NDJSON line", line.endswith("\n") and line.count("\n") == 1)

    # The -p trap: a BARE -p swallows the next token as its prompt, so `-p` immediately
    # followed by a flag silently turns that flag into the prompt (measured: exit 2).
    src = (ROOT / "skills" / "dev-loop" / "scripts" / "agy_session.py").read_text()
    check("argv uses the attached-empty -p= form", '"-p="' in src)
    check("argv never emits a bare -p", '"-p"' not in src,
          "a bare -p would consume the following flag as the prompt")


def test_report_tracking() -> None:
    """missing_reports drives the poll loop; an Empty-Set Pass here would make the host
    declare every lane finished the moment no lane was listed."""
    print("report tracking:")
    import agy_session as S

    with tempfile.TemporaryDirectory() as td:
        native = Path(td) / ".devloop" / "native"
        native.mkdir(parents=True)
        check("unreported lane is listed", S.missing_reports(native, ["a", "b"]) == ["a", "b"])
        (native / "report-a.json").write_text("{}")
        check("reported lane drops out", S.missing_reports(native, ["a", "b"]) == ["b"])
        (native / "report-b.json").write_text("{}")
        check("all reported -> empty", S.missing_reports(native, ["a", "b"]) == [])

        lanes = Path(td) / "lanes.json"
        lanes.write_text(json.dumps({"lanes": [
            {"id": "n1", "worker": {"harness": "antigravity"}},
            {"id": "c1", "worker": {"harness": "claude-code"}},
            {"id": "n2", "worker": {"harness": "antigravity"}},
        ]}))
        ids = S.antigravity_lane_ids(lanes)
        check("only antigravity lanes are polled for", ids == ["n1", "n2"],
              f"got {ids}: a claude-code lane runs under devloop.sh and writes no native report")
        bad = Path(td) / "nope.json"
        bad.write_text("{not json")
        check("unparseable lane file yields no ids rather than raising",
              S.antigravity_lane_ids(bad) == [])


SESSION = ROOT / "skills" / "dev-loop" / "scripts" / "agy_session.py"

# --jobs-root's whole purpose is to replace the agent-written report file as the thing that ends
# a wait. It is meaningless unless a caller passes it. --input-format is the one flag the host
# legitimately never passes: agy_session.py owns the wire format and hardcodes it.
FLAGS_THE_HOST_NEED_NOT_PASS = {"--input-format"}


def test_no_dead_flags_on_the_session_driver() -> None:
    """DEAD-FLAG GUARD, and the specific regression it was written for.

    `--jobs-root` was added to agy_session.py and NO caller ever passed it, so every AGY run
    kept ending its waits on `report-<id>.json` -- a file the polled agent is asked to create.
    The fix was built, tested, committed and never reached production, and nothing was red.

    Asserting the general property rather than the one flag means the next such flag is caught
    too: a flag the driver declares but the host never passes is dead unless excused here."""
    print("session driver flags:")
    # argparse declarations ONLY. A bare scan for a quoted "--token" also matched flags the
    # driver PASSES to other programs -- `git status --porcelain` -- and reported them dead,
    # which is this file's own "measuring the wrong property" (SKILL.md 7): the property is
    # "the driver accepts this flag", and only add_argument establishes that.
    declared = set(re.findall(r'add_argument\(\s*"(--[a-z][a-z-]*)"', SESSION.read_text()))
    passed = set(re.findall(r'(--[a-z][a-z-]{2,})', HOST.read_text()))
    check("the driver declares flags at all", len(declared) > 5, f"found {len(declared)}")
    dead = sorted(declared - passed - FLAGS_THE_HOST_NEED_NOT_PASS)
    check("no declared flag is unreachable from the host", not dead,
          f"never passed by agy_host.sh: {dead}")
    check("--jobs-root specifically is passed", "--jobs-root" in passed,
          "without it the poll predicate falls back to the file the agent writes")
    check("the excuse list is not a blanket", len(FLAGS_THE_HOST_NEED_NOT_PASS) <= 2,
          "excusing flags wholesale turns this control into a no-op")


def test_the_prompt_permits_concurrency_but_not_shell_backgrounding() -> None:
    """The manager prompt said 'Work in STRICT SEQUENCE, no concurrency'. That was written when
    every attempt at concurrency had been shell backgrounding, which dies at the turn boundary.
    job.py removed that reason, so the blanket ban now contradicts the point of fanning out.

    The replacement must hold BOTH halves: concurrency through jobs is allowed, shell
    backgrounding is still forbidden, and base-tree work (gate/commit/merge) is still serial.
    A rewrite that drops either half fails here."""
    print("concurrency rule:")
    cp = subprocess.run(["sh", str(HOST), str(LANES), "--print-prompt"],
                        capture_output=True, text=True, timeout=60)
    body = cp.stdout
    check("the prompt renders", cp.returncode == 0 and len(body) > 2000,
          f"rc={cp.returncode} len={len(body)}")
    check("the blanket ban is gone", "no concurrency" not in body.lower(),
          "a manager told not to run lanes concurrently will not")
    check("concurrency is explicitly permitted", "CONCURRENCY IS ALLOWED" in body)
    check("shell backgrounding is still forbidden",
          "background work in your own shell" in body or "die with your turn" in body,
          "dropping this half re-opens the failure job.py exists to prevent")
    check("base-tree work is still serial",
          "strictly sequential" in body.lower() and "merge" in body.lower(),
          "two merges in flight corrupt the base tree")
    check("no unexpanded shell variables survive", "$SKILL_DIR/scripts/job.py" not in body
          or "$RUN_ROOT" not in body.split("job.py spawn")[-1][:200],
          "a literal $VAR in the prompt is an instruction the manager cannot follow")


def main() -> int:
    for t in (test_rules, test_print_only_is_sticky, test_session_wire_shape, test_report_tracking,
              test_no_dead_flags_on_the_session_driver,
              test_the_prompt_permits_concurrency_but_not_shell_backgrounding):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all dispatch-rule controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
