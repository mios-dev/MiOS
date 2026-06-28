# AI-hint: Normalizes raw tool/terminal output into a context-safe format by preserving the head and tail while eliding the middle with a specific marker to prevent context window saturation while preserving critical end-of-command results.
# AI-functions: _omit_marker, normalize_output
"""mios_aci -- pure Agent-Computer Interface output normalizer (WS-5).

DB-free + stdlib-only so the truncation logic unit-tests in isolation
(sibling-module pattern, like mios_sched / mios_evict / mios_hitl).

The problem: feeding raw tool/terminal output back to a model either saturates
the context window or, with a naive head-only slice (`out[:N]`), DROPS THE TAIL
-- which for command/terminal output is exactly where the error, exit code, or
final result lands. The ACI pattern keeps the most informative ENDS (head AND
tail) and elides the middle with an explicit, anti-fabrication marker, bounding
both line count and char count.

server.py owns the knobs + where this is applied; this module owns the pure
transform.
"""

from __future__ import annotations


def _omit_marker(kind: str, n: int, label: str) -> str:
    lbl = f"{label}: " if label else ""
    return (f"\n…⟪{lbl}{n} {kind} OMITTED from the middle — NOT shown. Report "
            f"ONLY the content shown above and below and say it continues. Do "
            f"NOT infer, complete, or invent the omitted {kind}, items, PIDs, "
            f"names, counts, or values.⟫\n")


def normalize_output(text, *, max_chars: int, max_lines: int = 0,
                     head_frac: float = 0.6, label: str = "") -> str:
    """Bound `text` to a context budget by keeping the head AND the tail and
    eliding the middle with a marker. Applies an optional line cap first, then a
    char cap. Returns `text` unchanged when already within budget.

    head_frac in (0,1) splits the kept budget between head and tail; the default
    keeps slightly more head (early context) while preserving the tail (the
    result/error). Degrade-open: any error returns a plain head slice."""
    try:
        text = text if isinstance(text, str) else str(text)
        hf = min(0.95, max(0.05, float(head_frac)))
        # (1) line cap -- keep head_n + tail_n lines.
        if max_lines and max_lines > 0:
            lines = text.splitlines()
            if len(lines) > max_lines:
                head_n = max(1, int(max_lines * hf))
                tail_n = max(1, max_lines - head_n)
                omitted = len(lines) - head_n - tail_n
                if omitted > 0:
                    text = ("\n".join(lines[:head_n])
                            + _omit_marker("lines", omitted, label)
                            + "\n".join(lines[-tail_n:]))
        # (2) char cap -- keep head_c + tail_c chars.
        if max_chars and max_chars > 0 and len(text) > max_chars:
            head_c = max(1, int(max_chars * hf))
            tail_c = max(1, max_chars - head_c)
            omitted = len(text) - head_c - tail_c
            if omitted > 0:
                text = (text[:head_c].rstrip()
                        + _omit_marker("characters", omitted, label)
                        + text[-tail_c:].lstrip())
        return text
    except Exception:  # noqa: BLE001 -- normalization must never raise
        try:
            return text[:max_chars] if max_chars and max_chars > 0 else text
        except Exception:  # noqa: BLE001
            return text
