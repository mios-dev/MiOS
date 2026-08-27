"""
mios_deliberate.py — T-341 MAO-02
Deliberative Collective Intelligence (DCI) — 4-archetype deliberation council
with typed interaction grammar and Decision Packet output.

Archetypes: Framer | Explorer | Challenger | Integrator
Grammar acts: propose | challenge | evidence | reframe | synthesize | concede

Decision Packet schema:
  {
    "chosen_actions": [...],
    "residual_objections": [...],
    "reopen_conditions": [...],
    "round_count": N,
    "consensus_score": 0.0..1.0
  }
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)

class Act(str, Enum):
    PROPOSE   = "propose"
    CHALLENGE = "challenge"
    EVIDENCE  = "evidence"
    REFRAME   = "reframe"
    SYNTHESIZE = "synthesize"
    CONCEDE   = "concede"

class Archetype(str, Enum):
    FRAMER     = "Framer"
    EXPLORER   = "Explorer"
    CHALLENGER = "Challenger"
    INTEGRATOR = "Integrator"

@dataclass
class Move:
    """Single deliberation move from an archetype agent."""
    archetype: Archetype
    act:       Act
    content:   str
    timestamp: float = field(default_factory=time.monotonic)

@dataclass
class DecisionPacket:
    """Final output of a DCI deliberation session."""
    session_id:          str
    chosen_actions:      list[str]
    residual_objections: list[str]
    reopen_conditions:   list[str]
    round_count:         int
    consensus_score:     float   # 0.0 .. 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":          self.session_id,
            "chosen_actions":      self.chosen_actions,
            "residual_objections": self.residual_objections,
            "reopen_conditions":   self.reopen_conditions,
            "round_count":         self.round_count,
            "consensus_score":     self.consensus_score,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class DCISession:
    """
    Orchestrates a single DCI deliberation session.

    In production each archetype is backed by an LLM call; in unit-test mode
    the caller provides a `responder` callable that returns (act, content)
    tuples per archetype so tests run without a live inference engine.
    """
    MAX_ROUNDS = 8

    def __init__(self, topic: str,
                 responder=None,
                 session_id: str | None = None) -> None:
        self.topic      = topic
        self.session_id = session_id or str(uuid.uuid4())
        self._responder = responder or _default_responder
        self.moves:     list[Move] = []
        self.concessions: set[Archetype] = set()

    # ------------------------------------------------------------------
    def run(self) -> DecisionPacket:
        """Execute up to MAX_ROUNDS of deliberation and return a Decision Packet."""
        sequence = [
            Archetype.FRAMER,
            Archetype.EXPLORER,
            Archetype.CHALLENGER,
            Archetype.INTEGRATOR,
        ]
        for round_i in range(self.MAX_ROUNDS):
            for archetype in sequence:
                act, content = self._responder(
                    archetype, self.moves, self.topic)
                move = Move(archetype=archetype, act=Act(act), content=content)
                self.moves.append(move)
                log.debug("DCI round=%d %s:%s", round_i, archetype, act)
                if Act(act) == Act.CONCEDE:
                    self.concessions.add(archetype)

            if self._has_consensus():
                log.info("DCI: consensus reached at round %d", round_i + 1)
                break

        return self._build_packet(round_count=round_i + 1)

    # ------------------------------------------------------------------
    def _has_consensus(self) -> bool:
        """
        Consensus = Integrator issued SYNTHESIZE and fewer than 2 archetypes
        have outstanding CHALLENGE moves without a subsequent CONCEDE.
        """
        challenger_conceded = Archetype.CHALLENGER in self.concessions
        integrator_synthesized = any(
            m.archetype == Archetype.INTEGRATOR and m.act == Act.SYNTHESIZE
            for m in self.moves)
        return integrator_synthesized and challenger_conceded

    def _build_packet(self, round_count: int) -> DecisionPacket:
        proposals   = [m.content for m in self.moves if m.act == Act.PROPOSE]
        synthesized = [m.content for m in self.moves if m.act == Act.SYNTHESIZE]
        challenges  = [m.content for m in self.moves
                       if m.act == Act.CHALLENGE
                       and m.archetype not in self.concessions]
        concede_count = len(self.concessions)
        consensus_score = min(1.0, concede_count / max(1, len([
            Archetype.FRAMER, Archetype.EXPLORER,
            Archetype.CHALLENGER, Archetype.INTEGRATOR]) - 1))

        return DecisionPacket(
            session_id=self.session_id,
            chosen_actions=synthesized or proposals[:1],
            residual_objections=challenges,
            reopen_conditions=["Reopen if critical safety objection raised."],
            round_count=round_count,
            consensus_score=consensus_score,
        )

def _default_responder(archetype: Archetype,
                       history: list[Move],
                       topic: str) -> tuple[str, str]:
    """
    Default responder used in tests — returns deterministic scripted moves.
    Production replaces this with LLM calls.
    """
    script: dict[Archetype, list[tuple[str, str]]] = {
        Archetype.FRAMER:     [("propose",    f"Frame: {topic}")],
        Archetype.EXPLORER:   [("evidence",   "Evidence: supporting data")],
        Archetype.CHALLENGER: [("challenge",  "Challenge: risk concern"),
                               ("concede",    "Conceded after evidence")],
        Archetype.INTEGRATOR: [("reframe",    "Reframe: synthesizing"),
                               ("synthesize", f"Decision: proceed with {topic}")],
    }
    moves_by_arch = sum(1 for m in history if m.archetype == archetype)
    choices = script.get(archetype, [("propose", "default proposal")])
    act, content = choices[min(moves_by_arch, len(choices) - 1)]
    return act, content
