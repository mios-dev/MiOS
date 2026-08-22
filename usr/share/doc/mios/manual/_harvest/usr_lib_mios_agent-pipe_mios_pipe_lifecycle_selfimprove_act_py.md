<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_selfimprove_act -- pure ACT-half decision core for the...

mios_selfimprove_act -- pure ACT-half decision core for the self-curation loop.

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

<!-- mios-src:242be2b4e1dd from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:3-40 -->

### True iff a proposal targeting ``target_kind`` is in the...

True iff a proposal targeting ``target_kind`` is in the improvable surface
    and NOT in the protected surface. DENY WINS: a kind in ``protected`` is refused
    even if it also appears in ``improvable`` (fail-safe, like the HITL resolver
    erring toward blocking) so the evaluator / eval-data / lane-config can never be
    edited by a proposal. Both surfaces come from the caller (SSOT) -- an empty
    improvable surface allows nothing (degrade-closed).

<!-- mios-src:5283289e5765 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:50-55 -->

### Validate a proposal's SHAPE + its target isolation. Returns...

Validate a proposal's SHAPE + its target isolation. Returns ``(ok, reason)``.

    A proposal is ``{target_kind, target_id, change, rationale}`` (change/rationale
    are the human-reviewable description -- a diff/tweak + why). Rejected when it is
    not a dict, lacks an identified target, or its ``target_kind`` is not in the
    improvable surface / is in the protected surface (the structural isolation).
    The reason is a stable machine token (not prose) so callers can log/branch on it
    without a keyword match.

<!-- mios-src:2e96b10c7e81 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:67-74 -->

### Keep only the DISCRIMINATIVE held-out eval candidates...

Keep only the DISCRIMINATIVE held-out eval candidates (Autodata curation).

    Each candidate carries the two lane scores under ``weak`` and ``strong`` (the
    light vs heavy/council pass-rates on that task). A candidate with no numeric
    pair is dropped (it cannot be judged). The kept set is the held-out eval the
    proof-of-utility scores baseline-vs-proposed on -- so a non-discriminative task
    can never inflate or mask a regression.

<!-- mios-src:9dd396861109 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:104-110 -->

### The pass^k reliability score over a held-out eval, via...

The pass^k reliability score over a held-out eval, via :mod:`mios_bench`.
    ``tasks`` = ``[(n_trials, c_correct), ...]`` per task. pass^k ("ALL k repeats
    succeed", tau-bench) is the worst-case reliability number production needs --
    the same metric the skill-promotion gate (T-049) uses, here applied to score a
    variant rather than to promote a skill. Thin wrapper so the ACT module names its
    scoring in its own domain; the math lives in mios_bench (single source).

<!-- mios-src:9035aa3695ff from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:124-129 -->

### T-064 accept criterion. Returns ``(accept, delta)`` where...

T-064 accept criterion. Returns ``(accept, delta)`` where
    ``delta = proposed - baseline``.

    ACCEPT iff the proposed variant does not regress the baseline beyond ``margin``
    (``delta >= -margin``; ``margin = 0`` => strict non-regression ``proposed >=
    baseline``). When ``require_improvement`` is set, a strict improvement is also
    required (``delta > 0``) -- used where a discriminative eval applies and a
    no-op change should not be queued. Both ``margin`` and ``require_improvement``
    are SSOT-supplied; nothing is baked here.

<!-- mios-src:16e8821b51af from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:136-144 -->

### THE single ACT verdict, composing isolation +...

THE single ACT verdict, composing isolation + proof-of-utility.

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
    applies -- queuing/dropping is the caller's job.

<!-- mios-src:be078fa0d95b from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py:155-171 -->
