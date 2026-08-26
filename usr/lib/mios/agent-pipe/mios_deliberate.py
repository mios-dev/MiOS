#!/usr/bin/env python3
# AI-hint: Bounded reflection loops with convergence criteria to prevent circular reasoning.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_reflect.py
"""
Bounded Reflection Loop Convergence (T-385 / AGY-1983)

Implements bounded deliberation and reflection loops with semantic delta scoring,
enforcing deterministic termination when refinement reaches diminishing returns (delta < 0.05)
or encounters the maximum iteration ceiling (default: 3) to prevent token waste and circular debate.
"""

from __future__ import annotations

import dataclasses
import logging
import math
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("mios.deliberate")


@dataclasses.dataclass
class DeliberationConfig:
    max_iterations: int = 3
    convergence_threshold: float = 0.05  # 5% semantic delta threshold
    min_iterations: int = 1
    critique_model: str = "mios-light"

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class DeliberationTurn:
    iteration: int
    draft: str
    critique: str
    revised: str
    semantic_delta: float
    tokens_used: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class DeliberationState:
    initial_prompt: str
    current_draft: str
    turns: List[DeliberationTurn] = dataclasses.field(default_factory=list)
    final_output: str = ""
    exit_reason: str = ""
    is_converged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_prompt": self.initial_prompt,
            "current_draft": self.current_draft,
            "turns": [t.to_dict() for t in self.turns],
            "final_output": self.final_output,
            "exit_reason": self.exit_reason,
            "is_converged": self.is_converged,
            "total_iterations": len(self.turns),
        }


class SemanticDeltaCalculator:
    """
    Computes multi-dimensional semantic difference between two text revisions
    using token Jaccard distance, n-gram overlap, and structural length variation.
    """

    WORD_RE = re.compile(r"\b[a-zA-Z0-9_-]+\b")

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        return [w.lower() for w in cls.WORD_RE.findall(text)]

    @classmethod
    def get_ngrams(cls, tokens: List[str], n: int = 2) -> Set[Tuple[str, ...]]:
        if len(tokens) < n:
            return set()
        return set(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))

    @classmethod
    def calculate_delta(cls, prev_text: str, curr_text: str) -> float:
        if prev_text.strip() == curr_text.strip():
            return 0.0

        prev_tokens = cls.tokenize(prev_text)
        curr_tokens = cls.tokenize(curr_text)

        if not prev_tokens and not curr_tokens:
            return 0.0
        if not prev_tokens or not curr_tokens:
            return 1.0

        prev_set = set(prev_tokens)
        curr_set = set(curr_tokens)

        # 1. Jaccard Token Distance
        intersection = len(prev_set.intersection(curr_set))
        union = len(prev_set.union(curr_set))
        jaccard_sim = intersection / union if union > 0 else 1.0
        jaccard_delta = 1.0 - jaccard_sim

        # 2. Bigram Overlap Distance
        prev_bigrams = cls.get_ngrams(prev_tokens, n=2)
        curr_bigrams = cls.get_ngrams(curr_tokens, n=2)
        if prev_bigrams or curr_bigrams:
            bi_union = len(prev_bigrams.union(curr_bigrams))
            bi_inter = len(prev_bigrams.intersection(curr_bigrams))
            bi_sim = bi_inter / bi_union if bi_union > 0 else 1.0
            bigram_delta = 1.0 - bi_sim
        else:
            bigram_delta = jaccard_delta

        # 3. Length Ratio Delta
        len_prev = len(prev_tokens)
        len_curr = len(curr_tokens)
        max_len = max(len_prev, len_curr)
        len_delta = abs(len_prev - len_curr) / max_len if max_len > 0 else 0.0

        # Weighted combination
        combined_delta = (jaccard_delta * 0.40) + (bigram_delta * 0.45) + (len_delta * 0.15)
        return min(max(round(combined_delta, 4), 0.0), 1.0)


