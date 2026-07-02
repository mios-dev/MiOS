# AI-hint: Council input-diversity gate + confidence-aware aggregation bypass (T-047 RouteMoA GAP-1 / T-048 MOSAIC GAP-2). Pure geometry over the ALREADY-computed 768-d nomic council-response embeddings -- NO extra model calls beyond one embed per response (computed once, REUSED by both gates), NO hand-coded weights/keywords. select_diverse picks a diverse subset of council responses for the aggregator (lowest-mean-similarity seed + minimax-orthogonal expansion; a slot whose similarity to the selected set exceeds diversity_threshold is dropped/replaced by the next most-orthogonal candidate). should_bypass is the aggregation-bypass predicate (True iff every pairwise cosine exceeds aggregator_bypass_threshold -> the council converged -> skip the aggregator LLM). medoid_index picks the highest-confidence (most representative / consensus) individual response when bypassing. apply_council_gates is the async orchestrator swarm._synthesise calls: it embeds the k council outputs ONCE, applies bypass (precedence) then diversity, and emits the aggregator_bypass event via the injected event logger. _STATS/note_aggregator/bypassed_pct expose the bypass rate for /v1/cluster/health. Both gates DEFAULT-OFF (degrade-open): off => the synthesis path is byte-identical. Pure of server.py (one-way boundary); the cosine metric is the SSOT one from mios_toolsearch.
# AI-related: ./swarm.py, ./toolsearch.py, ../kernel/clusterhealth.py, ../kernel/config.py, ./test_mios_council_diversity.py
# AI-functions: select_diverse, should_bypass, medoid_index, apply_council_gates, note_aggregator, bypassed_pct, reset_stats
"""Council diversity gate + aggregation bypass (T-047 GAP-1 / T-048 GAP-2).

The council/swarm fan-out produces ``k`` responses that are then handed to a
final aggregator LLM (``polish_response`` in :mod:`mios_pipe.routing.swarm`).
Two failure modes this module addresses, BOTH riding the 768-d nomic embeddings
that already exist on that path (no extra model calls, no per-pair calls):

* **T-047 (RouteMoA input diversity).** An echo-chamber council -- several
  near-identical responses -- wastes the aggregator's context and degrades
  synthesis. :func:`select_diverse` prunes the inputs to a semantically diverse
  subset: a lowest-mean-similarity seed, then minimax-orthogonal expansion; any
  candidate whose similarity to the selected set exceeds ``diversity_threshold``
  is redundant and is replaced by the next most-orthogonal candidate (dropped
  when even the most-orthogonal remaining candidate is over threshold).

* **T-048 (MOSAIC confidence-aware bypass).** When the whole council converges
  (every pairwise cosine exceeds ``aggregator_bypass_threshold``) the expensive
  aggregator call adds nothing. :func:`should_bypass` detects that; the caller
  then ships the highest-confidence individual response (:func:`medoid_index`,
  the consensus medoid) and skips the aggregator LLM.

The decision is pure cosine geometry -- no hand-coded scoring weight, no keyword
or language gate. Both gates default OFF (degrade-open); with both off nothing
here runs and the synthesis path is byte-identical. This module never imports
``server`` (one-way boundary); the cosine metric is the single SSOT one shared
with the verb-retrieval cache in :mod:`mios_toolsearch`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from mios_toolsearch import _cosine

log = logging.getLogger("mios-agent-pipe")


# -- Aggregation-bypass observability -------------------------------
# In-memory counters (reset on restart) surfaced as aggregator_calls_bypassed_pct
# in /v1/cluster/health (mios_clusterhealth). note_aggregator is called ONCE per
# real aggregation opportunity while the bypass gate is enabled; when the gate is
# off nothing is counted (pct stays 0.0) so the metric is honest, not inflated.
_STATS = {"aggregator_total": 0, "aggregator_bypassed": 0}


def note_aggregator(bypassed: bool) -> None:
    """Record one aggregation opportunity and whether it was bypassed."""
    _STATS["aggregator_total"] += 1
    if bypassed:
        _STATS["aggregator_bypassed"] += 1


def bypassed_pct() -> float:
    """Percentage of aggregation opportunities that skipped the aggregator LLM."""
    tot = _STATS["aggregator_total"]
    if tot <= 0:
        return 0.0
    return round(100.0 * _STATS["aggregator_bypassed"] / tot, 2)


def reset_stats() -> None:
    _STATS["aggregator_total"] = 0
    _STATS["aggregator_bypassed"] = 0


# -- Pure similarity geometry ---------------------------------------

def _sim_matrix(vectors: list, cosine: Callable = _cosine) -> list:
    """Full symmetric pairwise cosine matrix (diagonal = 1.0). O(k^2) cosine over
    the CACHED vectors -- NOT O(k^2) model calls (the vectors are embedded once)."""
    n = len(vectors)
    m = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = float(cosine(vectors[i], vectors[j]))
            m[i][j] = s
            m[j][i] = s
    return m


def select_diverse(vectors: list, threshold: float,
                   cosine: Callable = _cosine) -> list:
    """T-047 RouteMoA input-diversity selection. Returns the SELECTED indices
    (a subset of ``range(len(vectors))``) of the council responses to hand the
    aggregator:

      * seed ``i0 = argmin_i mean_{j!=i} S_ij`` -- the most peripheral response
        (lowest mean similarity to the rest);
      * expand by minimax: repeatedly add the remaining candidate whose MAXIMUM
        similarity to the already-selected set is smallest (the most orthogonal);
      * a candidate whose max-similarity to the selected set exceeds ``threshold``
        is redundant -- it is passed over for the next most-orthogonal candidate;
        once even the most-orthogonal remaining candidate is over threshold every
        remaining response is a near-duplicate of the set and they are dropped.

    The ranking is purely the cosine geometry -- no hand-coded weight. With <=1
    response there is nothing to diversify (returns all indices)."""
    n = len(vectors)
    if n <= 1:
        return list(range(n))
    S = _sim_matrix(vectors, cosine)
    mean_sim = [sum(S[i][j] for j in range(n) if j != i) / (n - 1)
                for i in range(n)]
    seed = min(range(n), key=lambda i: mean_sim[i])
    selected = [seed]
    remaining = [i for i in range(n) if i != seed]
    while remaining:
        cand = min(remaining, key=lambda i: max(S[i][q] for q in selected))
        if max(S[cand][q] for q in selected) > threshold:
            break  # most-orthogonal candidate is still redundant -> so is the rest
        selected.append(cand)
        remaining.remove(cand)
    return selected


def should_bypass(vectors: list, threshold: float,
                  cosine: Callable = _cosine) -> tuple:
    """T-048 MOSAIC bypass predicate. Returns ``(bypass, mean_similarity)`` where
    ``bypass`` is True iff there are >=2 council responses and EVERY pairwise
    cosine similarity exceeds ``threshold`` (the council converged). Fewer than 2
    responses cannot converge -> ``(False, 0.0)``. ``mean_similarity`` is the mean
    over the unique pairs."""
    n = len(vectors)
    if n < 2:
        return (False, 0.0)
    sims = []
    all_exceed = True
    for i in range(n):
        for j in range(i + 1, n):
            s = float(cosine(vectors[i], vectors[j]))
            sims.append(s)
            if not (s > threshold):
                all_exceed = False
    mean_s = sum(sims) / len(sims) if sims else 0.0
    return (all_exceed, mean_s)


def medoid_index(vectors: list, cosine: Callable = _cosine) -> int:
    """Index of the highest-confidence individual response: the medoid -- the
    response with the HIGHEST mean cosine similarity to the others, i.e. the one
    most representative of the converged council. When the bypass precondition
    holds every candidate is near-identical, so this is a principled, weight-free
    choice of the single response to ship instead of the aggregator's output."""
    n = len(vectors)
    if n <= 1:
        return 0
    S = _sim_matrix(vectors, cosine)
    return max(range(n),
               key=lambda i: sum(S[i][j] for j in range(n) if j != i) / (n - 1))


