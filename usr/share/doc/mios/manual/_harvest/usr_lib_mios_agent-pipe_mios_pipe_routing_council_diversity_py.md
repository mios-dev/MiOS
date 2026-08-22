<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Council diversity gate + aggregation bypass (T-047 GAP-1 /...

Council diversity gate + aggregation bypass (T-047 GAP-1 / T-048 GAP-2).

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

<!-- mios-src:786379e6ddc5 from usr/lib/mios/agent-pipe/mios_pipe/routing/council_diversity.py:3-29 -->

### T-047 RouteMoA input-diversity selection. Returns the...

T-047 RouteMoA input-diversity selection. Returns the SELECTED indices
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
    response there is nothing to diversify (returns all indices).

<!-- mios-src:6b04ebc4b812 from usr/lib/mios/agent-pipe/mios_pipe/routing/council_diversity.py:81-95 -->

### Index of the highest-confidence individual response: the...

Index of the highest-confidence individual response: the medoid -- the
    response with the HIGHEST mean cosine similarity to the others, i.e. the one
    most representative of the converged council. When the bypass precondition
    holds every candidate is near-identical, so this is a principled, weight-free
    choice of the single response to ship instead of the aggregator's output.

<!-- mios-src:b8c5bbf3aa40 from usr/lib/mios/agent-pipe/mios_pipe/routing/council_diversity.py:137-141 -->

### Apply the T-047 diversity gate + T-048 aggregation bypass...

Apply the T-047 diversity gate + T-048 aggregation bypass over the council
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
    unchanged with ``bypass=None`` (behaviour identical to gates-off).

<!-- mios-src:39854be0b856 from usr/lib/mios/agent-pipe/mios_pipe/routing/council_diversity.py:158-172 -->
