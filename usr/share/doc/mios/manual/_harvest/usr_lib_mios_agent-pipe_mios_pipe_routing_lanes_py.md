<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_lanes -- unified inference-lane resolver for the MiOS...

mios_lanes -- unified inference-lane resolver for the MiOS agent-pipe (WS-1, the
AIOS lane-selection layer).

A LANE is a single inference endpoint: ``(id, url, model)``. The resolver is given a
map of lanes and, per ROLE, an ordered PREFERENCE CHAIN of lane ids; ``pick(role)``
returns the first REACHABLE lane in the chain. Health is probed via an INJECTED async
callable and cached for ``ttl`` seconds; a lane that fails a probe is parked on
``cooldown`` so it is skipped (not re-probed) until it expires -- so a dead heavy lane
fails straight over to the next lane instead of 404ing every request, and recovers
automatically once the cooldown lapses and a probe succeeds. The terminal (light)
lane is returned as the floor even if its own probe is failing, so a turn degrades
rather than dead-ends.

Pure stdlib (only ``time``) in the sibling-module style of mios_sched / mios_owui:
NO server.py import, NO globals. server.py owns the wiring -- it constructs the lane
map from its already-resolved endpoint constants + the [ai].heavy_engine SSOT, injects
an httpx probe, and exposes the module-level instance. test_mios_lanes.py drives this
module with a fake clock + fake probe, no agent-pipe runtime deps.

<!-- mios-src:bf2e92aad965 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes.py:3-21 -->

### Ordered preference chain of lane ids from the...

Ordered preference chain of lane ids from the [ai].heavy_engine selector.

    ``available`` -- iterable of the lane ids the resolver was given (e.g.
    ``{'sglang','vllm','light'}``).
    ``heavy_engine`` -- either a single preferred engine (``'sglang'`` | ``'vllm'`` |
    ``'light'``) OR an explicit comma-list (``'sglang,vllm,light'``, honoured
    verbatim). Empty/None defaults to ``'sglang'`` (the SSOT default).

    Rules: drop ids that are not available; dedupe preserving order; keep the
    ``light`` terminal lane LAST when it is present (the always-on floor) but never
    add it if an explicit comma-chain omitted it (respect the operator's choice).
    ``'light'`` as a single engine forces a light-only chain (no heavy).

<!-- mios-src:97fdd80013b3 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes.py:44-55 -->

### Health-aware lane picker. Construct with...

Health-aware lane picker. Construct with::

        LaneResolver(lanes, chains, probe, ttl=30.0, cooldown=60.0)

    ``lanes``    -- {id: Lane}.
    ``chains``   -- {role: [lane_id, ...]} ordered preference per role.
    ``probe``    -- async callable ``probe(url) -> bool`` (True == lane serving).
    ``ttl``      -- seconds a health result is cached (probe at most once / window).
    ``cooldown`` -- seconds a FAILED lane is skipped before it is re-probed.
    ``clock``    -- injectable monotonic clock (tests pass a fake).

<!-- mios-src:6c01efb48734 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes.py:77-86 -->
