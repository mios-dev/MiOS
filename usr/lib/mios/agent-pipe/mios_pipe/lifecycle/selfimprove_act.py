# AI-hint: Pure self-improvement ACT-half decision core (T-062 ACT + T-064 proof-of-utility). The OBSERVE half (mios_selfimprove.analyze) surfaces WHAT to improve; this turns a finding into a bounded, VALIDATED change PROPOSAL and decides whether it may be QUEUED -- it never applies anything. Three composed, stdlib+mios_bench-only decisions: (1) STRUCTURAL anti-reward-hacking isolation (proposal_target_allowed/validate_proposal) -- a proposal may ONLY target a kind in the SSOT improvable surface and NEVER one in the SSOT protected surface (the evaluator/eval-data/lane-config); deny wins, so a proposal that tries to edit the thing that judges it is rejected BEFORE it is ever scored (the Autodata reward-hacking lesson); (2) the Autodata solver-GAP discriminative signal (solver_gap/is_discriminative/curate_eval) -- a held-out eval task carries signal only when a strong solver beats a weak one by >= the SSOT gap, so trivial/impossible tasks are dropped; (3) proof-of-utility (pass_hat_k_score over mios_bench + proof_of_utility) -- accept a proposal ONLY IF its pass^k does not regress the baseline beyond the SSOT margin (and, where required, strictly improves). decide_proposal composes all three into ONE verdict. Pure functions over plain dicts/numbers: no DB, no server import, no model call, no I/O -> unit-testable (test_mios_selfimprove_act.py). The orchestration that drafts proposals (a model call), runs the solver lanes, and writes the QUEUE lives in mios_daemons (the loop), default-off; this module only DECIDES. Every threshold/flag/surface is a parameter supplied by the caller from the [selfimprove] SSOT -- nothing numeric or lexical is baked here.
# AI-related: ./mios_selfimprove.py, ./mios_bench.py, ./mios_daemons.py, ./test_mios_selfimprove_act.py, /usr/share/mios/mios.toml
# AI-functions: proposal_target_allowed, validate_proposal, solver_gap, is_discriminative, curate_eval, pass_hat_k_score, proof_of_utility, decide_proposal
"""mios_selfimprove_act -- pure ACT-half decision core for the self-curation loop.

The risky part of self-improvement is an agent MODIFYING itself; the safe,
high-value part is honestly DECIDING whether a candidate change is worth a
human's review. ``mios_selfimprove.analyze`` is the OBSERVE half (what is going
wrong); this is the ACT half's brain: given a candidate change PROPOSAL plus the
scores of the current baseline vs the proposed variant on a held-out eval, it
returns a single accept/reject verdict.

It is deliberately split into three composable decisions, each grounded in the
Autodata "agentic data scientist" loop (arXiv:2606.25996):

1. **Structural isolation (anti-reward-hacking).** Autodata observed its
   self-rewriting agent editing the *weak solver's* prompt to fake a result --
   i.e. tampering with the thing that judged it. The structural defence is to
   make the evaluator / eval-data / lane-config UN-TOUCHABLE by a proposal: a
   proposal may only target a kind in the SSOT *improvable* surface and never one
   in the SSOT *protected* surface, with deny winning. This is enforced BEFORE
   any score is read, so a proposal aimed at the evaluator is rejected outright.

2. **Solver-gap curation.** A training/eval task carries signal only if a strong
   solver beats a weak one on it; a task both lanes pass (trivial) or both fail
   (impossible) is discarded. The light lane is the natural weak solver and the
   heavy/council lane the strong solver -- but this module only consumes the two
   numeric scores, never a model id.

3. **Proof-of-utility.** A proposal is accepted only if it does not regress the
   baseline beyond an SSOT margin (and, when required, strictly improves) -- the
   ``pass^k`` reliability metric from :mod:`mios_bench`. Autodata accepted only
   126/233 of its own proposals; rejecting the non-improving majority is the
   load-bearing mechanism, not optional caution.

Pure functions over plain dicts/numbers: no DB, no server import, no model call,
no I/O. Every threshold, flag, and surface set is supplied by the caller from the
``[selfimprove]`` SSOT section -- this module bakes in no numeric weight, no lane
id, and no English/keyword gate (target membership is structural set membership,
the gap is a numeric verifier signal).
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import mios_bench


# ── 1. Structural anti-reward-hacking isolation ────────────────────────────────
def proposal_target_allowed(target_kind: str, *, improvable, protected) -> bool:
    """True iff a proposal targeting ``target_kind`` is in the improvable surface
    and NOT in the protected surface. DENY WINS: a kind in ``protected`` is refused
    even if it also appears in ``improvable`` (fail-safe, like the HITL resolver
    erring toward blocking) so the evaluator / eval-data / lane-config can never be
    edited by a proposal. Both surfaces come from the caller (SSOT) -- an empty
    improvable surface allows nothing (degrade-closed)."""
    kind = str(target_kind or "").strip()
    if not kind:
        return False
    prot = {str(p).strip() for p in (protected or ())}
    impr = {str(p).strip() for p in (improvable or ())}
    if kind in prot:
        return False
    return kind in impr


def validate_proposal(proposal: dict, *, improvable, protected) -> "Tuple[bool, str]":
    """Validate a proposal's SHAPE + its target isolation. Returns ``(ok, reason)``.

    A proposal is ``{target_kind, target_id, change, rationale}`` (change/rationale
    are the human-reviewable description -- a diff/tweak + why). Rejected when it is
    not a dict, lacks an identified target, or its ``target_kind`` is not in the
    improvable surface / is in the protected surface (the structural isolation).
    The reason is a stable machine token (not prose) so callers can log/branch on it
    without a keyword match."""
    if not isinstance(proposal, dict):
        return False, "not_a_proposal"
    kind = str(proposal.get("target_kind") or "").strip()
    tid = str(proposal.get("target_id") or "").strip()
    if not kind:
        return False, "missing_target_kind"
    if not tid:
        return False, "missing_target_id"
    if not proposal_target_allowed(kind, improvable=improvable, protected=protected):
        # Structurally off-limits: either outside the improvable surface or inside
        # the protected (evaluator/eval/lane-config) surface. Same token either way
        # -- the proposal simply may not touch this surface.
        return False, "target_protected_or_unimprovable"
    return True, "ok"


# ── 2. Autodata solver-gap discriminative signal ───────────────────────────────
def solver_gap(weak_score: float, strong_score: float) -> float:
    """The discriminative signal: ``strong - weak``. A purely numeric verifier
    output (good per NO-HARDCODE -- not an English/keyword gate). Both args are
    pass-rates in [0,1]; the sign is preserved (a negative gap = the weak lane beat
    the strong one, which carries no curation signal)."""
    return float(strong_score) - float(weak_score)


def is_discriminative(weak_score: float, strong_score: float, *, gap_min: float) -> bool:
    """True iff a task SEPARATES a weak from a strong solver by at least ``gap_min``
    (Autodata's sweet spot). Tasks both lanes pass (trivial) or both fail
    (impossible) have a gap below the threshold and carry no eval/training signal."""
    return solver_gap(weak_score, strong_score) >= float(gap_min)


def curate_eval(candidates: "Iterable[dict]", *, gap_min: float) -> "list[dict]":
    """Keep only the DISCRIMINATIVE held-out eval candidates (Autodata curation).

    Each candidate carries the two lane scores under ``weak`` and ``strong`` (the
    light vs heavy/council pass-rates on that task). A candidate with no numeric
    pair is dropped (it cannot be judged). The kept set is the held-out eval the
    proof-of-utility scores baseline-vs-proposed on -- so a non-discriminative task
    can never inflate or mask a regression."""
    kept: list[dict] = []
    for c in candidates or []:
        if not isinstance(c, dict):
            continue
        w, s = c.get("weak"), c.get("strong")
        if not isinstance(w, (int, float)) or not isinstance(s, (int, float)):
            continue
        if is_discriminative(w, s, gap_min=gap_min):
            kept.append(c)
    return kept


# ── 3. Proof-of-utility (pass^k non-regression) ────────────────────────────────
def pass_hat_k_score(tasks: "Sequence[Tuple[int, int]]", *, k: int) -> float:
    """The pass^k reliability score over a held-out eval, via :mod:`mios_bench`.
    ``tasks`` = ``[(n_trials, c_correct), ...]`` per task. pass^k ("ALL k repeats
    succeed", tau-bench) is the worst-case reliability number production needs --
    the same metric the skill-promotion gate (T-049) uses, here applied to score a
    variant rather than to promote a skill. Thin wrapper so the ACT module names its
    scoring in its own domain; the math lives in mios_bench (single source)."""
    return mios_bench.aggregate_pass_hat_k(tasks, int(k))


def proof_of_utility(baseline_score: float, proposed_score: float, *,
                     margin: float = 0.0,
                     require_improvement: bool = False) -> "Tuple[bool, float]":
    """T-064 accept criterion. Returns ``(accept, delta)`` where
    ``delta = proposed - baseline``.

    ACCEPT iff the proposed variant does not regress the baseline beyond ``margin``
    (``delta >= -margin``; ``margin = 0`` => strict non-regression ``proposed >=
    baseline``). When ``require_improvement`` is set, a strict improvement is also
    required (``delta > 0``) -- used where a discriminative eval applies and a
    no-op change should not be queued. Both ``margin`` and ``require_improvement``
    are SSOT-supplied; nothing is baked here."""
    delta = float(proposed_score) - float(baseline_score)
    accept = delta >= -abs(float(margin))
    if require_improvement:
        accept = accept and (delta > 0.0)
    return accept, delta


def decide_proposal(proposal: dict, *, baseline_score: float, proposed_score: float,
                    improvable, protected, margin: float = 0.0,
                    require_improvement: bool = False) -> dict:
    """THE single ACT verdict, composing isolation + proof-of-utility.

    Order is load-bearing: STRUCTURAL ISOLATION is checked FIRST, so a proposal
    that targets the evaluator / eval-data / lane-config (or anything outside the
    improvable surface) is rejected BEFORE its scores are even consulted -- a
    reward-hacking proposal can never "earn" its way in. Only an isolation-valid
    proposal is then put to the proof-of-utility (pass^k non-regression) gate.

    Returns a verdict dict::

        {accept: bool, reason: <token>, delta: float|None,
         target_kind, target_id}

    ``reason`` is a stable machine token (``isolation_rejected`` / ``regression`` /
    ``accepted``), never prose. ``delta`` is None when the proposal was rejected on
    isolation (it was never scored). Pure + total: it never raises and never
    applies -- queuing/dropping is the caller's job."""
    kind = str((proposal or {}).get("target_kind") or "").strip()
    tid = str((proposal or {}).get("target_id") or "").strip()
    ok, why = validate_proposal(proposal, improvable=improvable, protected=protected)
    if not ok:
        return {"accept": False, "reason": "isolation_rejected", "detail": why,
                "delta": None, "target_kind": kind, "target_id": tid}
    accept, delta = proof_of_utility(
        baseline_score, proposed_score,
        margin=margin, require_improvement=require_improvement)
    return {"accept": bool(accept),
            "reason": "accepted" if accept else "regression",
            "delta": delta, "target_kind": kind, "target_id": tid}
