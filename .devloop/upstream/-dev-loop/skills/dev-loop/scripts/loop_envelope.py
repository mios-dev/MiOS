#!/usr/bin/env python3
"""
loop_envelope.py — normalise any harness's run envelope into the canonical `loop.v1` shape.

P0 of the loop translation layer (docs/decisions/0001-loop-translation-layer-*.md,
references/translation-layer.md 5.1). Three real dialects with ZERO shared field names:

  agy --output-format json          {conversation_id,status,response,num_turns,usage,
                                     duration_seconds, error?, denied_actions?}
  agy --output-format stream-json   {"event":"result","result":{ ...identical keys... }}
  claude -p --output-format json    {result,num_turns,permission_denials?}

Two rules this module exists to enforce, both from SKILL.md 6-7:

  1. NEVER trust the harness's own `status`, and never trust exit 0. A harness that reported
     SUCCESS over an empty response having changed nothing is the defect we are hunting.
     `status` here is DERIVED from evidence -- the worktree diff and the control results --
     and `vacuous` is a first-class terminal state, not a warning printed beside `delivered`.

  2. Absence of an envelope is NOT success. A stream whose events are all unknown produces no
     result event at all (measured), and that is reported as `errored`.

Cumulative counters: `num_turns` and `duration_seconds` from agy are CUMULATIVE ACROSS THE
SESSION, not per-turn (measured: successive results read 1 -> 2 turns, 1.20s -> 2.29s). They are
carried through as cumulative and labelled as such; callers wanting a per-turn delta subtract.

Conditional keys: `error` and `denied_actions` are ABSENT on success, not null (measured success
key set is exactly conversation_id, duration_seconds, num_turns, response, status, usage). Every
read here goes through .get().
"""
from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = "loop.v1"

# Terminal statuses. Order matters: this is the precedence used when several could apply,
# strongest failure first, so a denied AND empty run reports `refused` rather than `vacuous`.
STATUSES = ("errored", "timed_out", "control_invalid", "gate_failed",
            "refused", "vacuous", "delivered")

DENIAL_KEYS = ("permission_denials", "denied_actions")
TEXT_KEYS = ("response", "result", "output", "text", "content")


class EnvelopeError(ValueError):
    """Raised when there is nothing to normalise. Never downgraded to a success."""


def unwrap(raw: Any) -> dict:
    """Accept a bare result object or a stream-json {"event":"result","result":{...}} wrapper.

    Measured: the two agy framings carry the SAME payload; stream-json only wraps it.
    """
    if not isinstance(raw, dict):
        raise EnvelopeError(f"envelope is {type(raw).__name__}, not an object")
    if raw.get("event") == "result" and isinstance(raw.get("result"), dict):
        return raw["result"]
    # A stream-json line for any other event is not a run envelope.
    if "event" in raw and "result" not in raw:
        raise EnvelopeError(f"not a result event: {raw.get('event')!r}")
    return raw


def denials_of(env: dict) -> list:
    for k in DENIAL_KEYS:
        v = env.get(k)
        if v:
            return list(v)
    return []


def text_of(env: dict) -> str:
    for k in TEXT_KEYS:
        v = env.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def derive_status(env: dict, evidence: dict) -> str:
    """Derive the terminal status from EVIDENCE, never from env['status'] or an exit code.

    evidence keys (all optional; absent means 'not measured', which is never a pass):
      diff_bytes   int   size of the lane's worktree diff
      positive     bool  positive control exit == 0
      negative     bool  negative control failed FOR THE PLANTED REASON
      tree_restored bool negative control left the tree as it found it
      timed_out    bool  outer wall-clock killed it
      exit_code    int   the process exit code
    """
    if evidence.get("timed_out"):
        return "timed_out"          # a killed step is a failure, never a pass (SKILL 7)
    if env.get("error") or (evidence.get("exit_code") not in (None, 0)):
        return "errored"
    if denials_of(env):
        return "refused"

    pos, neg = evidence.get("positive"), evidence.get("negative")
    if evidence.get("tree_restored") is False:
        return "control_invalid"    # a control that leaks fixtures inverts the proof
    if pos is False or neg is False:
        return "gate_failed"        # neg False == the negative control did NOT fail: vacuous gate

    diff = evidence.get("diff_bytes")
    if diff is not None and diff <= 0:
        return "vacuous"            # claimed success, denied nothing, changed nothing

    if pos is True and neg is True and (diff or 0) > 0:
        return "delivered"
    # Not enough evidence to claim delivery. Refuse to invent one.
    return "vacuous" if diff is not None else "gate_failed"


def normalize(raw: Any, *, harness: str, run_id: str = "", lane_id: str = "",
              evidence: dict | None = None) -> dict:
    """Envelope (any dialect) + evidence -> loop.v1. Raises EnvelopeError on nothing-to-read."""
    evidence = dict(evidence or {})
    env = unwrap(raw)
    return {
        "schema": SCHEMA_VERSION,
        "run_id": run_id,
        "lane_id": lane_id,
        "harness": harness,
        "status": derive_status(env, evidence),
        "text": text_of(env),
        "turns": env.get("num_turns"),
        "turns_are_cumulative": harness == "antigravity",
        "denials": denials_of(env),
        "usage": env.get("usage") or {},
        "duration_s": env.get("duration_seconds"),
        "error": env.get("error"),
        "evidence": evidence,
        "harness_claimed_status": env.get("status"),  # kept for audit, NEVER used for status
    }


def normalize_stream(lines, *, harness: str, **kw) -> dict:
    """Normalise the LAST result event of an NDJSON stream.

    A stream with no result event at all raises rather than returning a success-shaped
    object: measured, a stream of unknown events produces exactly that and it must not
    be mistaken for a clean run.
    """
    last = None
    seen = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        seen += 1
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and doc.get("event") == "result":
            last = doc
    if last is None:
        raise EnvelopeError(f"stream carried no result event ({seen} line(s) read) — nothing ran")
    return normalize(last, harness=harness, **kw)
