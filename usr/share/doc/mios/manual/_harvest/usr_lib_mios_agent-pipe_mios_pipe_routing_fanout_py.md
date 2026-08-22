<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Council/swarm fan-out agent SELECTION -- model-driven...

Council/swarm fan-out agent SELECTION -- model-driven relevance, no hardcoded scorer.

Extracted from ``server.py`` (R3) and de-hardcoded. ``_pick_fanout_agents``
returns the secondary ``(name, cfg)`` agents to dispatch concurrently with the primary.

Three paths, NONE of which uses a hand-coded relevance heuristic:
  * ``force_council`` -- engage every eligible non-primary live agent (explicit swarm).
  * ``mode == "council"`` -- equal-weight: every eligible agent, sub-lane-diverse, capped.
  * default -- **model-driven**: the micro-model picks the relevant specialists from the
    refined plan + each eligible agent's published card. Degrades open to council-equal-weight.

The module is pure of ``server.py`` (one-way boundary). The live registry, dispatch
config, and the depth/lane/dedup/admission helpers are injected via :func:`configure`;
the relevance model-call is the module's own ``httpx`` POST to the SSOT micro endpoint
(same pattern as ``mios_refine``/``mios_dci``). ``server.py`` re-imports
``_pick_fanout_agents`` under its original alias and ``await``\s it (surface byte-identical).

<!-- mios-src:ed220f396db2 from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:3-19 -->

### Inject the server.py registry/config + helpers/constants...

Inject the server.py registry/config + helpers/constants the selector uses.

    Unchanged signature from the pre-de-hardcode version -- the model-driven
    relevance call uses the module's own httpx to the SSOT micro endpoint
    (mios_config._MICRO_MODEL/_MICRO_ENDPOINT) + the injected ``dispatch_cfg``
    for the mode + timeout, so no new injected dependency is required.

<!-- mios-src:098aa28a1137 from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:60-66 -->

### The eligible secondary pool

The eligible secondary pool: every registered agent except the primary that
    is not opted-out, is live (OUTAGE prune), and is research-OK. NO relevance
    scoring -- this is the deterministic membership filter only. ``research_only``
 agents/nodes join ONLY on a research/deep turn (runaway fix:
    keep the research workers OUT of an everyday turn so a trivial prompt
    doesn't cold-load the whole pool at once).

<!-- mios-src:6c436bf18ced from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:115-120 -->

### Equal-weight council selection over the eligible pool...

Equal-weight council selection over the eligible pool: sub-lane-diverse
    first (a CPU agent parallelises a GPU primary at zero dGPU cost -- a hardware
    concurrency concern, NOT a relevance heuristic), endpoint/model-deduped, capped
    at ``want``. This is the degrade-open path when model selection is off/unreachable
    and the body of council mode -- it engages secondaries (never primary-only) while
    the cap bounds width. No hand-coded relevance scoring.

<!-- mios-src:b44fa075e897 from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:134-139 -->

### A federated peer's FULL published AgentCard ``skills[]``...

A federated peer's FULL published AgentCard ``skills[]`` rendered as compact
    capability lines -- each skill's own ``name`` + ``description`` + ``tags``. This
    is the RICH advertised surface an A2A peer publishes (stored on the synthetic
    peer registry entry as ``card_skills``), NOT the collapsed strength-token id list
    the peer registration also keeps; routing on it lets the model reason over what
    the peer actually claims to do. Empty for a local ``[agents.*]`` agent (no
    published card_skills) -- purely additive to the existing card corpus.

<!-- mios-src:39664e1ba1dd from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:149-155 -->

### A compact, SSOT-sourced card for the relevance model: the...

A compact, SSOT-sourced card for the relevance model: the agent's OWN
    declared role / strengths / A2A skill-tags ([agents.*] in mios.toml + the
    AgentCard the peer publishes). No hardcoded topic text -- the card IS the
    capability surface the model reasons over.

    FED-G7 (T-051, flag-gated): when ROUTE_ON_CARD_SKILLS is set, a federated peer's
    FULL published skills[] (name/description/tags) are folded in alongside the
    strength tokens so the model routes on the advertised skill, not just the token
    proximity. OFF -> byte-identical to the strength-token-only card.

<!-- mios-src:e413f9fc449f from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:181-189 -->

### MODEL-DRIVEN relevance

MODEL-DRIVEN relevance: ask the micro-model which of the eligible agents are
    worth engaging concurrently for this plan. Returns the chosen candidate names
    (subset, capped), or ``None`` to signal degrade-open (selection off, no candidates,
    timeout, unparseable). Pure generative selection -- no scoring, no keyword map.
    The model sees the refined plan + each agent's own card and returns a JSON name
    array; we validate the names against the candidate set.

<!-- mios-src:ac1e2289c664 from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:228-233 -->

### Pick SECONDARY (name, cfg) agents to run CONCURRENTLY...

Pick SECONDARY (name, cfg) agents to run CONCURRENTLY alongside the chosen
 primary -- 'a couple at a time' + 'self-delegate to CPU
    concurrently' + 'make sure hermes isn't always the only dispatched agent'.

 Relevance is MODEL-DRIVEN (the old role/strengths-token
    overlap scoring + magic CPU-lane bonus + ASCII tokenizer was itself a hardcode):
    the micro-model picks the relevant specialists from the refined plan + each
    eligible agent's own card. NO hand-coded scoring/weight/topic map. Degrades open
    to council-equal-weight (all eligible, lane-diverse, deduped, capped) when model
    selection is off/unreachable -- never primary-only, never an unbounded runaway.
    Returns [] when fan-out is disabled / capped at 1 / nothing relevant.

 force_council (SWARM toggle): engage EVERY eligible agent
    this turn, bypassing enable/fanout_max/relevance -- the manual 'full swarm'.

<!-- mios-src:aaf4f5248bf1 from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:295-308 -->
