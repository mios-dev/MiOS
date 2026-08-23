# AI-hint: WS-RES-GOV cost/energy accounting core (the PURE half, CLASSic "Cost" axis).
# AI-doc: usr/share/doc/mios/manual/observability.md
from __future__ import annotations

from typing import Dict, Optional

_WH_PER_J = 1.0 / 3600.0   # 1 Wh = 3600 J; here energy_wh = watts * seconds / 3600


class CostModel:
    """Turns a dispatch into an energy + dollar estimate. Rates are SSOT-supplied
    (mios.toml [cost]); conservative defaults. `usd_per_kwh = 0` => energy is
    tracked in Wh but the local $ stays 0 (energy-only accounting, the common
    local case)."""

    __slots__ = ("gpu_watts", "usd_per_kwh", "remote_usd_per_mtok")

    def __init__(self, *, gpu_watts: float = 350.0, usd_per_kwh: float = 0.0,
                 remote_usd_per_mtok: float = 0.0) -> None:
        self.gpu_watts = max(0.0, float(gpu_watts))
        self.usd_per_kwh = max(0.0, float(usd_per_kwh))
        self.remote_usd_per_mtok = max(0.0, float(remote_usd_per_mtok))

    def estimate(self, *, lane: str = "local", elapsed_s: float = 0.0,
                 prompt_tokens: int = 0, completion_tokens: int = 0,
                 is_remote: bool = False,
                 usd_per_mtok: "Optional[float]" = None) -> dict:
        """One dispatch's cost. LOCAL: energy = gpu_watts * elapsed_s (Wh), $ from
        usd_per_kwh. REMOTE: energy_wh = 0 (provider's), $ = tokens * the lane's
        $/Mtok (per-lane override or the model default). Deterministic; never
        negative."""
        toks = max(0, int(prompt_tokens)) + max(0, int(completion_tokens))
        el = max(0.0, float(elapsed_s))
        if is_remote:
            rate = float(usd_per_mtok if usd_per_mtok is not None
                         else self.remote_usd_per_mtok)
            usd = (toks / 1_000_000.0) * max(0.0, rate)
            return {"lane": str(lane), "energy_wh": 0.0, "usd": round(usd, 6),
                    "tokens": toks, "elapsed_s": round(el, 3), "remote": True}
        energy_wh = self.gpu_watts * el * _WH_PER_J
        usd = (energy_wh / 1000.0) * self.usd_per_kwh
        return {"lane": str(lane), "energy_wh": round(energy_wh, 4),
                "usd": round(usd, 6), "tokens": toks,
                "elapsed_s": round(el, 3), "remote": False}


class CostLedger:
    """Rolling accumulation of dispatch cost: totals + per-lane breakdown. Single
    event loop, no lock needed (mirrors mios_reputation's in-process counters)."""

    __slots__ = ("_usd", "_energy_wh", "_tokens", "_n", "_by_lane")

    def __init__(self) -> None:
        self._usd = 0.0
        self._energy_wh = 0.0
        self._tokens = 0
        self._n = 0
        self._by_lane: "Dict[str, dict]" = {}

    def record(self, est: dict) -> None:
        """Accumulate one estimate() result. Ignores a falsy/empty estimate."""
        if not est:
            return
        usd = float(est.get("usd") or 0.0)
        wh = float(est.get("energy_wh") or 0.0)
        tk = int(est.get("tokens") or 0)
        lane = str(est.get("lane") or "?")
        self._usd += usd
        self._energy_wh += wh
        self._tokens += tk
        self._n += 1
        b = self._by_lane.setdefault(lane, {"usd": 0.0, "energy_wh": 0.0,
                                            "tokens": 0, "n": 0})
        b["usd"] += usd
        b["energy_wh"] += wh
        b["tokens"] += tk
        b["n"] += 1

    def remaining(self, budget_usd: "Optional[float]") -> float:
        """$ left under a budget ceiling; inf when no budget set; floored at 0."""
        if not budget_usd or float(budget_usd) <= 0:
            return float("inf")
        return max(0.0, float(budget_usd) - self._usd)

    def over_budget(self, budget_usd: "Optional[float]") -> bool:
        return self.remaining(budget_usd) <= 0.0

    def snapshot(self) -> dict:
        return {
            "dispatches": self._n,
            "usd": round(self._usd, 6),
            "energy_wh": round(self._energy_wh, 3),
            "tokens": self._tokens,
            "by_lane": {k: {"usd": round(v["usd"], 6),
                            "energy_wh": round(v["energy_wh"], 3),
                            "tokens": v["tokens"], "n": v["n"]}
                        for k, v in sorted(self._by_lane.items())},
        }
