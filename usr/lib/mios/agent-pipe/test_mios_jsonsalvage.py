#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_jsonsalvage.loads_lenient (lenient JSON-grammar salvage for small-model output). Pure stdlib, no pytest/DB/network/server.py. Verifies the documented contract: clean objects round-trip, ```json fences/leading-trailing prose are stripped, trailing commas / // and /* */ comments / Python True/False/None|NaN|undefined literals / empty-value-after-colon are repaired, truncated tails are best-effort re-balanced, field-level harvest recovers scalars+flat arrays around an unrecoverable break, and the documented NEGATIVES return None (empty/None/whitespace, pure non-JSON, top-level arrays, single-quoted keys, unterminated strings). Also pins the surprising flat-harvest nested-key leak.
# AI-related: ./mios_jsonsalvage.py
# AI-functions: check, main
"""Unit tests for mios_jsonsalvage.loads_lenient (lenient JSON salvage)."""

import math
import sys

import mios_jsonsalvage as js

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_clean():
    # A clean object must round-trip byte-for-byte in value.
    r = js.loads_lenient('{"a": 1, "b": "two", "c": true, "d": null}')
    check("clean: parses to dict", isinstance(r, dict), repr(r))
    check("clean: exact values", r == {"a": 1, "b": "two", "c": True, "d": None}, repr(r))
    # Numbers (negatives + floats) survive.
    rn = js.loads_lenient('{"x": -3.14, "y": 42, "z": 0}')
    check("clean: numeric types", rn == {"x": -3.14, "y": 42, "z": 0}, repr(rn))
    # Empty object is a valid dict (not None).
    re_ = js.loads_lenient("{}")
    check("clean: empty object -> {}", re_ == {} and isinstance(re_, dict), repr(re_))
    # Nested scalars/arrays preserved (modulo the documented flat-harvest leak; see t_harvest_leak).
    rnest = js.loads_lenient('{"a": {"b": 1}, "c": [1, 2]}')
    check("clean: nested value preserved", rnest.get("a") == {"b": 1} and rnest.get("c") == [1, 2], repr(rnest))


def t_negatives():
    # Documented: returns None when it genuinely can't be salvaged.
    check("neg: None input -> None", js.loads_lenient(None) is None)
    check("neg: empty str -> None", js.loads_lenient("") is None)
    check("neg: whitespace -> None", js.loads_lenient("   \n\t ") is None)
    check("neg: pure prose -> None", js.loads_lenient("just some words, no json here") is None)
    # No harvestable "key": scalar pairs and no parseable object -> None.
    check("neg: braces but no json -> None", js.loads_lenient("{ this is : not json at all }") is None)
    # loads_lenient recovers an OBJECT only; a top-level array of SCALARS yields no
    # {...} span and is not a dict -> None. It never returns a list.
    check("neg: top-level scalar array -> None", js.loads_lenient("[1, 2, 3]") is None)
    # SURPRISE: a top-level array of OBJECTS is NOT None -- the greedy {...} extraction
    # reaches inside the brackets and salvages the embedded object(s) as a dict.
    check("neg: array-of-objects salvages inner dict", js.loads_lenient('[{"a": 1}]') == {"a": 1},
          repr(js.loads_lenient('[{"a": 1}]')))
    check("neg: array of two objects merges via span",
          js.loads_lenient('[{"a": 1}, {"b": 2}]') == {"a": 1, "b": 2},
          repr(js.loads_lenient('[{"a": 1}, {"b": 2}]')))
    # Whatever it returns is always a dict or None -- never a list.
    for raw in ("[1, 2, 3]", '[{"a": 1}]', '{"a": 1}', "garbage"):
        check(f"neg: never returns a list ({raw!r})", not isinstance(js.loads_lenient(raw), list))


def t_fenced():
    # ```json ... ``` fenced block: the fence prose is dropped by the {...} extraction.
    r = js.loads_lenient('```json\n{"intent": "agent", "news": true}\n```')
    check("fence: json-tagged stripped", r == {"intent": "agent", "news": True}, repr(r))
    # Bare ``` fence (no language tag) also works.
    r2 = js.loads_lenient('```\n{"a": 1}\n```')
    check("fence: bare fence stripped", r2 == {"a": 1}, repr(r2))


def t_prose():
    # Leading + trailing prose around the object is discarded.
    r = js.loads_lenient('Here is the refined plan: {"intent": "chat", "ok": true} -- hope that helps!')
    check("prose: surrounding text dropped", r == {"intent": "chat", "ok": True}, repr(r))
    # Greedy {...} spans from FIRST { to LAST } -> two prose-separated objects merge via harvest.
    r2 = js.loads_lenient('text {"a": 1} more {"b": 2} end')
    check("prose: greedy span harvests both", r2 == {"a": 1, "b": 2}, repr(r2))


def t_trailing_comma():
    check("tc: object trailing comma", js.loads_lenient('{"a": 1, "b": 2,}') == {"a": 1, "b": 2})
    check("tc: array trailing comma", js.loads_lenient('{"a": [1, 2, 3,]}') == {"a": [1, 2, 3]})
    check("tc: nested trailing commas", js.loads_lenient('{"a": [1,], "b": 2,}') == {"a": [1], "b": 2})


