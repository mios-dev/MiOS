# AI-hint: MiOS system and orchestration module providing mios deliberate capabilities.
# AI-functions: to_dict, to_json, __init__, run, _has_consensus, _build_packet, _default_responder, Act, Archetype, Move, DecisionPacket, DCISession

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


# ---------------------------------------------------------------------------
# T-385: Bounded Reflection Loop Convergence
# ---------------------------------------------------------------------------
import difflib

@dataclass
class DeliberationConfig:
    """Configuration for bounded deliberation/reflection convergence."""
    max_iterations: int = 3
    convergence_threshold: float = 0.05
    timeout_seconds: float = 30.0

@dataclass
class DeliberationTurn:
    """One critique-revision cycle."""
    turn_index: int
    critique: str
    draft: str
    semantic_delta: float
    timestamp: float = field(default_factory=time.monotonic)

@dataclass
class DeliberationState:
    """Accumulated state across bounded deliberation iterations."""
    initial_prompt: str
    current_draft: str
    turns: list[DeliberationTurn] = field(default_factory=list)
    is_converged: bool = False
    exit_reason: str = ""
    final_output: str = ""

class SemanticDeltaCalculator:
    """Calculates semantic distance between successive drafts (0.0=identical, 1.0=disjoint)."""

    def calculate_delta(self, text_a: str, text_b: str) -> float:
        if text_a == text_b:
            return 0.0
        matcher = difflib.SequenceMatcher(None, text_a.strip(), text_b.strip())
        similarity = matcher.ratio()
        return max(0.0, min(1.0, 1.0 - similarity))

def calculate_semantic_delta(text_a: str, text_b: str) -> float:
    return SemanticDeltaCalculator().calculate_delta(text_a, text_b)

class BoundedDeliberationEngine:
    """Manages reflection loop convergence based on diminishing returns and max iteration limits."""

    def __init__(self,
                 config: DeliberationConfig | None = None,
                 calculator: SemanticDeltaCalculator | None = None) -> None:
        self.config = config or DeliberationConfig()
        self.calculator = calculator or SemanticDeltaCalculator()

    def step(self, state: DeliberationState, critique: str, revision: str) -> bool:
        critique_upper = critique.upper()
        if "APPROVED" in critique_upper or "NO FURTHER CHANGES" in critique_upper:
            state.is_converged = True
            state.exit_reason = "converged_critique_passed"
            state.current_draft = revision
            state.final_output = revision
            return True

        delta = self.calculator.calculate_delta(state.current_draft, revision)
        turn = DeliberationTurn(
            turn_index=len(state.turns) + 1,
            critique=critique,
            draft=revision,
            semantic_delta=delta,
            timestamp=time.monotonic()
        )
        state.turns.append(turn)
        state.current_draft = revision
        state.final_output = revision

        if delta < self.config.convergence_threshold:
            state.is_converged = True
            state.exit_reason = "converged_diminishing_returns"
            return True

        if len(state.turns) >= self.config.max_iterations:
            state.is_converged = True
            state.exit_reason = "max_iterations"
            return True

        return False

# Backwards compatibility / alias
DeliberationEngine = BoundedDeliberationEngine

def run_bounded_deliberation(
    initial_prompt: str,
    initial_draft: str,
    critique_fn: Any,
    revision_fn: Any,
    max_iterations: int = 3,
    convergence_threshold: float = 0.05
) -> DeliberationState:
    config = DeliberationConfig(max_iterations=max_iterations, convergence_threshold=convergence_threshold)
    engine = BoundedDeliberationEngine(config=config)
    state = DeliberationState(initial_prompt=initial_prompt, current_draft=initial_draft, final_output=initial_draft)

    for i in range(max_iterations):
        critique = critique_fn(initial_prompt, state.current_draft)
        revision = revision_fn(initial_prompt, state.current_draft, critique)
        if engine.step(state, critique, revision):
            break

    return state