class BoundedDeliberationEngine:
    """
    Coordinates multi-turn bounded deliberation with convergence gating.
    """

    def __init__(
        self,
        config: Optional[DeliberationConfig] = None,
        calculator: Optional[SemanticDeltaCalculator] = None,
    ) -> None:
        self.config = config or DeliberationConfig()
        self.calculator = calculator or SemanticDeltaCalculator()

    def step(
        self,
        state: DeliberationState,
        critique: str,
        revision: str,
        config: Optional[DeliberationConfig] = None,
        tokens_used: int = 0,
        duration_ms: float = 0.0,
    ) -> bool:
        """
        Executes a single deliberation step, updates state, and evaluates convergence.
        Returns True if deliberation is converged and complete.
        """
        cfg = config or self.config
        iteration_idx = len(state.turns) + 1

        delta = self.calculator.calculate_delta(state.current_draft, revision)

        turn = DeliberationTurn(
            iteration=iteration_idx,
            draft=state.current_draft,
            critique=critique,
            revised=revision,
            semantic_delta=delta,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
        )
        state.turns.append(turn)

        # Check critique pass criteria
        critique_lower = critique.lower()
        if (
            "approved" in critique_lower
            or "no further changes" in critique_lower
            or "satisfies all requirements" in critique_lower
            or "no improvements needed" in critique_lower
        ) and iteration_idx >= cfg.min_iterations:
            state.final_output = revision if revision.strip() else state.current_draft
            state.exit_reason = "converged_critique_passed"
            state.is_converged = True
            return True

        # Check diminishing-returns criteria
        if delta < cfg.convergence_threshold and iteration_idx >= cfg.min_iterations:
            state.final_output = revision if revision.strip() else state.current_draft
            state.exit_reason = "converged_diminishing_returns"
            state.is_converged = True
            return True

        # Check max iterations ceiling
        if iteration_idx >= cfg.max_iterations:
            state.final_output = revision if revision.strip() else state.current_draft
            state.exit_reason = "max_iterations"
            state.is_converged = True
            return True

        # Update draft for next turn
        state.current_draft = revision
        return False

    def run_deliberation(
        self,
        initial_prompt: str,
        initial_draft: str,
        critique_fn: Callable[[str, str], str],
        revision_fn: Callable[[str, str, str], str],
        config: Optional[DeliberationConfig] = None,
    ) -> DeliberationState:
        """
        Executes complete bounded deliberation loop using provided callbacks.
        """
        cfg = config or self.config
        state = DeliberationState(
            initial_prompt=initial_prompt,
            current_draft=initial_draft,
        )

        for iteration in range(1, cfg.max_iterations + 1):
            t0 = time.perf_counter()
            critique = critique_fn(state.initial_prompt, state.current_draft)
            revision = revision_fn(state.initial_prompt, state.current_draft, critique)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            converged = self.step(
                state,
                critique=critique,
                revision=revision,
                config=cfg,
                duration_ms=elapsed_ms,
            )
            if converged:
                break

        if not state.is_converged:
            state.final_output = state.current_draft
            state.exit_reason = "max_iterations"
            state.is_converged = True

        return state


# Module-level convenience functions
_DEFAULT_ENGINE = BoundedDeliberationEngine()


def calculate_semantic_delta(prev_text: str, curr_text: str) -> float:
    return _DEFAULT_ENGINE.calculator.calculate_delta(prev_text, curr_text)


def run_bounded_deliberation(
    initial_prompt: str,
    initial_draft: str,
    critique_fn: Callable[[str, str], str],
    revision_fn: Callable[[str, str, str], str],
    max_iterations: int = 3,
    convergence_threshold: float = 0.05,
) -> DeliberationState:
    config = DeliberationConfig(
        max_iterations=max_iterations,
        convergence_threshold=convergence_threshold,
    )
    return _DEFAULT_ENGINE.run_deliberation(
        initial_prompt=initial_prompt,
        initial_draft=initial_draft,
        critique_fn=critique_fn,
        revision_fn=revision_fn,
        config=config,
    )
