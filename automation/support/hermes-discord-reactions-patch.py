#!/usr/bin/env python3
"""In-place patch of gateway/platforms/discord.py to add progressive
"thinking" reactions on the operator's Discord message during agent
processing.

Operator directive 2026-05-18: "also add more reactions to the
MiOS-Hermes Discord bot--Should be using more discord reactions to
show it's thinking!"

Upstream hermes-agent's Discord gateway emits exactly two reactions:
  on_processing_start    -> 👀 (single "looking" emoji)
  on_processing_complete -> ✅ / ❌

That gives the operator no visibility into what stage the agent is in
mid-run. This patch enriches the reaction surface with a progressive
sequence:
    📡 (received)          immediate
    🧠 (thinking)          after 2s if still processing
    🛠️ (using tools)       after 8s if still processing
    ⏳ (still working)      after 20s if still processing
    ✅ / ❌ (final)         on completion (and all phase reactions
                            are cleared first so the final outcome
                            stands alone)

A background asyncio.create_task() drives the progression so the
gateway's normal flow isn't blocked. The task is stashed on the
gateway instance keyed by Discord message id so concurrent
in-flight messages each get their own task that the matching
on_processing_complete can cancel.

Idempotent: rerunning is a no-op once the marker comment is present.
Safe: if Discord's add_reaction / remove_reaction fail (rate limit,
missing perm), each call already swallows the exception in the
existing _add_reaction / _remove_reaction helpers, so the progression
degrades silently.

Usage:
    hermes-discord-reactions-patch.py /path/to/discord.py
"""
from __future__ import annotations
import re
import sys
import pathlib

MARKER = "# MiOS-patch: progressive thinking reactions"

# New on_processing_start / on_processing_complete that replace the
# upstream single-emoji surface. _react_progression is the background
# task that adds emojis on a timer. _processing_tasks is a per-instance
# dict keyed by Discord message.id so concurrent runs don't stomp.
NEW_BLOCK = '''    # MiOS-patch: progressive thinking reactions
    # Replaces the upstream on_processing_start / _complete pair so the
    # operator sees a sequence of emojis on their message that reflect
    # the agent's current phase (received -> thinking -> tools -> done).
    # Operator directive 2026-05-18 "add more reactions ... to show it's
    # thinking". Background task drives the progression so the gateway's
    # main flow isn't blocked.

    _MIOS_PHASE_EMOJIS = ("📡", "🧠", "🛠️", "⏳", "👀")
    _MIOS_PHASE_TIMERS = (
        (2.0,  "🧠"),
        (8.0,  "🛠️"),
        (20.0, "⏳"),
    )

    async def _react_progression(self, message: "Any") -> None:
        """Add emojis on a timer to show the agent is still working.
        Cancelled by on_processing_complete when the run finishes."""
        import asyncio as _asyncio
        try:
            for delay, emoji in self._MIOS_PHASE_TIMERS:
                await _asyncio.sleep(delay)
                await self._add_reaction(message, emoji)
        except _asyncio.CancelledError:
            pass

    async def on_processing_start(self, event: "MessageEvent") -> None:
        """Add the initial 📡 received reaction + spawn the progression."""
        if not self._reactions_enabled():
            return
        message = event.raw_message
        if not hasattr(message, "add_reaction"):
            return
        await self._add_reaction(message, "📡")
        # Keyed per-message so concurrent in-flight runs don't stomp.
        import asyncio as _asyncio
        if not hasattr(self, "_mios_processing_tasks"):
            self._mios_processing_tasks = {}
        mid = getattr(message, "id", None)
        if mid is not None:
            t = _asyncio.create_task(self._react_progression(message))
            self._mios_processing_tasks[mid] = t

    async def on_processing_complete(self, event: "MessageEvent", outcome: "ProcessingOutcome") -> None:
        """Cancel the progression task + clear phase emojis + add final."""
        if not self._reactions_enabled():
            return
        message = event.raw_message
        # Cancel progression task if still running.
        mid = getattr(message, "id", None)
        if mid is not None and hasattr(self, "_mios_processing_tasks"):
            t = self._mios_processing_tasks.pop(mid, None)
            if t and not t.done():
                t.cancel()
        if hasattr(message, "remove_reaction"):
            for e in self._MIOS_PHASE_EMOJIS:
                await self._remove_reaction(message, e)
            if outcome == ProcessingOutcome.SUCCESS:
                await self._add_reaction(message, "✅")
            elif outcome == ProcessingOutcome.FAILURE:
                await self._add_reaction(message, "❌")

'''

# Regex that matches BOTH on_processing_start and on_processing_complete
# (as a contiguous block; the upstream defines them adjacently and we
# replace the pair atomically). The pattern grabs everything from the
# `async def on_processing_start` line through the end of the
# on_processing_complete body (terminated by the dedent that introduces
# the next `async def` or `def` at the same indent).
TARGET_RE = re.compile(
    r"    async def on_processing_start\(.*?\n"           # signature
    r"(?:        .*\n|\n)*?"                              # body
    r"    async def on_processing_complete\(.*?\n"        # signature
    r"(?:        .*\n|\n)*?"                              # body
    r"(?=    async def |    def )",                        # next method at the same indent
    re.DOTALL,
)


def main(path: str) -> int:
    p = pathlib.Path(path)
    if not p.is_file():
        sys.stderr.write(f"discord-reactions-patch: file not found: {p}\n")
        return 1
    src = p.read_text(encoding="utf-8")
    if MARKER in src:
        sys.stdout.write(f"discord-reactions-patch: already applied (marker present)\n")
        return 0
    if not TARGET_RE.search(src):
        sys.stderr.write(
            "discord-reactions-patch: target block (on_processing_start + _complete pair) "
            "not found. Upstream gateway/platforms/discord.py may have been refactored; "
            "the patch needs an updated regex.\n"
        )
        return 2
    new_src = TARGET_RE.sub(NEW_BLOCK, src, count=1)
    if new_src == src:
        sys.stderr.write("discord-reactions-patch: substitution produced no change\n")
        return 3
    p.write_text(new_src, encoding="utf-8")
    sys.stdout.write(
        f"discord-reactions-patch: applied (file grew "
        f"{len(src)} -> {len(new_src)} chars)\n"
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write(
            "usage: hermes-discord-reactions-patch.py /path/to/discord.py\n"
        )
        sys.exit(64)
    sys.exit(main(sys.argv[1]))
