# AI-hint: Unified inference-lane resolver (WS-1) -- the ONE place the agent-pipe chooses a model lane. Picks the best reachable lane from an ordered preference chain with a TTL health cache + per-lane cooldown, so a dead lane fails over (never 404s) and auto-recovers; collapses the two heavy lanes (SGLang/vLLM, both served as 'mios-heavy') behind one [ai].heavy_engine selector. Pure of server/FastAPI globals -> unit-testable.
# AI-related: server.py (_pick_tool_backend, _TOOL_BACKEND*, _load_node_pool), mios.toml [ai].heavy_engine / [ai.sglang] / [ai.vllm] / [llamacpp]
# AI-functions: build_chain, class Lane, class LaneResolver
"""mios_lanes -- unified inference-lane resolver for the MiOS agent-pipe (WS-1, the
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
"""
import time


class Lane:
    """A single inference endpoint. ``url`` is the OpenAI /v1 base (no trailing
    slash); ``model`` is the served-model-name to request on it."""
    __slots__ = ("id", "url", "model")

    def __init__(self, id: str, url: str, model: str):
        self.id = id
        self.url = url
        self.model = model

    def as_tuple(self) -> tuple:
        """(url, model) -- the shape the legacy _pick_tool_backend callers expect."""
        return (self.url, self.model)

    def __repr__(self) -> str:  # pragma: no cover -- debug only
        return "Lane(%r, %r, %r)" % (self.id, self.url, self.model)


def build_chain(heavy_engine, available) -> list:
    """Ordered preference chain of lane ids from the [ai].heavy_engine selector.

    ``available`` -- iterable of the lane ids the resolver was given (e.g.
    ``{'sglang','vllm','light'}``).
    ``heavy_engine`` -- either a single preferred engine (``'sglang'`` | ``'vllm'`` |
    ``'light'``) OR an explicit comma-list (``'sglang,vllm,light'``, honoured
    verbatim). Empty/None defaults to ``'sglang'`` (the SSOT default).

    Rules: drop ids that are not available; dedupe preserving order; keep the
    ``light`` terminal lane LAST when it is present (the always-on floor) but never
    add it if an explicit comma-chain omitted it (respect the operator's choice).
    ``'light'`` as a single engine forces a light-only chain (no heavy)."""
    avail_set = set(available)
    he = (heavy_engine or "sglang").strip().lower()
    if "," in he:
        order = [x.strip() for x in he.split(",") if x.strip()]
    elif he == "light":
        order = ["light"]
    else:
        heavies = [x for x in ("sglang", "vllm") if x in avail_set]
        order = ([he] if he in avail_set else []) + [x for x in heavies if x != he] + ["light"]
    seen: set = set()
    chain: list = []
    for x in order:
        if x in avail_set and x not in seen:
            seen.add(x)
            chain.append(x)
    if "light" in chain:                       # force the floor lane terminal
        chain = [x for x in chain if x != "light"] + ["light"]
    return chain


class LaneResolver:
    """Health-aware lane picker. Construct with::

        LaneResolver(lanes, chains, probe, ttl=30.0, cooldown=60.0)

    ``lanes``    -- {id: Lane}.
    ``chains``   -- {role: [lane_id, ...]} ordered preference per role.
    ``probe``    -- async callable ``probe(url) -> bool`` (True == lane serving).
    ``ttl``      -- seconds a health result is cached (probe at most once / window).
    ``cooldown`` -- seconds a FAILED lane is skipped before it is re-probed.
    ``clock``    -- injectable monotonic clock (tests pass a fake)."""

    def __init__(self, lanes, chains, probe, *, ttl: float = 30.0,
                 cooldown: float = 60.0, clock=time.monotonic):
        self._lanes = dict(lanes)
        self._chains = {k: list(v) for k, v in chains.items()}
        self._probe = probe
        self._ttl = float(ttl)
        self._cooldown = float(cooldown)
        self._clock = clock
        self._health: dict = {}          # id -> (ts, ok)
        self._cooldown_until: dict = {}   # id -> ts

    async def _is_up(self, lane: Lane) -> bool:
        now = self._clock()
        if now < self._cooldown_until.get(lane.id, 0.0):
            return False                  # parked -> skip the probe, treat as down
        cached = self._health.get(lane.id)
        if cached is not None and (now - cached[0]) < self._ttl:
            return cached[1]
        try:
            ok = bool(await self._probe(lane.url))
        except Exception:  # noqa: BLE001 -- any probe failure => lane is down
            ok = False
        self._health[lane.id] = (now, ok)
        if not ok:
            self._cooldown_until[lane.id] = now + self._cooldown
        else:
            self._cooldown_until.pop(lane.id, None)
        return ok

    async def pick(self, role: str, fallback_role: str = "heavy"):
        """First reachable Lane in ``role``'s chain. Returns the chain's terminal
        lane (the always-on floor) if none probe up, or None if the role has no
        configured lanes at all. Never raises."""
        chain = self._chains.get(role) or self._chains.get(fallback_role) or []
        last = None
        for lid in chain:
            lane = self._lanes.get(lid)
            if lane is None:
                continue
            last = lane
            if await self._is_up(lane):
                return lane
        return last                       # terminal floor (e.g. light) or None

    def mark_down(self, lane_id: str) -> None:
        """Force a lane onto cooldown (e.g. after a dispatch 404/connect error at a
        call site) so the next pick fails it over immediately."""
        now = self._clock()
        self._health[lane_id] = (now, False)
        self._cooldown_until[lane_id] = now + self._cooldown

    def snapshot(self) -> dict:
        """Health/cooldown view for /v1/cluster/health + diagnostics."""
        return {"lanes": {k: {"url": v.url, "model": v.model} for k, v in self._lanes.items()},
                "chains": {k: list(v) for k, v in self._chains.items()},
                "health": dict(self._health),
                "cooldown_until": dict(self._cooldown_until)}
