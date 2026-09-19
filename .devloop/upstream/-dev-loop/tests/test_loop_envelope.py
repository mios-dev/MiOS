#!/usr/bin/env python3
"""
Two-sided controls for loop_envelope.normalize (P0 of the loop translation layer).

Every envelope below was RECORDED from a real run, not invented. Provenance is on each
fixture. The point of the suite is not that normalisation works on happy data -- it is that
the three failure shapes the design exists to catch cannot be normalised into a success:

  * a harness that says SUCCESS having changed nothing            -> vacuous, never delivered
  * a negative control that PASSED (i.e. failed to fail)          -> gate_failed
  * a stream that produced no result event at all                 -> raises, never returns

Run: python3 tests/test_loop_envelope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "dev-loop" / "scripts"))

from loop_envelope import EnvelopeError, normalize, normalize_stream  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


# --------------------------------------------------------------------------- fixtures
# RECORDED 2026-09-19 from `agy -p 'Reply with exactly: PROBE_OK' --output-format json`.
AGY_JSON_SUCCESS = {
    "conversation_id": "da9f0586-3cf2-4753-8526-f0dcd1aa83b7",
    "status": "SUCCESS", "response": "PROBE_OK\n",
    "duration_seconds": 2.657665837, "num_turns": 1,
    "usage": {"input_tokens": 12569, "output_tokens": 38, "thinking_tokens": 34,
              "cache_read_tokens": 0, "total_tokens": 12607},
}
# RECORDED from the same command with the keyring daemon down.
AGY_JSON_ERROR = {
    "conversation_id": "", "status": "ERROR", "response": "",
    "error": "authentication failed or timed out",
    "duration_seconds": 0, "num_turns": 0,
    "usage": {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0,
              "cache_read_tokens": 0, "total_tokens": 0},
}
# RECORDED from --output-format stream-json: the SAME payload, wrapped.
AGY_STREAM_RESULT = {"event": "result", "result": dict(AGY_JSON_SUCCESS)}
# RECORDED shape of the silent-failure envelope described in SKILL.md 10.
AGY_DENIED = {"conversation_id": "x", "status": "SUCCESS", "response": "",
              "num_turns": 1, "denied_actions": [{"action": "read_file", "target": "/repo"}]}
CLAUDE_JSON = {"result": "done", "num_turns": 3, "permission_denials": []}

GOOD = {"diff_bytes": 512, "positive": True, "negative": True, "tree_restored": True,
        "exit_code": 0}


def test_dialects() -> None:
    print("dialect coverage:")
    a = normalize(AGY_JSON_SUCCESS, harness="antigravity", evidence=GOOD)
    s = normalize(AGY_STREAM_RESULT, harness="antigravity", evidence=GOOD)
    c = normalize(CLAUDE_JSON, harness="claude-code", evidence=GOOD)

    check("agy json text", a["text"] == "PROBE_OK\n")
    check("claude text comes from 'result'", c["text"] == "done")
    check("agy turns", a["turns"] == 1)
    check("claude turns", c["turns"] == 3)
    check("agy usage carried", a["usage"]["total_tokens"] == 12607)
    check("agy duration carried", a["duration_s"] == 2.657665837)
    # The two agy framings must normalise IDENTICALLY -- if they ever diverge, one of them
    # is being read with a field name the other does not have.
    check("json and stream-json framings normalise identically", a == s,
          "same payload, different wrapper — any difference is a mapping bug")
    check("cumulative flag set for agy only",
          a["turns_are_cumulative"] is True and c["turns_are_cumulative"] is False)


def test_status_is_derived_not_trusted() -> None:
    print("status derivation (the harness's own word is never used):")
    # The central case: harness says SUCCESS, nothing changed.
    v = normalize(AGY_JSON_SUCCESS, harness="antigravity",
                  evidence={**GOOD, "diff_bytes": 0})
    check("SUCCESS + empty diff -> vacuous", v["status"] == "vacuous",
          f"got {v['status']}: this is the defect the whole layer exists to catch")
    check("the harness's claim is retained for audit only",
          v["harness_claimed_status"] == "SUCCESS" and v["status"] != "SUCCESS")

    d = normalize(AGY_DENIED, harness="antigravity", evidence={**GOOD, "diff_bytes": 0})
    check("denials outrank vacuity -> refused", d["status"] == "refused")
    check("denials extracted from denied_actions", len(d["denials"]) == 1)

    cd = normalize({"result": "", "num_turns": 1,
                    "permission_denials": [{"tool": "Bash"}]},
                   harness="claude-code", evidence=GOOD)
    check("claude denials extracted from permission_denials", cd["status"] == "refused")

    e = normalize(AGY_JSON_ERROR, harness="antigravity", evidence={"diff_bytes": 0})
    check("error field -> errored", e["status"] == "errored")
    check("error text preserved", "authentication" in (e["error"] or ""))

    t = normalize(AGY_JSON_SUCCESS, harness="antigravity",
                  evidence={**GOOD, "timed_out": True})
    check("timeout is a failure, never a pass", t["status"] == "timed_out")

    nz = normalize(AGY_JSON_SUCCESS, harness="antigravity",
                   evidence={**GOOD, "exit_code": 3})
    check("non-zero exit -> errored even when the envelope says SUCCESS",
          nz["status"] == "errored")


def test_gate_failures() -> None:
    print("gate outcomes:")
    g = normalize(AGY_JSON_SUCCESS, harness="antigravity",
                  evidence={**GOOD, "negative": False})
    check("negative control that PASSED -> gate_failed", g["status"] == "gate_failed",
          "a negative control which did not fail is a vacuous gate; never merge it")
    p = normalize(AGY_JSON_SUCCESS, harness="antigravity",
                  evidence={**GOOD, "positive": False})
    check("failed positive control -> gate_failed", p["status"] == "gate_failed")
    l = normalize(AGY_JSON_SUCCESS, harness="antigravity",
                  evidence={**GOOD, "tree_restored": False})
    check("fixture leak -> control_invalid", l["status"] == "control_invalid")

    # Only a fully-evidenced run may be called delivered.
    ok = normalize(AGY_JSON_SUCCESS, harness="antigravity", evidence=GOOD)
    check("fully evidenced run -> delivered", ok["status"] == "delivered")
    thin = normalize(AGY_JSON_SUCCESS, harness="antigravity", evidence={"diff_bytes": 900})
    check("diff alone is not enough for delivered", thin["status"] != "delivered",
          "controls unmeasured means unproven, not passed")


def test_absence_is_not_success() -> None:
    print("absence of an envelope:")
    # Measured: a stream whose events are all unknown yields no result event at all.
    stream = ['{"event":"init","init":{"tools":[]}}',
              'warning: ignoring unsupported stream input message event "__x__"']
    try:
        normalize_stream(stream, harness="antigravity")
        check("stream with no result raises", False, "it returned an object instead")
    except EnvelopeError as ex:
        check("stream with no result raises", True)
        check("the raise names the cause", "no result event" in str(ex))

    try:
        normalize("not an object", harness="antigravity")
        check("non-object envelope raises", False)
    except EnvelopeError:
        check("non-object envelope raises", True)

    try:
        normalize({"event": "step_update", "step_update": {}}, harness="antigravity")
        check("a non-result stream event is not an envelope", False)
    except EnvelopeError:
        check("a non-result stream event is not an envelope", True)

    # A stream WITH a result must still work, and must take the LAST one (per-turn results).
    two = [json.dumps({"event": "result", "result": {**AGY_JSON_SUCCESS, "num_turns": 1}}),
           json.dumps({"event": "result", "result": {**AGY_JSON_SUCCESS, "num_turns": 2,
                                                     "response": "second"}})]
    got = normalize_stream(two, harness="antigravity", evidence=GOOD)
    check("last result wins in a multi-turn stream", got["turns"] == 2 and got["text"] == "second")


def main() -> int:
    for t in (test_dialects, test_status_is_derived_not_trusted,
              test_gate_failures, test_absence_is_not_success):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all loop.v1 envelope controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
