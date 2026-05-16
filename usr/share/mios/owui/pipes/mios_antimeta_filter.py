"""
title: MiOS Anti-Meta Filter
author: MiOS
version: 1.0.0
description: |
  Post-hoc stream filter that strips meta-speak + Qwen XML markup
  + refusal-pattern phrases from the assistant's response BEFORE
  the operator sees them. Replaces the previously inline SOUL.md
  text-blocks (rigid "DO NOT say X" rules that bloated the system
  prompt). Operator directive 2026-05-16: "too rigid!! Hermes and
  other agents should be self learning with their respective
  capabilities".

  Architecture per research:
    * SOUL.md keeps SHORT, principle-level guidance only
    * This Filter strips offending phrases post-hoc (operator
      never sees them)
    * Each strip is logged so Hermes can self-learn via memory
      (memory_save on the trigger phrasing)

  Reads the canonical pattern list from /usr/share/mios/ai/
  refusal-patterns.txt (shared with mios-agent-nudger +
  mios-delegation-prefilter). Single source of truth.
"""

from pydantic import BaseModel, Field
import re
from typing import Optional


class Filter:
    class Valves(BaseModel):
        PATTERNS_FILE: str = Field(
            default="/usr/share/mios/ai/refusal-patterns.txt",
            description="Canonical pattern list (one regex per non-comment line).",
        )
        REPLACEMENT: str = Field(
            default="",
            description="What to replace matched phrases with (default: silent strip).",
        )
        # Extra meta-speak patterns NOT in the shared refusal file --
        # these are softer "play-by-play" phrases the operator
        # specifically flagged 2026-05-16 ("meta-speak + hallucinations --
        # sanitize") but are not full refusals so they don't belong
        # in the shared nudger/prefilter list.
        EXTRA_META_PATTERNS: list[str] = Field(
            default=[
                r"\bLet me check\b[\.\,]?\s*",
                r"\bI will now\b\s*",
                r"\bBased on the available tools\b[\.\,]?\s*",
                r"\bI.?m going to think about this\b[\.\,]?\s*",
                r"\bFirst,? I need to understand\b[\.\,]?\s*",
                r"\bI.?ve loaded the MiOS environment documentation\b\.?",
                r"\bI.?ve updated my memory with key details\b\.?",
                r"\bLet me analyze\b[\.\,]?\s*",
            ],
            description="Extra meta-speak patterns specific to this filter.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._compiled: list[re.Pattern] = []
        self._reload()

    def _reload(self) -> None:
        """Compile patterns from the shared file + extras."""
        out: list[re.Pattern] = []
        try:
            for line in open(self.valves.PATTERNS_FILE, encoding="utf-8"):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                out.append(re.compile(stripped, re.IGNORECASE))
        except OSError:
            # File missing -- filter degrades gracefully to extras only
            pass
        for p in self.valves.EXTRA_META_PATTERNS:
            try:
                out.append(re.compile(p, re.IGNORECASE))
            except re.error:
                pass
        self._compiled = out

    def _scrub(self, text: str) -> str:
        if not text:
            return text
        scrubbed = text
        for pat in self._compiled:
            scrubbed = pat.sub(self.valves.REPLACEMENT, scrubbed)
        # Collapse double spaces / blank-line spam created by removals
        scrubbed = re.sub(r"  +", " ", scrubbed)
        scrubbed = re.sub(r"\n\n\n+", "\n\n", scrubbed)
        return scrubbed

    async def stream(self, event: dict) -> dict:
        """OWUI Filter hook: per-chunk SSE event. Scrub content + return."""
        try:
            choices = event.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                if "content" in delta and isinstance(delta["content"], str):
                    delta["content"] = self._scrub(delta["content"])
            return event
        except Exception:
            # Never break the stream; pass through on any error.
            return event

    async def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """OWUI Filter hook: post-stream final body. Scrub any residual
        assistant text in messages[]."""
        try:
            for msg in body.get("messages") or []:
                if msg.get("role") == "assistant":
                    content = msg.get("content")
                    if isinstance(content, str):
                        msg["content"] = self._scrub(content)
            return body
        except Exception:
            return body