async def apply_council_gates(
    nodes: list, *, embed_one: Optional[Callable],
    cosine: Callable = _cosine,
    diversity_gate: bool = False, diversity_threshold: float = 0.92,
    aggregator_bypass: bool = False, aggregator_bypass_threshold: float = 0.95,
    output_key: str = "output",
    log_event: Optional[Callable] = None,
) -> tuple:
    """Apply the T-047 diversity gate + T-048 aggregation bypass over the council
    response ``nodes`` (each a dict carrying ``output_key`` text). Embeds every
    response's text ONCE via ``embed_one`` (the 768-d nomic vectors) and REUSES
    those vectors for both gates -- zero per-pair model calls.

    Returns ``(selected_nodes, bypass)`` where:
      * ``selected_nodes`` -- the (possibly diversity-pruned) nodes for the
        aggregator (unchanged when the diversity gate is off / nothing pruned);
      * ``bypass`` -- ``None``, or ``{"node", "mean_similarity", "council_size"}``
        when the council converged and the aggregator LLM must be SKIPPED (T-048).

    Convergence (bypass) takes precedence over diversity pruning -- a converged
    council needs neither aggregation nor trimming. Degrades OPEN: with both gates
    off, <2 nodes, no embedder, or any missing embedding it returns the nodes
    unchanged with ``bypass=None`` (behaviour identical to gates-off)."""
    if not (diversity_gate or aggregator_bypass):
        return (nodes, None)
    if not nodes or len(nodes) < 2 or embed_one is None:
        return (nodes, None)
    texts = [str((n or {}).get(output_key) or "") for n in nodes]
    try:
        vecs = list(await asyncio.gather(*[embed_one(t) for t in texts]))
    except Exception as e:  # noqa: BLE001 -- degrade-open, never break synthesis
        log.debug("council gate: embed failed -> gates skipped: %s", e)
        return (nodes, None)
    if any(not v for v in vecs):
        # A missing vector means we cannot score reliably -> no-op (gates-off shape).
        return (nodes, None)

    if aggregator_bypass:
        bypass_ok, mean_s = should_bypass(vecs, aggregator_bypass_threshold, cosine)
        if bypass_ok:
            mi = medoid_index(vecs, cosine)
            if log_event is not None:
                try:
                    log_event(kind="aggregator_bypass",
                              council_size=len(nodes), mean_similarity=mean_s)
                except Exception:  # noqa: BLE001 -- telemetry never breaks synthesis
                    pass
            return (nodes, {"node": nodes[mi], "mean_similarity": mean_s,
                            "council_size": len(nodes)})

    if diversity_gate:
        keep = set(select_diverse(vecs, diversity_threshold, cosine))
        if keep and len(keep) < len(nodes):
            return ([n for i, n in enumerate(nodes) if i in keep], None)

    return (nodes, None)
