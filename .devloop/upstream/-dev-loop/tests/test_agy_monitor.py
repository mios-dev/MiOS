#!/usr/bin/env python3
"""
Controls for agy_monitor.py — the live view of an AGY-managed run.

What a monitor is for
---------------------
An AGY-managed run was one opaque process: the only signal was the envelope, at the end. If a
lane died, or every tool call was being denied, or the manager was answering without doing
anything, the operator learned it minutes later. A monitor exists to answer "if this failed
right now, would anything be emitted?" (SKILL.md 6) — so these controls are mostly about the
monitor NOT reporting calm.

The three it must never call healthy:
  * a stream with no result event at all  -> no_result (measured: an all-unknown-event stream)
  * a result claiming SUCCESS with no text and no tool calls -> vacuous
  * denials present -> refused, regardless of the harness's own SUCCESS

And the one it must not lose: agy writes warnings and bare-text errors into the same stream, so
a monitor that json.loads every line silently drops exactly the lines that say a run is doing
nothing. Those are counted and surfaced, not swallowed.

Run: python3 tests/test_agy_monitor.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MON = ROOT / "skills" / "dev-loop" / "scripts" / "agy_monitor.py"
# every other case drives the monitor as a subprocess; the stall detector is imported
sys.path.insert(0, str(MON.parent))

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def init_evt(tools: int = 57) -> str:
    return json.dumps({"event": "init", "conversation_id": "conv-abc12345",
                       "init": {"cwd": "/repo", "tools": ["t"] * tools,
                                "permission_mode": "always-proceed"}})


def tool_evt(name: str) -> str:
    return json.dumps({"event": "step_update", "step_update": {
        "step_index": 1, "state": "DONE", "step_type": "tool", "tool_name": name}})


def subagent_evt(child: str, typ: str) -> str:
    return json.dumps({"event": "step_update", "step_update": {
        "step_index": 2, "state": "DONE", "step_type": "subagent",
        "tool_name": "invoke_subagent",
        "subagent_info": {"subagents": [{"type_name": typ, "conversation_id": child}]}}})


def result_evt(**over) -> str:
    r = {"conversation_id": "conv-abc12345", "status": "SUCCESS", "response": "done",
         "num_turns": 1, "duration_seconds": 3.5,
         "usage": {"total_tokens": 100}}
    r.update(over)
    return json.dumps({"event": "result", "result": r})


def run_once(lines: list[str]) -> tuple[int, dict]:
    d = Path(tempfile.mkdtemp())
    f = d / "events.ndjson"
    f.write_text("\n".join(lines) + ("\n" if lines else ""))
    cp = subprocess.run([sys.executable, str(MON), str(f), "--once"],
                        capture_output=True, text=True, timeout=60)
    try:
        return cp.returncode, json.loads(cp.stdout)
    except json.JSONDecodeError:
        return cp.returncode, {"_stdout": cp.stdout, "_stderr": cp.stderr}


def test_healthy_run() -> None:
    """POSITIVE CONTROL — and the baseline. A monitor that shouted on every stream would pass
    every negative case below while being useless, so this must read clean first."""
    print("a healthy run:")
    rc, r = run_once([init_evt(), tool_evt("view_file"),
                      subagent_evt("child-999", "lane-worker"), result_evt()])
    check("verdict working", r.get("verdict") == "working", str(r.get("verdict")))
    check("exit 0", rc == 0, f"rc={rc}")
    check("session id captured", (r.get("conversation_id") or "").startswith("conv-"))
    check("cwd and mode captured", r.get("cwd") == "/repo" and r.get("permission_mode") == "always-proceed")
    check("tool calls counted", r.get("tool_calls") == 2, str(r.get("tool_calls")))
    check("subagent tracked with its CHILD conversation id",
          r.get("subagents") == [{"conversation_id": "child-999", "type": "lane-worker"}],
          str(r.get("subagents")))
    check("no denials", r.get("denials") == [])


def test_no_result_event() -> None:
    print("stream with no result event (measured: all-unknown-event stream):")
    rc, r = run_once([init_evt(),
                      'warning: ignoring unsupported stream input message event "x"'])
    check("verdict no_result", r.get("verdict") == "no_result", str(r.get("verdict")))
    check("exit 2 so a caller can gate on it", rc == 2, f"rc={rc}")
    check("the warning was NOT swallowed", r.get("unparsed_lines") == 1, str(r.get("unparsed_lines")))
    check("the warning text is surfaced",
          any("unsupported stream input" in s for s in r.get("unparsed_sample", [])))


def test_in_progress_is_not_a_failure() -> None:
    """A live run has not failed, it has not finished. The first version of this monitor
    reported no_result + exit 2 on every healthy run it was watching -- found by pointing it at
    a real MiOS run, not by reading. A monitor that cries wolf on working runs gets ignored,
    which costs you the one time it is right."""
    print("run still in progress:")
    d = Path(tempfile.mkdtemp())
    f = d / "e.ndjson"
    f.write_text("\n".join([init_evt(), tool_evt("view_file"), tool_evt("run_command")]) + "\n")
    cp = subprocess.run([sys.executable, str(MON), str(f), "--once", "--stale-after-s", "3600"],
                        capture_output=True, text=True, timeout=60)
    r = json.loads(cp.stdout)
    check("verdict in_progress", r.get("verdict") == "in_progress", str(r.get("verdict")))
    check("exit 0 — not a failure", cp.returncode == 0, f"rc={cp.returncode}")
    check("stream_complete is false", r.get("stream_complete") is False)
    check("the staleness assumption is stated, not hidden",
          r.get("assumed_complete_after_s") == 3600 and "stream_idle_s" in r)


def test_stalled_run_is_not_in_progress() -> None:
    """NEGATIVE CONTROL for the above: a stream that stopped growing must NOT stay 'in_progress'
    forever, or the monitor can never report a hung run."""
    print("run stopped without ever producing a result:")
    d = Path(tempfile.mkdtemp())
    f = d / "e.ndjson"
    f.write_text("\n".join([init_evt(), tool_evt("view_file")]) + "\n")
    cp = subprocess.run([sys.executable, str(MON), str(f), "--once", "--stale-after-s", "0"],
                        capture_output=True, text=True, timeout=60)
    r = json.loads(cp.stdout)
    check("verdict no_result once the stream is stale", r.get("verdict") == "no_result",
          str(r.get("verdict")))
    check("exit 2", cp.returncode == 2, f"rc={cp.returncode}")


def test_vacuous_success() -> None:
    print("SUCCESS with nothing done:")
    rc, r = run_once([init_evt(), result_evt(response="")])
    check("verdict vacuous", r.get("verdict") == "vacuous", str(r.get("verdict")))
    check("exit 2", rc == 2, f"rc={rc}")
    check("the harness's own claim is kept for audit, not used as the verdict",
          r.get("harness_claimed_status") == "SUCCESS" and r.get("verdict") != "SUCCESS")


def test_denials_outrank_success() -> None:
    print("denied tool calls under a SUCCESS envelope:")
    rc, r = run_once([init_evt(), tool_evt("read_file"),
                      result_evt(denied_actions=[{"action": "read_file", "target": "/x"}])])
    check("verdict refused", r.get("verdict") == "refused", str(r.get("verdict")))
    check("the denial is carried", len(r.get("denials", [])) == 1)


def test_absent_stream_is_not_a_clean_run() -> None:
    """An absent file must not read as a quiet, healthy run — silence is not success."""
    print("stream file does not exist:")
    d = Path(tempfile.mkdtemp())
    cp = subprocess.run([sys.executable, str(MON), str(d / "nope.ndjson"), "--once"],
                        capture_output=True, text=True, timeout=60)
    r = json.loads(cp.stdout)
    check("verdict no_stream", r.get("verdict") == "no_stream", str(r.get("verdict")))
    check("exit 2", cp.returncode == 2, f"rc={cp.returncode}")
    check("it says the session may not have started", "may not have started" in (r.get("error") or ""))


def test_report_out_matches_stdout() -> None:
    """The pane view and the agent's report come from ONE state. If --report-out and stdout
    could differ, the operator and the monitoring agent would be looking at two runs."""
    print("report file matches the printed report:")
    d = Path(tempfile.mkdtemp())
    f = d / "e.ndjson"
    f.write_text("\n".join([init_evt(), tool_evt("run_command"), result_evt()]) + "\n")
    out = d / "report.json"
    cp = subprocess.run([sys.executable, str(MON), str(f), "--once", "--report-out", str(out)],
                        capture_output=True, text=True, timeout=60)
    check("report file written", out.is_file())
    if out.is_file():
        check("identical to stdout", json.loads(out.read_text()) == json.loads(cp.stdout))


def test_follow_renders_and_stops_when_idle() -> None:
    """The tmux pane path. It must render the same events and must not hang a test forever."""
    print("--follow (the tmux pane):")
    d = Path(tempfile.mkdtemp())
    f = d / "e.ndjson"
    f.write_text("\n".join([init_evt(), tool_evt("view_file"), result_evt()]) + "\n")
    cp = subprocess.run([sys.executable, str(MON), str(f), "--follow",
                         "--poll-s", "0.2", "--max-idle-s", "1"],
                        capture_output=True, text=True, timeout=60)
    check("exit 0 (a dead monitor takes the only view with it)", cp.returncode == 0)
    check("renders the session line", "cwd=/repo" in cp.stdout)
    check("renders tool calls", "tool view_file" in cp.stdout)
    check("renders the result", "result #1" in cp.stdout and "SUCCESS" in cp.stdout)
    check("prints a verdict when it stops", "verdict=" in cp.stdout)


def test_transcript_ui_element() -> None:
    """The transcript page is the UI element a client shows for a run. It must be openable with
    no network and no build step, and it must not disagree with the JSON report -- both come
    from the same State, and a page that says something the report does not is a second,
    unverified source of truth."""
    print("transcript UI element:")
    d = Path(tempfile.mkdtemp())
    f = d / "e.ndjson"
    f.write_text("\n".join([
        init_evt(), tool_evt("view_file"), subagent_evt("child-7", "lane-a"),
        'warning: ignoring unsupported stream input message event "z"',
        result_evt(denied_actions=[{"action": "command", "target": "rm"}]),
    ]) + "\n")
    html, rep_out = d / "t.html", d / "r.json"
    cp = subprocess.run([sys.executable, str(MON), str(f), "--once",
                         "--html", str(html), "--report-out", str(rep_out)],
                        capture_output=True, text=True, timeout=60)
    check("page written", html.is_file())
    if not html.is_file():
        return
    page = html.read_text()
    rep = json.loads(rep_out.read_text())
    check("self-contained: no external script or stylesheet",
          'src="http' not in page and 'href="http' not in page,
          "a transcript that needs the network is useless in a sandbox")
    check("mobile viewport", "width=device-width" in page)
    check("well-formed document", page.rstrip().endswith("</html>"))
    # five events in the fixture: init, tool, subagent, the warning line, result.
    check("renders every event as a row", page.count('class="row') == 5,
          f"got {page.count(chr(39) + 'class=' + chr(34) + 'row')} rows for 5 events")
    check("shows the derived verdict, not the harness's claim",
          ">refused<" in page and rep["verdict"] == "refused")
    check("surfaces the denial count", page.count("denials") >= 1 and len(rep["denials"]) == 1)
    check("surfaces the unparsed warning line", "unsupported stream input" in page,
          "the lines a json.loads monitor drops are exactly the ones worth showing")
    check("names the subagent child id", "child-7" in page)
    check("page and report agree on the verdict", f'>{rep["verdict"]}<' in page)


def test_stall_detector_ignores_prompt_echoes() -> None:
    """The detector that caught nothing, then caught itself.

    Watching t1001 I grepped the whole event stream for "wait for the background command" --
    a phrase the LANE OBJECTIVE quoted as a warning about attempt 2's failure. It matched the
    warning, inside two invoke_subagent events carrying that objective, and reported a
    regression while the run was perfectly healthy. A Self-Certifying Predicate: the subject's
    own given text satisfied the test.

    Verifying the fix returns 0 on a clean stream proves nothing on its own -- a detector that
    never fires also returns 0. Both directions are required."""
    print("stall detector (prompt echo vs genuine):")
    from agy_monitor import stall_signals

    phrase = "I will wait for the background command to finish execution."
    echo = json.dumps({"event": "step_update", "step_update": {
        "step_type": "subagent", "state": "DONE", "tool_name": "invoke_subagent",
        "subagent_info": {"subagents": [
            {"type_name": "lane", "initial_prompt": f"Do NOT do this: '{phrase}'"}]}}})
    genuine = json.dumps({"event": "step_update", "step_update": {
        "step_type": "agent_response", "state": "DONE",
        "text_delta": "I have launched the drift check and will wait for the background "
                      "command to finish execution."}})

    check("a prompt echo does NOT fire", stall_signals([echo]) == [],
          "matching text the agent was GIVEN is self-certifying")
    check("a genuine worker stall DOES fire", len(stall_signals([genuine])) == 1,
          "a detector that never fires also returns 0 on a clean stream")
    check("a mixed stream reports only the genuine one",
          stall_signals([echo, genuine]) == stall_signals([genuine]))
    check("the reported text is the worker's own words",
          "i have launched" in (stall_signals([genuine])[0] if stall_signals([genuine]) else ""))


def test_stall_reaches_the_verdict() -> None:
    """stall_signals() existed, was tested, and had ZERO call sites outside its own test.
    Detection that is never invoked is not detection. These assert the whole path: a worker
    announcing a background wait must change the verdict, appear in the report, and set a
    non-zero exit so a caller can gate on it."""
    print("a stall reaches the verdict (not just the helper):")
    stall = json.dumps({"event": "step_update", "step_update": {
        "step_type": "agent_response", "state": "DONE",
        "text_delta": "I have launched the drift check and will wait for the background "
                      "command to finish execution."}})
    rc, r = run_once([init_evt(), stall, result_evt()])
    check("verdict is stalled", r.get("verdict") == "stalled", str(r.get("verdict")))
    check("exit 2 so a caller can gate", rc == 2, f"rc={rc}")
    check("the stall text is in the report", len(r.get("stalls", [])) == 1)
    check("it outranks the harness's SUCCESS",
          r.get("harness_claimed_status") == "SUCCESS" and r.get("verdict") != "working")

    # NEGATIVE: a clean run must not be called stalled, or the signal is useless noise.
    rc2, r2 = run_once([init_evt(), tool_evt("view_file"), result_evt()])
    check("a clean run is NOT stalled", r2.get("verdict") == "working" and rc2 == 0,
          f"verdict={r2.get('verdict')} rc={rc2}")


def main() -> int:
    for t in (test_healthy_run, test_no_result_event, test_in_progress_is_not_a_failure,
              test_stalled_run_is_not_in_progress, test_vacuous_success,
              test_denials_outrank_success, test_absent_stream_is_not_a_clean_run,
              test_report_out_matches_stdout, test_follow_renders_and_stops_when_idle,
              test_transcript_ui_element, test_stall_detector_ignores_prompt_echoes,
              test_stall_reaches_the_verdict):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all monitor controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
