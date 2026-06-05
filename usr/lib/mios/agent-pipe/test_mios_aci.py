"""Standalone unit test for mios_aci.normalize_output (WS-5 ACI normalizer).

Pure stdlib + the sibling module only. Run:  python test_mios_aci.py
"""

import sys

from mios_aci import normalize_output as N

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_within_budget() -> None:
    s = "short output"
    _check("within: char unchanged", N(s, max_chars=1000) == s)
    _check("within: line unchanged", N("a\nb\nc", max_chars=1000, max_lines=10)
           == "a\nb\nc")


def t_char_head_tail() -> None:
    body = "HEAD_START" + ("x" * 5000) + "TAIL_END_ERROR"
    out = N(body, max_chars=400, label="cmd")
    _check("char: bounded-ish", len(out) < 900, f"len={len(out)}")  # budget + marker
    _check("char: keeps head", "HEAD_START" in out)
    _check("char: keeps TAIL (the result/error)", "TAIL_END_ERROR" in out, out[-40:])
    _check("char: has omit marker", "OMITTED from the middle" in out)
    _check("char: labelled", "cmd:" in out)


def t_line_head_tail() -> None:
    lines = "\n".join(f"line{i}" for i in range(200))
    out = N(lines, max_chars=100000, max_lines=20)
    _check("line: keeps first", "line0" in out)
    _check("line: keeps last (tail)", "line199" in out, out[-30:])
    _check("line: drops middle", "line100" not in out)
    _check("line: marks omitted lines", "lines OMITTED" in out)


def t_head_frac() -> None:
    body = "A" * 1000 + "B" * 1000
    # head_frac 0.9 -> mostly head (A's), little tail (B's)
    out = N(body, max_chars=200, head_frac=0.9)
    head_len = out.split("…⟪")[0].count("A")
    _check("frac: head dominates at 0.9", head_len >= 150, f"head A's={head_len}")


def t_degrade_open() -> None:
    # non-string coerced, never raises
    _check("degrade: int coerced", isinstance(N(12345, max_chars=3), str))
    _check("degrade: zero budget no-op", N("abc", max_chars=0) == "abc")


def main() -> int:
    for t in (t_within_budget, t_char_head_tail, t_line_head_tail, t_head_frac,
              t_degrade_open):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
