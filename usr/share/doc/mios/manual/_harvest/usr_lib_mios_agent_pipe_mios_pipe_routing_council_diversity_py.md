<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Council input-diversity gate + confidence-aware aggregation bypass (T-047 RouteMoA GAP-1 / T-048 MOSAIC GAP-2). Pure geometry over the ALREADY-computed 768-d nomic council-response embeddings -- NO extra model calls beyond one embed per response (computed once, REUSED by both gates), NO hand-coded weights/keywords. select_diverse picks a diverse subset of council responses for the aggregator (lowest-mean-similarity seed + minimax-orthogonal expansion; a slot whose similarity to the selected set exceeds diversity_threshold is dropped/replaced by the next most-orthogonal candidate). should_bypass is the aggregation-bypass predicate (True iff every pairwise cosine exceeds aggregator_bypass_threshold -> the council converged -> skip the aggregator LLM). medoid_index picks the highest-confidence (most representative / consensus) individual response when bypassing. apply_council_gates is the async orchestrator swarm._synthesise calls: it embeds the k council outputs ONCE, applies bypass (precedence) then diversity, and emits the aggregator_bypass event via the injected event logger. _STATS/note_aggregator/bypassed_pct expose the bypass rate for /v1/cluster/health. Both gates DEFAULT-OFF (degrade-open): off => the synthesis path is byte-identical. Pure of server.py (one-way boundary); the cosine metric is the SSOT one from mios_toolsearch.
AI-related: ./swarm.py, ./toolsearch.py, ../kernel/clusterhealth.py, ../kernel/config.py, ./test_mios_council_diversity.py
AI-functions: select_diverse, should_bypass, medoid_index, apply_council_gates, note_aggregator, bypassed_pct, reset_stats

<!-- mios-src:2d0b61676c48 from usr/lib/mios/agent-pipe/mios_pipe/routing/council_diversity.py:1-3 -->

