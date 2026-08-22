<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### INFERENCE lane-resolver cluster (strangler-fig refactor)....

INFERENCE lane-resolver cluster (strangler-fig refactor).

Extracted VERBATIM from ``server.py``. ``_lane_resolver`` lazily builds the WS-1
unified :class:`mios_lanes.LaneResolver` from SSOT and caches it in the
module-owned ``_LANE_RESOLVER`` singleton (rebound at runtime); ``_pick_tool_backend``
returns the ``(url, model)`` for the client-tools loop via that resolver with a
legacy heavy/light-probe fallback; ``_heavy_lane_up`` is the cached SGLang-heavy
reachability probe. The config scalars are imported from :mod:`mios_config`;
``mios_lanes`` is imported directly; every server-resident symbol (``_get_client``,
``_is_remote_endpoint``) is injected via :func:`configure` (one-way boundary -- this
module never imports ``server``). server.py re-imports the moved names under their
original aliases, and reads the live ``_LANE_RESOLVER`` through
:func:`_lane_resolver_current` so the importable surface stays byte-identical.

<!-- mios-src:d8fceacfb041 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes_resolver.py:3-16 -->

### WS-1 unified lane resolver (mios_lanes), built LAZILY from...

WS-1 unified lane resolver (mios_lanes), built LAZILY from SSOT so _toml_section
    / _get_client are defined, then cached. ONE place a model lane is chosen: the
    [ai].heavy_engine-preferred heavy lane, then the other heavy lane, then the always-on
    light lane, with a per-lane cooldown so a dead lane fails over (never 404s). Collapses
    the two 'mios-heavy' lanes (SGLang :11441 + vLLM :11440) behind one selector.

<!-- mios-src:8200d2470c87 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes_resolver.py:85-89 -->

### (url, model) for the client-tools loop -- delegated to the...

(url, model) for the client-tools loop -- delegated to the WS-1 unified lane
    resolver: the preferred heavy reasoner when reachable, else the other heavy lane,
    else the always-on light lane (with per-lane cooldown so a dead lane fails over,
    never 404s). Degrade-open: any resolver error falls back to the legacy heavy/light
    probe so the agentic surface never hard-fails.

<!-- mios-src:812932e88c19 from usr/lib/mios/agent-pipe/mios_pipe/routing/lanes_resolver.py:142-146 -->