def t_python_literals():
    # Python True/False/None -> json true/false/null.
    r = js.loads_lenient('{"a": True, "b": False, "c": None}')
    check("pylit: True/False/None", r == {"a": True, "b": False, "c": None}, repr(r))
    # undefined/Undefined -> null.
    check("pylit: undefined -> null", js.loads_lenient('{"a": undefined}') == {"a": None})
    check("pylit: Undefined -> null", js.loads_lenient('{"a": Undefined}') == {"a": None})
    # NaN: json.loads accepts it natively -> a real float nan.
    rn = js.loads_lenient('{"a": NaN}')
    check("pylit: NaN -> float nan", isinstance(rn.get("a"), float) and math.isnan(rn["a"]), repr(rn))


def t_comments():
    # Line comments.
    check("cmt: // line comment", js.loads_lenient('{"a": 1, // explanation\n"b": 2}') == {"a": 1, "b": 2})
    # Block comments.
    check("cmt: /* block */ comment", js.loads_lenient('{/* lead */ "a": 1}') == {"a": 1})
    check("cmt: inline block comment", js.loads_lenient('{"a": 1 /* mid */, "b": 2}') == {"a": 1, "b": 2})


def t_empty_value():
    # Empty value after a colon (the failure) -> null, rest preserved.
    r = js.loads_lenient('{"a": , "b": 2}')
    check("empty: colon-then-comma -> null", r == {"a": None, "b": 2}, repr(r))
    r2 = js.loads_lenient('{"intent": "agent", "inventory_filter": , "news": true}')
    check("empty: mid-field empty preserves neighbors",
          r2 == {"intent": "agent", "inventory_filter": None, "news": True}, repr(r2))
    # Empty value right before a closing brace.
    r3 = js.loads_lenient('{"a": 1, "b": }')
    check("empty: before closing brace -> null", r3 == {"a": 1, "b": None}, repr(r3))


def t_truncated():
    # Unterminated object (missing closing brace) -> best-effort re-balance recovers all fields.
    check("trunc: missing close brace", js.loads_lenient('{"a": 1, "b": 2') == {"a": 1, "b": 2})
    # Unterminated array value -> closers appended.
    check("trunc: unterminated array", js.loads_lenient('{"a": [1, 2, 3') == {"a": [1, 2, 3]})
    # Truncated at a partial trailing field -> drop the partial, keep the valid prefix.
    check("trunc: partial trailing field dropped",
          js.loads_lenient('{"a": 1, "b": 2, "bad": ') == {"a": 1, "b": 2})
    # Only an opening brace -> re-balanced to an empty object (documented: dict not None).
    check("trunc: lone opening brace -> {}", js.loads_lenient("{") == {})
    # An unterminated STRING value is NOT recoverable -> None (documented contract).
    check("trunc: unterminated string -> None", js.loads_lenient('{"a": "hello') is None)


def t_harvest():
    # Field-level harvest: a hard break mid-object still yields the well-formed scalar/array pairs.
    r = js.loads_lenient('{"intent": "agent", "news": true, this is broken garbage')
    check("harvest: scalars before break", r == {"intent": "agent", "news": True}, repr(r))
    # Flat array harvest.
    ra = js.loads_lenient('{"hint_tools": ["web_search", "open_app"], then junk')
    check("harvest: flat array", ra == {"hint_tools": ["web_search", "open_app"]}, repr(ra))
    # bool/null scalars harvested out of a broken envelope.
    rb = js.loads_lenient('{"flag": false, "x": null, GARBAGE')
    check("harvest: bool+null scalars", rb == {"flag": False, "x": None}, repr(rb))
    # A negative-number scalar harvested.
    rn = js.loads_lenient('{"score": -7, broken')
    check("harvest: negative number", rn == {"score": -7}, repr(rn))


def t_quirks():
    # Single-quoted keys are NOT a documented repair -> they don't parse and harvest finds no
    # double-quoted pairs -> None. Pin this so a future "add single-quote repair" is a conscious change.
    check("quirk: single-quoted obj -> None", js.loads_lenient("{'a': 1}") is None)
    # Duplicate keys: strict json semantics (last wins) carry through.
    check("quirk: duplicate keys last-wins", js.loads_lenient('{"a": 1, "a": 2}') == {"a": 2})
    # Escaped quotes inside a string value survive intact.
    re_ = js.loads_lenient('{"a": "he said \\"hi\\""}')
    check("quirk: escaped quotes preserved", re_ == {"a": 'he said "hi"'}, repr(re_))


def t_harvest_leak():
    # SURPRISE (documented contract, not a test bug): the flat field-harvest regex ignores nesting,
    # so an inner "key": scalar leaks to the top level via setdefault even when the structural parse
    # already succeeded. Pin the ACTUAL behavior so a future fix is a deliberate, visible change.
    r = js.loads_lenient('{"a": {"x": 1}}')
    check("leak: inner key leaks to top level", r == {"a": {"x": 1}, "x": 1}, repr(r))
    r2 = js.loads_lenient('{"a": {"b": 1}, "c": [1, 2]}')
    check("leak: inner 'b' leaks alongside top keys", r2 == {"a": {"b": 1}, "c": [1, 2], "b": 1}, repr(r2))
    # The leak only fills MISSING keys (setdefault): a real top-level key is never overwritten.
    r3 = js.loads_lenient('{"a": {"b": 9}, "b": 1}')
    check("leak: setdefault does not overwrite real top key", r3 == {"a": {"b": 9}, "b": 1}, repr(r3))


def main():
    t_clean()
    t_negatives()
    t_fenced()
    t_prose()
    t_trailing_comma()
    t_python_literals()
    t_comments()
    t_empty_value()
    t_truncated()
    t_harvest()
    t_quirks()
    t_harvest_leak()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
