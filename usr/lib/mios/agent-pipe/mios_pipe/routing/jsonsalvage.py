# AI-hint: Provides a dependency-free, regex-based JSON parser to recover malformed JSON objects from small-model outputs by repairing common syntax errors like trailing commas, comments, and empty values.
# AI-functions: loads_lenient
"""Generic JSON-grammar salvage for small-model output.

Extracted from server.py (modularization). Pure stdlib (re + json) --
NO coupling to the agent-pipe globals, NO schema/field/topic/English knowledge.
This is the FIRST module split out of the 19k-line monolith; keep it dependency-free
so it stays trivially testable and importable.
"""
from __future__ import annotations

import json
import re

__all__ = ["loads_lenient"]


def loads_lenient(content: str) -> "dict | None":
    """Best-effort recovery of a JSON OBJECT from a small model's NEAR-json output.
    operator binding NO-HARDCODES: this is generic STRUCTURAL repair of the JSON
    grammar -- it knows nothing about the schema, fields, topics, or any English.

    A tiny refine/planner model (qwen3:1.7b) intermittently emits ONE malformed
    token -- an empty value after a colon (`"k":` then `,`/`}`), a trailing comma,
    a // or /* */ comment, a Python True/False/None literal, or a truncated tail --
    and strict json.loads then DISCARDS THE ENTIRE otherwise-perfect object. That
 is the failure: refine produced a flawless trending plan
    (intent=agent, news=true, a clean refined_text) but one empty `inventory_filter`
    field at line 11 made json.loads raise -> the whole plan was dropped -> the
    degraded fallback web-searched "worldwide trends today" (dictionary/shipping
    junk) and punted. Recover the object instead of throwing it away.

    Returns the parsed dict, or None if it genuinely can't be salvaged."""
    if not content:
        return None
    # Outermost {...} object: drop any leading prose / trailing junk around it.
    m = re.search(r"\{.*\}", content, flags=re.DOTALL)
    base = m.group(0) if m else content
    cands = [base]
    # Generic JSON-grammar repairs (no field/topic knowledge):
    r = re.sub(r"/\*.*?\*/", "", base, flags=re.DOTALL)   # block comments
    r = re.sub(r"(?m)//.*$", "", r)                        # line comments
    r = re.sub(r"\bTrue\b", "true", r)                     # python -> json literals
    r = re.sub(r"\bFalse\b", "false", r)
    r = re.sub(r"\b(?:None|NaN|Undefined|undefined)\b", "null", r)
    r = re.sub(r":\s*(?=[,}\]])", ": null", r)             # empty value -> null
    r = re.sub(r",\s*(?=[}\]])", "", r)                    # trailing comma
    cands.append(r)
    # Truncated tail: append the missing closers (best-effort brace/bracket balance).
    _opens = r.count("{") - r.count("}")
    _brk = r.count("[") - r.count("]")
    if _opens > 0 or _brk > 0:
        cands.append(r + ("]" * max(0, _brk)) + ("}" * max(0, _opens)))
    # Truncate-at-error: parse the VALID PREFIX up to the first bad token, drop the
    # partial trailing field, re-balance the closers. Recovers every field BEFORE
    # the malformed one (in the refine envelope intent/refined_text/news/... lead).
    try:
        json.loads(r)
    except json.JSONDecodeError as e:
        head = r[:max(0, e.pos)]
        _cut = max(head.rfind(","), head.rfind("{"))
        if _cut > 0:
            head = head[:_cut].rstrip().rstrip(",")
            head = head + ("]" * max(0, head.count("[") - head.count("]"))) \
                        + ("}" * max(0, head.count("{") - head.count("}")))
            cands.append(head)
    except Exception:  # noqa: BLE001
        pass
    _best = None
    for cand in cands:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                _best = obj
                break
        except Exception:  # noqa: BLE001 -- try the next repair candidate
            continue
    # FIELD-LEVEL harvest: pull every well-formed top-level "key": <scalar|flat-
    # array> pair and IGNORE the one malformed field, so a SINGLE bad token (on
    # ANY line) can never sink the whole plan (two refine
    # parse-fails in a row at "line 11" each discarded a correct intent/
    # refined_text/news -> punt). NO field/topic knowledge -- it harvests whatever
    # keys are present; routing needs only the scalars (intent/refined_text/news/
    # target_agent/...) + flat arrays (hint_tools). MERGED UNDER the structural
    # parse so a truncate-at-error recovery still regains fields AFTER the break.
    flat: dict = {}
    for am in re.finditer(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*(\[[^\[\]]*\])', base):
        try:
            flat[am.group(1)] = json.loads(am.group(2))
        except Exception:  # noqa: BLE001
            continue
    for fm in re.finditer(
            r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*'
            r'("(?:[^"\\]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?)', base):
        if fm.group(1) not in flat:
            try:
                flat[fm.group(1)] = json.loads(fm.group(2))
            except Exception:  # noqa: BLE001
                continue
    if _best is not None:
        for _k, _v in flat.items():
            _best.setdefault(_k, _v)   # fill only the keys the parse missed
        return _best
    return flat or None
