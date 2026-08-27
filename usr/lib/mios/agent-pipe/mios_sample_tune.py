# AI-hint: Dynamic sampling hyperparameter scheduler based on task entropy estimation.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-sample-tune.py
"""
MiOS Agent-Pipe Dynamic Sampling Hyperparameter Scheduler.
Adjusts temperature, top_p, and min_p dynamically based on prompt intent classification.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

class SamplingScheduler:
    """Classifies task intent and yields optimal decoding hyperparameters."""

    DETERMINISTIC_PATTERNS = [
        r"\b(code|python|rust|bash|json|sql|function|def|struct|class|bug|syntax|test)\b",
        r"\b(calculate|math|regex|fhs|path|sha256|md5|crc32|diff)\b",
    ]

    CREATIVE_PATTERNS = [
        r"\b(story|poem|brainstorm|essay|creative|explore|roleplay|scenario)\b",
    ]

    def estimate_hyperparameters(self, prompt: str) -> Dict[str, float]:
        """Returns dict containing temperature, top_p, and frequency_penalty."""
        text = (prompt or "").lower()

        # Check deterministic patterns first
        for pat in self.DETERMINISTIC_PATTERNS:
            if re.search(pat, text):
                return {
                    "temperature": 0.0,
                    "top_p": 0.1,
                    "min_p": 0.05,
                    "mode": "deterministic",
                }

        # Check creative patterns
        for pat in self.CREATIVE_PATTERNS:
            if re.search(pat, text):
                return {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "min_p": 0.0,
                    "mode": "creative",
                }

        # Balanced general default
        return {
            "temperature": 0.2,
            "top_p": 0.8,
            "min_p": 0.05,
            "mode": "balanced",
        }
