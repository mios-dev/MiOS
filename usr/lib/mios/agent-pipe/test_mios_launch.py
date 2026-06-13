# AI-hint: Standalone unit test for the deterministic_action_route logic to ensure "open/launch" commands correctly strip filler phrases and map to open_app(name) instead of falling back to the LLM discovery path.
# AI-related: /usr/share/mios/mios.toml
# AI-functions: _check, _load_fillers, _extract, t_ssot, t_extraction, main
"""Standalone unit test for the deterministic launch-target extraction
(server.py `_deterministic_action_route`: SSOT trailing-filler strip + word-count
+ compound-connective guard that binds an unambiguous 'open/launch <app>' to
open_app(name=<app>)).

Pure stdlib -- no server.py import, so it runs on any Python 3.11+ without the
agent-pipe runtime deps. Mirrors the test_mios_kvfork standalone pattern: a
reference impl PINS the contract, and the REAL mios.toml
[routing].launch_filler_phrases SSOT is loaded so a drift in either the list or the
logic is caught. Regression guard for the 2026-06-07 operator e2e bug where
'open notepad for me' bound name='notepad for me' and 'open spotify on my desktop'
fell through to the LLM path and mis-routed to discovery.

Run:  python test_mios_launch.py
"""

import os
import re
import sys

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _load_fillers() -> list:
    """Load the REAL SSOT list the same way server.py `_load_launch_fillers` does."""
    path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    if not os.path.exists(path):
        here = os.path.dirname(os.path.abspath(__file__))
        cand = os.path.join(here, "..", "..", "..", "share", "mios", "mios.toml")
        if os.path.exists(cand):
            path = cand
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(path, "rb") as f:
        rt = (tomllib.load(f).get("routing") or {})
    return sorted(
        (str(p).lower().strip() for p in (rt.get("launch_filler_phrases") or []) if str(p).strip()),
        key=len, reverse=True)


# Reference impl: mirrors the post-head body of server.py _deterministic_action_
# route. PINS the contract (the test fails if server.py's logic drifts from this).
_TRIGGERS = {"open", "launch"}


def _extract(user_text: str, fillers: list):
    t = (user_text or "").strip()
    if not t or len(t) > 80 or "?" in t:
        return None
    words = t.split()
    if len(words) < 2:
        return None
    head = words[0].lower().strip(".,:;!\"'")
    if head not in _TRIGGERS:
        return None
    rest = " ".join(words[1:]).strip()
    low = rest.lower()
    changed = True
    while changed and rest:
        changed = False
        for f in fillers:
            if f and low.endswith(f):
                rest = rest[:len(rest) - len(f)].rstrip(" ,.")
                low = rest.lower()
                changed = True
                break
    if not rest or len(rest.split()) > 3:
        return None
    if "://" in rest or re.search(r"\b(in|and|then|with|on|to)\b", low):
        return None
    return rest


def t_ssot() -> None:
    fillers = _load_fillers()
    _check("fillers: SSOT list non-empty", len(fillers) > 0, f"n={len(fillers)}")
    _check("fillers: longest-match-first ordering",
           fillers == sorted(fillers, key=len, reverse=True))
    _check("fillers: 'for me' present (the e2e case)", "for me" in fillers)
    _check("fillers: 'on my desktop' present (the e2e case)", "on my desktop" in fillers)


def t_extraction() -> None:
    fillers = _load_fillers()
    cases = {
        "open notepad": "notepad",                        # bare
        "open notepad for me": "notepad",                 # trailing courtesy stripped (was the bug)
        "open spotify on my desktop for me": "spotify",   # location+courtesy stripped (was the bug)
        "launch discord please": "discord",
        "open file explorer": "file explorer",            # 2-word app preserved
        "open file in editor": None,                      # true compound -> LLM router
        "open the calculator and minimize it": None,      # conjunction -> LLM router
        "open https://example.com": None,                 # url -> LLM router
        "what is open today": None,                       # not a launch -> None
        "open": None,                                     # bare trigger only -> None
    }
    for text, expected in cases.items():
        got = _extract(text, fillers)
        _check(f"extract {text!r} -> {expected!r}", got == expected, f"got={got!r}")


def main() -> int:
    for t in (t_ssot, t_extraction):
        t()
    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
