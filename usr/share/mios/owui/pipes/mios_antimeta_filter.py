# AI-hint: Processes the OWUI output stream to wrap meta-narrative and reasoning lines in <think> tags for collapsible UI rendering while stripping hard refusal patterns based on the system's central refusal-patterns.txt.
# AI-related: /usr/share/mios/ai/, /usr/share/mios/ai/refusal-patterns.txt, mios-agent-nudger, mios-delegation-prefilter
# AI-functions: _is_narration_line, __init__, _reload, _strip_refusals, _transform_lines, _flush_narration, _process, stream, outlet, class Filter, class Valves
"""
title: MiOS Anti-Meta Filter
author: MiOS
version: 1.1.0
description: |
  Per-line stream filter that DETECTS narration/meta-speak lines
  ("Let me check X", "I need to Y", "I'll try Z") and WRAPS them
  in <think>...</think> tags so OWUI renders them inside its
  native collapsible "Thinking" block, OUT of the final answer
  body. Final-answer content passes through untouched.

  Operator directive 2026-05-16: "ALL THESE MIOS-HERMES AGENTS
  THINKING PRINTS COULD BE EMMITED AND/OR COLLAPSABLE AS THINKING
  IN OWUI". Previously this filter just stripped meta-speak; now
  it preserves the lines as collapsible thinking so the operator
  can audit what the agent was reasoning about without it bloating
  the visible reply.

  Also retains the original refusal-pattern strip (rigid "DO NOT
  say X" phrases stay removed entirely, not collapsed -- those are
  failures, not thinking).

  Reads the canonical refusal pattern list from /usr/share/mios/ai/
  refusal-patterns.txt (shared with mios-agent-nudger +
  mios-delegation-prefilter). Single source of truth.
"""

from pydantic import BaseModel, Field
import re
from typing import Optional


# Lines that match any of these REGEXEN are wrapped in <think>...</think>
# instead of being passed through verbatim. Each is intentionally
# anchored to the START of a stripped line (text.strip()) so we only
# catch lines whose lead phrase is meta-narration -- prose that
# happens to contain "let me check" mid-sentence is left alone.
NARRATION_LEADERS = [
    r"^let me\b",
    r"^let.s\b",
    r"^i.ll\b",
    r"^i.m going to\b",
    r"^i.m about to\b",
    r"^i need to\b",
    r"^i.ll need to\b",
    r"^first,?\s*i\b",
    r"^next,?\s*i\b",
    r"^now,?\s*i\b",
    r"^i.ve (loaded|updated|checked|verified|noted)\b",
    r"^i.?ll try (a different|another) approach\b",
    r"^i.?ll take a (simpler|different) approach\b",
    r"^i.?ll approach this (differently|another way)\b",
    r"^based on the available tools\b",
    r"^i need to analyze\b",
    r"^let me analyze\b",
    r"^i should\b",
    r"^i will now\b",
    r"^(thinking|reasoning):\s",
]
NARRATION_RES = [re.compile(p, re.IGNORECASE) for p in NARRATION_LEADERS]


def _is_narration_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    for pat in NARRATION_RES:
        if pat.search(s):
            return True
    return False


class Filter:
    class Valves(BaseModel):
        ENABLED: bool = Field(default=True, description="Master on/off.")
        COLLAPSE_NARRATION: bool = Field(
            default=True,
            description="Wrap meta-speak lines in <think>...</think> so OWUI shows them in a collapsible block instead of the final answer body.",
        )
        STRIP_REFUSALS: bool = Field(
            default=True,
            description="Silently remove canonical refusal phrases (loaded from PATTERNS_FILE) -- these are failure modes, not reasoning.",
        )
        PATTERNS_FILE: str = Field(
            default="/usr/share/mios/ai/refusal-patterns.txt",
            description="Canonical refusal-pattern list (one regex per non-comment line). Matches are removed entirely.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._refusal_res: list[re.Pattern] = []
        self._buffer = ""  # per-instance line buffer for stream()
        self._think_open = False
        self._reload()

    def _reload(self) -> None:
        out: list[re.Pattern] = []
        try:
            for line in open(self.valves.PATTERNS_FILE, encoding="utf-8"):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                try:
                    out.append(re.compile(stripped, re.IGNORECASE))
                except re.error:
                    pass
        except OSError:
            pass
        self._refusal_res = out

    def _strip_refusals(self, text: str) -> str:
        if not (text and self.valves.STRIP_REFUSALS):
            return text
        for pat in self._refusal_res:
            text = pat.sub("", text)
        text = re.sub(r"  +", " ", text)
        text = re.sub(r"\n\n\n+", "\n\n", text)
        return text

    def _transform_lines(self, text: str) -> str:
        """Walk text line-by-line. Narration lines get wrapped in
        <think>...</think>; final-answer lines pass through. Adjacent
        narration lines collapse into a single <think> block to avoid
        UI noise."""
        if not (text and self.valves.COLLAPSE_NARRATION):
            return text
        out: list[str] = []
        narration_buf: list[str] = []

        def _flush_narration():
            if narration_buf:
                joined = "\n".join(narration_buf).rstrip()
                out.append(f"<think>{joined}</think>")
                narration_buf.clear()

        for line in text.splitlines():
            if _is_narration_line(line):
                narration_buf.append(line)
            else:
                _flush_narration()
                out.append(line)
        _flush_narration()
        # splitlines drops trailing newline; preserve it if original had one
        result = "\n".join(out)
        if text.endswith("\n") and not result.endswith("\n"):
            result += "\n"
        return result

    def _process(self, text: str) -> str:
        text = self._strip_refusals(text)
        text = self._transform_lines(text)
        return text

    async def stream(self, event: dict) -> dict:
        """Per-chunk SSE event. We can't safely classify partial lines
        mid-token, so we ONLY apply the cheap refusal-strip to chunks.
        The full line-collapse pass runs in outlet() once the response
        is complete and we have whole lines to work with."""
        if not self.valves.ENABLED:
            return event
        try:
            choices = event.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                if "content" in delta and isinstance(delta["content"], str):
                    delta["content"] = self._strip_refusals(delta["content"])
            return event
        except Exception:
            return event

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Post-stream rewrite: refusal-strip + narration-collapse the
        final assistant message so the operator sees a clean answer
        with collapsible <think> for the reasoning."""
        if not self.valves.ENABLED:
            return body
        try:
            for msg in body.get("messages") or []:
                if msg.get("role") == "assistant":
                    content = msg.get("content")
                    if isinstance(content, str):
                        msg["content"] = self._process(content)
            return body
        except Exception:
            return body
