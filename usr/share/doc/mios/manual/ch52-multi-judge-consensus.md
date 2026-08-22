<!-- AI-hint: Chapter 52: Multi-Judge Consensus. Explains why one judge lane's yes/no is not enough to gate a pipeline, and how the weighted quorum replaces it. Covers the vote fold, abstention versus rejection, the quorum floor, reliability weighting, and Reciprocal-Rank-Fusion over ranked lanes. Documents the [consensus] SSOT block and the three ways the panel degrades open. -->

# <a name="52_multi_judge_consensus"></a>Chapter 52: Multi-Judge Consensus

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#52_multi_judge_consensus`

#### Overview

The Definition-of-Done check asks a small model one question: does this answer
substantively satisfy the query, or is it a punt? For most of MiOS's life a
single lane answered it, and that single answer gated the swarm deepen loop —
one unreliable judge could pass a punt or send a finished answer back around
forever, with no second opinion and no record that the verdict was thin.

CONS-01 replaces the lone verdict with a **reliability-weighted quorum**. The
pure math lives in `usr/lib/mios/agent-pipe/mios_pipe/routing/consensus.py`; the
judge path that calls it is `_judge_panel_verdict` in `routing/reflect.py`. The
module holds no I/O, imports no config and never imports `server.py`, so every
branch below is exercised directly by `test_mios_consensus.py`.

### <a name="52_the_weighted_vote_fold"></a>52.The Weighted Vote Fold: The Weighted Vote Fold

Each lane returns one of three things, and the third is the point of the design:

| Vote | Meaning | Effect on the fold |
|---|---|---|
| `True` | the answer satisfies the query | counts its weight toward "yes" |
| `False` | the answer is a punt | counts its weight toward "no" |
| `None` | **abstain** — the lane errored, timed out, or answered unparseably | dropped from *both* the numerator and the denominator |

Abstention is deliberately not a "no". A judge lane that fails to respond has
told you nothing about the answer; counting its silence as a rejection would
turn every transport hiccup into a false negative and send a correct answer back
around the deepen loop. The fold therefore divides only by the weight that
actually voted.

The returned score is the weight-share voting `True` among the live lanes, and
the decision is `score >= threshold`. The reported `agreement` is the share held
by whichever side won — `1.0` for a unanimous panel, near `0.5` for a split one
— so a caller can tell a confident verdict from a coin-flip.

### <a name="52_the_quorum_floor"></a>52.The Quorum Floor: The Quorum Floor

Below `min_lanes` live votes the panel returns `decision = None` rather than a
value. This matters more than it looks: if two of three lanes are down, the
surviving vote is a single judge again, and handing it back wearing a consensus
label would be worse than the original design, not better. The caller reads
`None` as "the panel declined" and keeps its ordinary single-lane answer.

### <a name="52_reliability_weighting"></a>52.Reliability Weighting: Reliability Weighting

Weights are resolved by `resolve_weights` in three tiers, each overriding the
last: the lane's own declared `weight` in SSOT, then a reliability scorer's
score when one is wired, and every result clamped up to `weight_floor`. The
clamp is what keeps the panel a panel — a lane that scored badly once is
down-weighted, never silently removed. Scores that are non-numeric, `NaN` or
infinite fall back to the default instead of poisoning the fold.

With no reliability signal and no declared weights the panel is uniform, which
means consensus can be switched on before any scorer exists.

### <a name="52_reciprocal_rank_fusion"></a>52.Reciprocal-Rank-Fusion: Reciprocal-Rank-Fusion

Where lanes return *ranked candidate lists* rather than a yes/no,
`reciprocal_rank_fusion` merges them with the standard RRF formula: each lane
contributes `weight / (k + rank)` to every candidate it ranks, with `rank`
1-based. A candidate several lanes place highly outranks one lane's favourite,
and `k` (default 60) damps the head of each list so a single lane's first place
cannot dominate the fusion outright. Ties break toward first appearance, so the
output is deterministic across runs.

### <a name="52_degrading_open"></a>52.Degrading Open: Degrading Open

The panel is off by default and can fail in three places; none of them can make
the judge less available than it was before:

1. `[consensus].enable = false` — the panel is never consulted, and the fast CPU
   path stays exactly single-judge.
2. Fewer lanes declared than `min_lanes` — the panel never engages.
3. No quorum among live votes — the panel declines and the single-lane verdict
   stands.

On top of that, `_judge_answer_satisfied` wraps the whole panel call in a guard:
any unexpected exception falls through to the single-lane path, and a
single-lane abstention still resolves to `True`, preserving the original rule
that a judge hiccup never makes a node loop forever.

### <a name="52_consensus_configuration"></a>52.Consensus Configuration: Consensus Configuration

The `[consensus]` block in `usr/share/mios/mios.toml` carries every tunable, and
each has a matching `MIOS_CONSENSUS_*` environment override plus a configurator
card:

| Key | Default | Meaning |
|---|---|---|
| `enable` | `false` | consult the panel at all |
| `threshold` | `0.5` | weight-share of "yes" needed for a satisfied verdict |
| `min_lanes` | `2` | live votes required before the fold is trusted |
| `timeout_s` | `20.0` | per-lane judge call budget |
| `weight_floor` | `0.1` | lowest weight a lane can be reduced to |
| `rrf_k` | `60` | RRF damping for ranked-list lanes |
| `lanes` | `[]` | one `{name, endpoint, model, weight}` entry per judge |

A lane with an empty `endpoint` or `model` reuses the refine lane's, so a panel
can be declared without repeating its address. Every lane costs one model call
per verdict, which is why two or three is the intended size and why the default
is off.
