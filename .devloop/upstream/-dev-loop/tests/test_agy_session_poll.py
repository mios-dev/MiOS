#!/usr/bin/env python3
"""
Controls for agy_session.py's POLL LOOP — the mechanism that justifies --session.

Why this file exists
--------------------
`--session` was built on one claim: a held stream-json session outlives a turn, so a native
subagent that has not finished when the manager stops speaking is not lost. The first
end-to-end run did NOT test that. The manager dispatched, gated and merged everything inside a
single turn (num_turns 1, zero polls), so `missing_reports` was already empty at the first
result and no follow-up turn was ever sent. The loop shipped unexercised.

Driving a real `agy` into the slow case is non-deterministic and expensive: you cannot reliably
make a model end its turn mid-subagent. So these controls put a FAKE `agy` on PATH that emits
the measured wire protocol and lets the test choose exactly when reports appear. That tests the
code under test — agy_session.py's loop — rather than a model's mood.

The fake speaks the shapes recorded from agy 1.2.6 (references/translation-layer.md 5.1a):
  out: {"event":"init","conversation_id":...,"init":{cwd,tools[],permission_mode}}
       {"event":"result","result":{conversation_id,status,response,num_turns,...}}
  in : one NDJSON {"event":"user","message":{...}} per line, one turn each

Run: python3 tests/test_agy_session_poll.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSION = ROOT / "skills" / "dev-loop" / "scripts" / "agy_session.py"

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


FAKE = r'''#!/usr/bin/env python3
"""Fake `agy`. Behaviour driven by FAKE_AGY_MODE; writes reports when told to."""
import json, os, sys

MODE = os.environ["FAKE_AGY_MODE"]
NATIVE = os.environ["FAKE_AGY_NATIVE"]     # .devloop/native dir
LANES = os.environ.get("FAKE_AGY_LANES", "").split(",") if os.environ.get("FAKE_AGY_LANES") else []

def emit(o):
    sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()

def result(n):
    emit({"event": "result", "result": {
        "conversation_id": "fake-conv", "status": "SUCCESS",
        "response": f"turn {n}", "num_turns": n, "duration_seconds": 0.1,
        "usage": {"input_tokens": 1, "output_tokens": 1, "thinking_tokens": 0,
                  "cache_read_tokens": 0, "total_tokens": 2}}})

def write_reports(ids):
    os.makedirs(NATIVE, exist_ok=True)
    for i in ids:
        with open(os.path.join(NATIVE, f"report-{i}.json"), "w") as f:
            json.dump({"devloop_report": {"status": "done", "objective": i}}, f)

emit({"event": "init", "conversation_id": "fake-conv",
      "init": {"cwd": os.getcwd(), "tools": ["invoke_subagent"], "permission_mode": "always-proceed"}})

if MODE == "no_result":                      # a stream of unknown events: no result at all
    sys.stdin.readline()
    sys.stderr.write('warning: ignoring unsupported stream input message event "x"\n')
    sys.exit(1)

turn = 0
for line in sys.stdin:                       # one turn per NDJSON line
    if not line.strip():
        continue
    turn += 1
    if MODE == "immediate":                  # lanes already done before the first result
        write_reports(LANES)
    elif MODE == "slow" and turn == 2:       # finishes only after ONE poll
        write_reports(LANES)
    elif MODE == "very_slow":                # never finishes; poll budget must run out
        pass
    result(turn)
'''


def run_session(tmp: Path, mode: str, lanes: list[str], poll_max: int = 3):
    """Run agy_session.py against the fake agy. Returns (rc, stderr, envelope|None)."""
    bindir = tmp / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    fake = bindir / "agy"
    fake.write_text(FAKE)
    fake.chmod(0o755)

    native = tmp / ".devloop" / "native"
    native.mkdir(parents=True, exist_ok=True)

    lanes_file = tmp / "lanes.json"
    lanes_file.write_text(json.dumps({"lanes": [
        {"id": i, "worker": {"harness": "antigravity"}} for i in lanes]}))
    prompt = tmp / "prompt.txt"
    prompt.write_text("dispatch the lanes")
    env_out = tmp / "envelope.json"

    env = {**os.environ,
           "PATH": f"{bindir}:{os.environ['PATH']}",
           "FAKE_AGY_MODE": mode,
           "FAKE_AGY_NATIVE": str(native),
           "FAKE_AGY_LANES": ",".join(lanes)}
    cp = subprocess.run(
        [sys.executable, str(SESSION), "--prompt-file", str(prompt), "--lanes", str(lanes_file),
         "--run-root", str(tmp), "--envelope-out", str(env_out), "--poll-max", str(poll_max)],
        capture_output=True, text=True, timeout=120, env=env)
    envelope = json.loads(env_out.read_text()) if env_out.is_file() else None
    return cp.returncode, cp.stderr, envelope


def test_poll_fires_when_a_lane_is_unfinished() -> None:
    """THE CASE --session EXISTS FOR, and the one the real run never reached."""
    print("poll fires on an unfinished lane:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rc, err, env = run_session(tmp, "slow", ["a", "b"])
        check("the loop polled", "polling" in err,
              "no poll means the turn end was accepted as the run end — the exact failure --session exists to prevent")
        check("it named the unreported lanes", "'a'" in err or "a," in err or "['a'" in err, err[-300:])
        check("it ran a SECOND turn", env is not None and env.get("num_turns") == 2,
              f"num_turns={env and env.get('num_turns')} — a single turn means no follow-up was sent")
        check("exit 0 once every lane reported", rc == 0, f"rc={rc} stderr={err[-200:]}")
        for lid in ("a", "b"):
            check(f"report-{lid}.json exists", (tmp / ".devloop" / "native" / f"report-{lid}.json").is_file())


def test_no_poll_when_lanes_already_reported() -> None:
    """NEGATIVE CONTROL for the poll itself: it must not fire when there is nothing to wait for.

    Without this, a loop that polled unconditionally would pass the test above while burning a
    turn — and every extra turn is a real model call in production."""
    print("poll does NOT fire when lanes are already done:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rc, err, env = run_session(tmp, "immediate", ["a"])
        check("no poll was sent", "polling" not in err)
        check("exactly one turn", env is not None and env.get("num_turns") == 1,
              f"num_turns={env and env.get('num_turns')}")
        check("exit 0", rc == 0, f"rc={rc}")


def test_poll_budget_is_enforced_and_failure_is_loud() -> None:
    """A lane that never reports must NOT come back as success (Timeout-as-Pass, SKILL 7)."""
    print("poll budget exhausted:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rc, err, env = run_session(tmp, "very_slow", ["a"], poll_max=2)
        check("exit 5, not 0", rc == 5, f"rc={rc} — a never-reporting lane must never read as success")
        check("it says which lane is still unreported", "still unreported" in err and "a" in err)
        check("it polled up to the budget and stopped", err.count("polling") == 2,
              f"polled {err.count('polling')}x with poll-max=2")


def test_no_result_event_is_an_error() -> None:
    """Measured: a stream of unknown events yields NO result event. Absence is not success."""
    print("no result event at all:")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rc, err, env = run_session(tmp, "no_result", ["a"])
        check("exit 3", rc == 3, f"rc={rc}")
        check("it says nothing ran", "NO result event" in err or "no result event" in err.lower())
        check("no envelope was written", env is None,
              "writing an envelope here would hand the caller a success-shaped object for a run that did nothing")


def test_poll_predicate_prefers_the_shell_receipt() -> None:
    """The predicate, not the loop. missing_reports() was is_file() over a report the poll
    prompt ASKS THE POLLED AGENT TO CREATE — the measured thing wrote the measurement. With a
    jobs root present the shell's receipt decides instead, and an agent-written report file no
    longer ends the wait for a lane that is still running."""
    print("poll predicate:")
    sys.path.insert(0, str(SESSION.parent))
    import agy_session as S
    import job

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        native = tmp / ".devloop" / "native"; native.mkdir(parents=True)
        jobs = tmp / "jobs"; jobs.mkdir()

        # A lane that is genuinely still running, with a report file an agent could have written.
        job.spawn(jobs, "lane1", ["sh", "-c", "sleep 20"], Path("."), budget_s=60)
        (native / "report-lane1.json").write_text('{"devloop_report": {"status": "done"}}')

        end = time.time() + 15
        while job.status(jobs, "lane1")["pid"] is None and time.time() < end:
            time.sleep(0.2)

        without = S.missing_reports(native, ["lane1"])
        withjobs = S.missing_reports(native, ["lane1"], jobs)
        check("the OLD predicate is satisfied by the agent's own file", without == [],
              f"got {without} — this is the self-certifying behaviour being replaced")
        check("the receipt-backed predicate still reports it outstanding", withjobs == ["lane1"],
              f"got {withjobs} — a running lane must not be ended by a file the agent wrote")

        job.kill(jobs, "lane1", "KILL")
        end = time.time() + 15
        while job.status(jobs, "lane1")["state"] == "running" and time.time() < end:
            time.sleep(0.3)
        check("a lost lane is terminal, so the wait ends rather than hanging",
              S.missing_reports(native, ["lane1"], jobs) == [],
              "lost is an outcome, not a reason to keep polling forever")

        # A lane with no job at all falls back to the report file, and that is stated, not hidden.
        (native / "report-native1.json").write_text("{}")
        check("a lane with no job falls back to the report file",
              S.missing_reports(native, ["native1"], jobs) == [])


def main() -> int:
    if not SESSION.is_file():
        print(f"FAIL: {SESSION} missing")
        return 1
    for t in (test_poll_fires_when_a_lane_is_unfinished,
              test_no_poll_when_lanes_already_reported,
              test_poll_budget_is_enforced_and_failure_is_loud,
              test_no_result_event_is_an_error,
              test_poll_predicate_prefers_the_shell_receipt):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all poll-loop controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
