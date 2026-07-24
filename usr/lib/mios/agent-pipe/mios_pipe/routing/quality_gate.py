# AI-hint: Pure deterministic quality gate producer for smartroute escalation decisions.
# AI-related: mios_pipe/routing/smartroute.py, mios_pipe/routing/native_loop.py, mios_pipe/routing/lanes_resolver.py, test_mios_quality_gate.py
"""Pure deterministic quality gate for local lane output evaluation."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

try:
    from mios_pipe.routing.native_loop import _is_punt
except Exception:  # noqa: BLE001
    import re
    def _is_punt(_out: str) -> bool:
        t = (_out or "").strip().lower()
        if not t:
            return True
        _markers = (
            "no specific", "no information", "no data", "not available",
            "provided context", "cannot provide", "i cannot", "unable to",
            "no relevant", "i do not have enough", "don't have enough",
            "would you like me to", "rephrase the search", "search again",
            "no direct information", "not present in the current context",
            "don't have access", "do not have access",
        )
        if not any(m in t for m in _markers):
            return False
        _facty = bool(re.search(r"\[\d+\]|\b20\d\d\b|\b\d{3,}\b", t)) or len(t) > 600
        return not _facty

log = logging.getLogger("mios-agent-pipe")

# Default quality thresholds (overridden by [agent_pipe.quality] SSOT)
_DEFAULT_MIN_LENGTH = 5
_DEFAULT_CHECK_EMPTY = True
_DEFAULT_CHECK_PUNT = True
_DEFAULT_CHECK_JSON = True


def _load_quality_config() -> Dict[str, Any]:
    """Load [agent_pipe.quality] settings from mios_toml resolver if available."""
    try:
        import mios_toml
        sec = mios_toml.get("agent_pipe.quality", {})
        if isinstance(sec, dict):
            return sec
    except Exception:
        pass
    return {}


def evaluate_quality(output: str, config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """Evaluate output quality against deterministic rules.

    Returns:
        (quality_ok: bool, reason: str)
        If quality_ok is False, smartroute.should_escalate() will trigger escalation.
        Degrades open (returns True, "degrade_open") on unexpected exceptions.
    """
    try:
        cfg = config if config is not None else _load_quality_config()
        min_length = int(cfg.get("min_length", _DEFAULT_MIN_LENGTH))
        check_empty = bool(cfg.get("check_empty", _DEFAULT_CHECK_EMPTY))
        check_punt = bool(cfg.get("check_punt", _DEFAULT_CHECK_PUNT))
        check_json = bool(cfg.get("check_json", _DEFAULT_CHECK_JSON))

        text = output or ""
        stripped = text.strip()

        # 1. Empty / whitespace check
        if check_empty and not stripped:
            return False, "empty_output"

        # 2. Min length floor
        if len(stripped) < min_length:
            return False, "below_min_length"

        # 3. Refusal / punt check
        if check_punt and _is_punt(stripped):
            return False, "refusal_or_punt"

        # 4. JSON structure validation (if text looks like JSON block)
        if check_json and (stripped.startswith("{") or stripped.startswith("[")):
            try:
                json.loads(stripped)
            except ValueError:
                try:
                    from mios_pipe.utils.jsonsalvage import salvage_json
                    salvaged = salvage_json(stripped)
                    if salvaged is None:
                        return False, "malformed_json"
                except Exception:
                    return False, "malformed_json"

        return True, "quality_ok"
    except Exception as e:
        log.warning("quality_gate evaluation failed open: %s", e)
        return True, "degrade_open"
