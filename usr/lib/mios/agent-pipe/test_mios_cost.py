#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_cost (WS-RES-GOV cost/energy accounting, CLASSic Cost axis). Pure stdlib, no server.py/pytest. Verifies CostModel.estimate for a LOCAL GPU lane (energy = gpu_watts*elapsed -> Wh; $ from usd_per_kwh) and a REMOTE lane ($/Mtok, 0 local energy), plus the CostLedger accumulation (totals + per-lane breakdown) and remaining()/over_budget() against a $ ceiling.
# AI-related: ./mios_cost.py
# AI-functions: check, main
"""Unit tests for mios_cost (WS-RES-GOV)."""
import sys

import mios_cost as cost

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_local_energy():
    m = cost.CostModel(gpu_watts=360.0, usd_per_kwh=0.30)
    # 10s at 360W -> 360*10/3600 = 1.0 Wh ; $ = 1.0/1000 * 0.30 = 0.0003
    e = m.estimate(lane="dgpu", elapsed_s=10.0, prompt_tokens=100, completion_tokens=50)
    check("local: energy_wh = watts*s/3600", abs(e["energy_wh"] - 1.0) < 1e-6, str(e["energy_wh"]))
    check("local: usd from kwh", abs(e["usd"] - 0.0003) < 1e-9, str(e["usd"]))
    check("local: tokens summed", e["tokens"] == 150)
    check("local: not remote", e["remote"] is False)
    # usd_per_kwh=0 -> energy tracked, $ stays 0 (energy-only local accounting)
    m0 = cost.CostModel(gpu_watts=360.0, usd_per_kwh=0.0)
    check("local: zero kwh-price -> $0 but energy>0",
          m0.estimate(elapsed_s=10.0)["usd"] == 0.0 and m0.estimate(elapsed_s=10.0)["energy_wh"] > 0)


def t_remote_dollar():
    m = cost.CostModel(remote_usd_per_mtok=5.0)
    # 1,000,000 tokens at $5/Mtok -> $5.00 ; remote energy attributed to provider (0)
    e = m.estimate(lane="remote-gpt", is_remote=True, prompt_tokens=600_000, completion_tokens=400_000)
    check("remote: $/Mtok", abs(e["usd"] - 5.0) < 1e-9, str(e["usd"]))
    check("remote: zero local energy", e["energy_wh"] == 0.0)
    # per-call rate override wins
    e2 = m.estimate(is_remote=True, prompt_tokens=1_000_000, usd_per_mtok=2.0)
    check("remote: per-call rate override", abs(e2["usd"] - 2.0) < 1e-9, str(e2["usd"]))


def t_ledger():
    m = cost.CostModel(gpu_watts=360.0, usd_per_kwh=1.0)
    L = cost.CostLedger()
    L.record(m.estimate(lane="dgpu", elapsed_s=10.0, completion_tokens=50))   # 1 Wh, $0.001
    L.record(m.estimate(lane="dgpu", elapsed_s=20.0, completion_tokens=70))   # 2 Wh, $0.002
    L.record(m.estimate(lane="cpu", elapsed_s=5.0, completion_tokens=10))     # 0.5 Wh
    snap = L.snapshot()
    check("ledger: dispatch count", snap["dispatches"] == 3)
    check("ledger: total energy", abs(snap["energy_wh"] - 3.5) < 1e-3, str(snap["energy_wh"]))
    check("ledger: per-lane split", snap["by_lane"]["dgpu"]["n"] == 2 and snap["by_lane"]["cpu"]["n"] == 1)
    check("ledger: tokens summed", snap["tokens"] == 130)
    # budget
    check("ledger: remaining under budget", abs(L.remaining(1.0) - (1.0 - snap["usd"])) < 1e-9)
    check("ledger: no budget -> inf", L.remaining(None) == float("inf"))
    check("ledger: over_budget true past ceiling", L.over_budget(0.0001) is True)
    check("ledger: empty estimate ignored", (L.record({}), L.snapshot()["dispatches"])[1] == 3)


def main():
    t_local_energy()
    t_remote_dollar()
    t_ledger()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
