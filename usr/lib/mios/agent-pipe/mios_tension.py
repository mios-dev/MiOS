# AI-hint: Tension-tracking ledger in DCI deliberation to quantify unresolved objections.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-tension-ledger.py
"""
MiOS Agent-Pipe Multi-Agent Deliberation Tension Ledger.
Tracks structured objections and guarantees all high-severity tensions are resolved before closing deliberation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

class TensionLedger:
    """Maintains objection records and resolution status during agent deliberation."""

    SEVERITY_LEVELS = {"low", "medium", "high", "critical"}

    def __init__(self) -> None:
        self._tensions: List[Dict[str, Any]] = []

    def record_objection(
        self,
        challenger_id: str,
        claim_id: str,
        severity: str,
        reason: str
    ) -> int:
        """Records an objection and returns its tension ID."""
        sev = severity.lower() if severity.lower() in self.SEVERITY_LEVELS else "medium"
        tension_id = len(self._tensions)
        self._tensions.append({
            "id": tension_id,
            "challenger_id": challenger_id,
            "claim_id": claim_id,
            "severity": sev,
            "reason": reason,
            "status": "open",  # open, resolved, waived_as_caveat
        })
        return tension_id

    def resolve_objection(self, tension_id: int, resolution_notes: str) -> bool:
        if 0 <= tension_id < len(self._tensions):
            self._tensions[tension_id]["status"] = "resolved"
            self._tensions[tension_id]["notes"] = resolution_notes
            return True
        return False

    def can_close_deliberation(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Returns True if no open critical or high-severity tensions remain."""
        unresolved = [
            t for t in self._tensions
            if t["status"] == "open" and t["severity"] in {"high", "critical"}
        ]
        return len(unresolved) == 0, unresolved
