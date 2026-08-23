# AI-hint: Provides a dependency-free, regex-based JSON parser to recover malformed JSON objects from small-model outputs by repairing common syntax errors like trailing commas, comments, and empty values.
# AI-functions: loads_lenient
from __future__ import annotations

import json
import re

__all__ = ["loads_lenient"]


def loads_lenient(content: str) -> "dict | None":
    if not content:
        return None
    m = re.search(r"\{.*\}", content, flags=re.DOTALL)
    base = m.group(0) if m else content
    cands = [base]
    r = re.sub(r"/\*.*?\*/", "", base, flags=re.DOTALL)   # block comments
    r = re.sub(r"(?m)//.*$", "", r)                        # line comments
    r = re.sub(r"\bTrue\b", "true", r)                     # python -> json literals
    r = re.sub(r"\bFalse\b", "false", r)
    r = re.sub(r"\b(?:None|NaN|Undefined|undefined)\b", "null", r)
    r = re.sub(r":\s*(?=[,}\]])", ": null", r)             # empty value -> null
    r = re.sub(r",\s*(?=[}\]])", "", r)                    # trailing comma
    cands.append(r)
    _opens = r.count("{") - r.count("}")
    _brk = r.count("[") - r.count("]")
    if _opens > 0 or _brk > 0:
        cands.append(r + ("]" * max(0, _brk)) + ("}" * max(0, _opens)))
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
