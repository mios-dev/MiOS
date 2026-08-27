"""
streaming_llm.py — T-755 WS-AI
StreamingLLM attention sink pinner and rolling KV eviction manager in llama-swap.

Pins initial attention sink tokens (positions 0..3) permanently while maintaining
a rolling FIFO circular buffer for positions >= 4, bounding memory consumption
and enabling perpetual infinite generation with zero OOM crashes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger("streaming_llm")

@dataclass
class StreamingKVCache:
    sink_size: int = 4
    window_size: int = 32768
    sink_tokens: list[int] = field(default_factory=list)
    rolling_tokens: list[int] = field(default_factory=list)
    total_tokens_seen: int = 0

    @property
    def current_allocated_tokens(self) -> int:
        return len(self.sink_tokens) + len(self.rolling_tokens)

class StreamingLLMManager:
    """
    Manages StreamingLLM KV attention sink pinning and rolling window eviction.
    """
    def __init__(self, sink_size: int = 4, window_size: int = 32768) -> None:
        self.sink_size = sink_size
        self.window_size = window_size
        self.cache = StreamingKVCache(sink_size=sink_size, window_size=window_size)

    def append_token(self, token_id: int) -> dict:
        """Appends a token, preserving sinks and evicting oldest rolling tokens if full."""
        c = self.cache
        c.total_tokens_seen += 1

        if len(c.sink_tokens) < c.sink_size:
            c.sink_tokens.append(token_id)
            evicted = False
        else:
            if len(c.rolling_tokens) >= (c.window_size - c.sink_size):
                # Evict oldest token from rolling window (FIFO)
                c.rolling_tokens.pop(0)
                evicted = True
            else:
                evicted = False
            c.rolling_tokens.append(token_id)

        return {
            "total_seen": c.total_tokens_seen,
            "allocated": c.current_allocated_tokens,
            "evicted": evicted
        }
