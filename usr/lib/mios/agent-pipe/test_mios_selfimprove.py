# AI-hint: Standalone unit test for mios_selfimprove (#64 self-improve analysis): per-tool failure-rate + slow-tool + unreliable-peer findings, min-samples gating, severity ranking, and clean-input -> no findings.
# AI-related: mios_selfimprove
# AI-functions: _check, t_failing, t_min_samples, t_slow, t_peer, t_clean, t_ranking, main
"""Standalone unit test for mios_selfimprove (#64 self-improvement analyzer).

Pure stdlib + the sibling module only -- no server.py / DB. Proves the analyzer
surfaces the right findings from outcome records and does not over-react to thin
samples.

Run:  python test_mios_selfimprove.py
"""

import sys

import mios_selfimprove as S

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _calls(tool, n, fails, latency=100):
    out = []
    for i in range(n):
        out.append({"tool": tool, "success": i >= fails,
                    "exit_code": 0 if i >= fails else 1, "latency_ms": latency})
    return out


def t_failing() -> None:
    rep = S.analyze(_calls("flaky", 10, 5))  # 50% fail, 10 samples
    kinds = [(f["kind"], f["subject"]) for f in rep["findings"]]
    _check("failing: flagged", ("failing_tool", "flaky") in kinds, str(kinds))
    f = next(f for f in rep["findings"] if f["subject"] == "flaky")
    _check("failing: severity medium at 50%", f["severity"] == "medium", f["severity"])
    sev = next(f for f in S.analyze(_calls("dead", 10, 8))["findings"]
               if f["subject"] == "dead")
    _check("failing: severity high at 80%", sev["severity"] == "high", sev["severity"])


def t_min_samples() -> None:
    # 2 calls, both fail -> below min_samples -> NOT flagged (no over-reaction)
    rep = S.analyze(_calls("rare", 2, 2))
    _check("min-samples: thin sample not flagged",
           not any(f["kind"] == "failing_tool" for f in rep["findings"]))


def t_slow() -> None:
    rep = S.analyze(_calls("slowpoke", 6, 0, latency=20000), slow_ms=10000)
    _check("slow: flagged", any(f["kind"] == "slow_tool"
                                and f["subject"] == "slowpoke" for f in rep["findings"]))


def t_peer() -> None:
    rep = S.analyze([], reputation={"badpeer": {"score": 0.2, "ok": 1, "bad": 9},
                                    "freshpeer": {"score": 0.5, "ok": 0, "bad": 0}})
    subs = [f["subject"] for f in rep["findings"] if f["kind"] == "unreliable_peer"]
    _check("peer: unreliable flagged", "badpeer" in subs, str(subs))
    _check("peer: fresh/neutral NOT flagged", "freshpeer" not in subs, str(subs))


def t_clean() -> None:
    rep = S.analyze(_calls("good", 20, 0, latency=50))
    _check("clean: no findings on a healthy tool", rep["findings"] == [], str(rep["findings"]))
    _check("clean: counts reported", rep["tools_analyzed"] == 1 and rep["samples"] == 20)


def t_ranking() -> None:
    calls = _calls("dead", 10, 9) + _calls("slowpoke", 6, 0, latency=20000)
    rep = S.analyze(calls, slow_ms=10000)
    sevs = [f["severity"] for f in rep["findings"]]
    _check("ranking: high before low", sevs == sorted(sevs, key={"high":0,"medium":1,"low":2}.get),
           str(sevs))


def main() -> int:
    for t in (t_failing, t_min_samples, t_slow, t_peer, t_clean, t_ranking):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
