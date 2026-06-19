# AI-hint: Standalone unit test for mios_lanes (WS-1 unified lane resolver) -- verifies build_chain ordering, health-cached pick, per-lane cooldown failover, terminal-floor degrade, and recovery, with a fake clock + fake probe and no agent-pipe runtime deps.
# AI-related: mios_lanes
# AI-functions: _check, t_build_chain, t_pick_prefers_heavy, t_failover_to_vllm_then_light, t_cooldown_skips_reprobe, t_ttl_caches, t_recovery_after_cooldown, t_terminal_floor, t_mark_down, main
"""Standalone unit test for mios_lanes (WS-1).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps (httpx/fastapi/...). Mirrors the
mios_sched test pattern: a mock-free asyncio harness with explicit asserts and a
PASS/FAIL summary; exit code != 0 on any failure.

Run:  python test_mios_lanes.py
"""

import asyncio
import sys

from mios_lanes import Lane, LaneResolver, build_chain

_RESULTS: list = []


def _check(name: str, cond: bool, detail: str = "") -> None:
    _RESULTS.append((name, bool(cond), detail))
    print("  [%s] %s%s" % ("OK" if cond else "FAIL", name, (" -- " + detail) if detail and not cond else ""))


class _Clock:
    """Mutable monotonic clock."""
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _lanes():
    return {
        "light": Lane("light", "http://localhost:11450/v1", "granite4.1:8b"),
        "sglang": Lane("sglang", "http://localhost:11441/v1", "mios-heavy"),
        "vllm": Lane("vllm", "http://localhost:11440/v1", "mios-heavy"),
    }


def _resolver(up, clock, **kw):
    """up: dict {lane_url_substring: bool}; probe counts calls in `calls`."""
    calls = {"n": 0}

    async def probe(url):
        calls["n"] += 1
        # match by port substring
        for key, ok in up.items():
            if key in url:
                return ok
        return False

    lanes = _lanes()
    chain = build_chain(kw.pop("heavy_engine", "sglang"), lanes.keys())
    r = LaneResolver(lanes, {"heavy": chain, "tool": chain}, probe,
                     ttl=kw.pop("ttl", 30.0), cooldown=kw.pop("cooldown", 60.0),
                     clock=clock)
    return r, calls


# --- build_chain -----------------------------------------------------------
async def t_build_chain():
    ids = ["light", "sglang", "vllm"]
    _check("chain sglang-first", build_chain("sglang", ids) == ["sglang", "vllm", "light"],
           str(build_chain("sglang", ids)))
    _check("chain vllm-first", build_chain("vllm", ids) == ["vllm", "sglang", "light"],
           str(build_chain("vllm", ids)))
    _check("chain explicit comma", build_chain("vllm,light", ids) == ["vllm", "light"],
           str(build_chain("vllm,light", ids)))
    _check("chain light-only", build_chain("light", ids) == ["light"],
           str(build_chain("light", ids)))
    _check("chain default(empty)->sglang", build_chain("", ids) == ["sglang", "vllm", "light"],
           str(build_chain("", ids)))
    _check("chain drops unavailable", build_chain("sglang", ["light", "sglang"]) == ["sglang", "light"],
           str(build_chain("sglang", ["light", "sglang"])))
    _check("chain light always terminal", build_chain("light,sglang", ids) == ["sglang", "light"],
           str(build_chain("light,sglang", ids)))


# --- pick ------------------------------------------------------------------
async def t_pick_prefers_heavy():
    clk = _Clock()
    r, _ = _resolver({"11441": True, "11440": True, "11450": True}, clk)
    lane = await r.pick("tool")
    _check("prefers sglang when up", lane.id == "sglang", lane.id)


async def t_failover_to_vllm_then_light():
    clk = _Clock()
    r, _ = _resolver({"11441": False, "11440": True, "11450": True}, clk)
    _check("sglang down -> vllm", (await r.pick("tool")).id == "vllm")
    clk.advance(100)  # past cooldown so a fresh state
    r2, _ = _resolver({"11441": False, "11440": False, "11450": True}, clk)
    _check("both heavy down -> light", (await r2.pick("tool")).id == "light")


async def t_cooldown_skips_reprobe():
    clk = _Clock()
    r, calls = _resolver({"11441": False, "11440": True, "11450": True}, clk, cooldown=60.0)
    await r.pick("tool")               # probes sglang(fail)+vllm(ok) = 2
    n1 = calls["n"]
    await r.pick("tool")               # sglang in cooldown -> skipped; vllm cached(ttl) -> 0 new
    _check("cooldown+ttl avoid reprobe", calls["n"] == n1, "calls went %d->%d" % (n1, calls["n"]))


async def t_ttl_caches():
    clk = _Clock()
    r, calls = _resolver({"11441": True, "11450": True, "11440": True}, clk, ttl=30.0)
    await r.pick("tool")
    n1 = calls["n"]
    clk.advance(10)                    # within ttl
    await r.pick("tool")
    _check("ttl caches health", calls["n"] == n1, "calls %d->%d" % (n1, calls["n"]))
    clk.advance(40)                    # past ttl -> reprobe
    await r.pick("tool")
    _check("reprobe after ttl", calls["n"] > n1)


async def t_recovery_after_cooldown():
    clk = _Clock()
    up = {"11441": False, "11440": True, "11450": True}
    r, _ = _resolver(up, clk, cooldown=60.0, ttl=30.0)
    _check("initially vllm (sglang down)", (await r.pick("tool")).id == "vllm")
    up["11441"] = True                 # sglang comes back
    clk.advance(70)                    # past cooldown -> re-probe sglang
    _check("recovers to sglang after cooldown", (await r.pick("tool")).id == "sglang")


async def t_terminal_floor():
    clk = _Clock()
    # nothing up at all -> still returns the terminal floor (light), never None
    r, _ = _resolver({"11441": False, "11440": False, "11450": False}, clk)
    lane = await r.pick("tool")
    _check("all down -> terminal floor light (not None)", lane is not None and lane.id == "light",
           repr(lane))


async def t_mark_down():
    clk = _Clock()
    r, _ = _resolver({"11441": True, "11440": True, "11450": True}, clk)
    _check("up before mark_down", (await r.pick("tool")).id == "sglang")
    r.mark_down("sglang")
    _check("mark_down forces failover", (await r.pick("tool")).id == "vllm")


async def main():
    print("test_mios_lanes (WS-1 lane resolver)")
    for fn in (t_build_chain, t_pick_prefers_heavy, t_failover_to_vllm_then_light,
               t_cooldown_skips_reprobe, t_ttl_caches, t_recovery_after_cooldown,
               t_terminal_floor, t_mark_down):
        await fn()
    fails = [n for (n, ok, _d) in _RESULTS if not ok]
    print("\n%d checks, %d passed, %d failed" % (len(_RESULTS), len(_RESULTS) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
