# AI-hint: Stdlib offline unit tests for mios_pipe.observability.drift_monitor -- the Jensen-Shannon Goodhart alarm (CONS-02). No network / no DB / no ...
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Stdlib offline unit tests for the Jensen-Shannon drift monitor (CONS-02)."""

import sys

from mios_pipe.observability import drift_monitor as M

_fails = 0


def check(name, cond):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}")


def t_histogram():
    h = M.histogram(["yes", "yes", "no", "no"])
    check("histogram: even split", h == {"yes": 0.5, "no": 0.5})
    check("histogram: sums to 1.0", abs(sum(h.values()) - 1.0) < 1e-12)
    check("histogram: empty input -> {} (not a uniform window)",
          M.histogram([]) == {})
    check("histogram: labels are stringified",
          M.histogram([1, 1, 2]) == {"1": 2 / 3, "2": 1 / 3})


def t_jsd_bounds():
    p = {"yes": 0.7, "no": 0.3}
    check("jsd: identical -> 0.0", M.jensen_shannon(p, p) == 0.0)
    check("jsd: disjoint support -> 1.0",
          M.jensen_shannon({"a": 1.0}, {"b": 1.0}) == 1.0)
    d = M.jensen_shannon(p, {"yes": 0.3, "no": 0.7})
    check("jsd: partial shift is strictly inside the bounds", 0.0 < d < 1.0)
    check("jsd: symmetric",
          abs(M.jensen_shannon(p, {"yes": 0.1, "no": 0.9})
              - M.jensen_shannon({"yes": 0.1, "no": 0.9}, p)) < 1e-12)


def t_jsd_monotone():
    base = {"yes": 0.5, "no": 0.5}
    near = M.jensen_shannon(base, {"yes": 0.6, "no": 0.4})
    far = M.jensen_shannon(base, {"yes": 0.95, "no": 0.05})
    check("jsd: a bigger shift scores higher", far > near)


def t_jsd_degenerate():
    check("jsd: empty baseline -> 0.0 (nothing to compare)",
          M.jensen_shannon({}, {"a": 1.0}) == 0.0)
    check("jsd: empty live -> 0.0", M.jensen_shannon({"a": 1.0}, {}) == 0.0)
    check("jsd: all-zero weights -> 0.0",
          M.jensen_shannon({"a": 0.0}, {"a": 0.0}) == 0.0)
    check("jsd: negative and non-numeric weights are dropped",
          M.jensen_shannon({"a": 1.0, "b": -5.0, "c": "junk"},
                           {"a": 1.0}) == 0.0)
    check("jsd: unnormalized input is normalized first",
          abs(M.jensen_shannon({"a": 70, "b": 30}, {"a": 0.7, "b": 0.3})) < 1e-12)


def t_compare_alerting():
    base = {"verdict": {"satisfied": 0.9, "unsatisfied": 0.1}}
    same = {"verdict": {"satisfied": 0.9, "unsatisfied": 0.1}}
    r = M.compare(base, same, threshold=0.2)
    check("compare: no shift -> not alerting", r["alerting"] is False)
    check("compare: no shift -> divergence 0.0", r["max_divergence"] == 0.0)

    flipped = {"verdict": {"satisfied": 0.1, "unsatisfied": 0.9}}
    r = M.compare(base, flipped, threshold=0.2)
    check("compare: flipped verdicts -> alerting", r["alerting"] is True)
    check("compare: names the worst axis", r["max_axis"] == "verdict")
    check("compare: axis carries its own flag",
          r["axes"]["verdict"]["alerting"] is True)
    check("compare: is_alerting agrees", M.is_alerting(r) is True)

    r = M.compare(base, flipped, threshold=0.99)
    check("compare: a high threshold suppresses the alarm", r["alerting"] is False)
    check("compare: suppressed alarm still reports the divergence",
          r["max_divergence"] > 0.0)


def t_compare_incomparable():
    base = {"verdict": {"satisfied": 1.0}, "intent": {"chat": 1.0}}
    live = {"verdict": {"unsatisfied": 1.0}}
    r = M.compare(base, live, threshold=0.1)
    check("compare: an axis missing from live is compared=False",
          r["axes"]["intent"]["compared"] is False)
    check("compare: a missing axis never alerts",
          r["axes"]["intent"]["alerting"] is False)
    check("compare: the present axis still alerts",
          r["axes"]["verdict"]["alerting"] is True)


def t_compare_thin_window():
    base = {"verdict": {"satisfied": 1.0}}
    live = {"verdict": {"unsatisfied": 1.0}}
    r = M.compare(base, live, threshold=0.1, min_samples=50,
                  live_counts={"verdict": 3})
    check("compare: a thin live window is not evidence of drift",
          r["alerting"] is False)
    check("compare: thin window is marked uncompared",
          r["axes"]["verdict"]["compared"] is False)

    r = M.compare(base, live, threshold=0.1, min_samples=50,
                  live_counts={"verdict": 500})
    check("compare: a full window alerts normally", r["alerting"] is True)


def t_is_alerting_tolerates_junk():
    check("is_alerting: empty report -> False", M.is_alerting({}) is False)
    check("is_alerting: malformed report -> False", M.is_alerting(None) is False)


def _server_or_skip():
    """Import server.py for the route-level cases, or None on a bare checkout
    without fastapi -- the pure-math cases above still run either way.

    Stubs only `websockets` (the portal terminal proxy imports it at module
    load and no route here touches it), exactly as test_mios_approutes does."""
    import types  # noqa: PLC0415
    ws = types.ModuleType("websockets")
    wse = types.ModuleType("websockets.exceptions")
    wse.ConnectionClosed = type("ConnectionClosed", (Exception,), {})
    ws.exceptions = wse
    sys.modules.setdefault("websockets", ws)
    sys.modules.setdefault("websockets.exceptions", wse)
    for sub in ("legacy", "legacy.client", "client", "sync", "sync.client",
                "asyncio", "asyncio.client"):
        sys.modules.setdefault("websockets." + sub,
                               types.ModuleType("websockets." + sub))
    try:
        import server  # noqa: PLC0415
        return server
    except Exception:  # noqa: BLE001
        return None


def t_route_axis_extractors():
    srv = _server_or_skip()
    if srv is None:
        print("skip - route cases (fastapi absent)")
        return
    rows = [
        {"kind": "user_query_satisfied", "payload": {"refine_intent": "chat"}},
        {"kind": "user_query_satisfied", "payload": '{"refine_intent": "agent"}'},
        {"kind": "user_query_unsatisfied", "payload": {"refine_intent": ""}},
    ]
    dist, n = srv._drift_live_window(rows, "verdict")
    check("route: verdict axis counts every row", n == 3)
    check("route: verdict axis splits 2/1",
          abs(dist["user_query_satisfied"] - 2 / 3) < 1e-12)

    dist, n = srv._drift_live_window(rows, "intent")
    check("route: intent axis skips the empty label", n == 2)
    check("route: intent axis parses a JSON-string payload",
          set(dist) == {"chat", "agent"})

    dist, n = srv._drift_live_window(rows, "no_such_axis")
    check("route: an axis with no extractor yields nothing", (dist, n) == ({}, 0))


def t_route_payload_normalization():
    srv = _server_or_skip()
    if srv is None:
        return
    check("route: dict payload passes through",
          srv._drift_payload({"payload": {"a": 1}}) == {"a": 1})
    check("route: JSON-string payload is parsed",
          srv._drift_payload({"payload": '{"a": 1}'}) == {"a": 1})
    check("route: unparseable payload -> {}",
          srv._drift_payload({"payload": "not json"}) == {})
    check("route: missing payload -> {}", srv._drift_payload({}) == {})


def t_route_gate_closed():
    srv = _server_or_skip()
    if srv is None:
        return
    check("route: the monitor ships disabled",
          srv.DRIFT_MONITOR_ENABLED is False)
    import asyncio as _a
    body = _a.run(srv.v1_drift()).body.decode()
    check("route: disabled -> enabled:false, no alert",
          '"enabled":false' in body.replace(" ", "")
          and '"alerting":false' in body.replace(" ", ""))


def main():
    t_histogram()
    t_jsd_bounds()
    t_jsd_monotone()
    t_jsd_degenerate()
    t_compare_alerting()
    t_compare_incomparable()
    t_compare_thin_window()
    t_is_alerting_tolerates_junk()
    t_route_axis_extractors()
    t_route_payload_normalization()
    t_route_gate_closed()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
