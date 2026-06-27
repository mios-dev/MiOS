# AI-hint: Standalone unit test for mios_goap (#53 deterministic GOAP planner): already-satisfied, single + multi-step chains, precondition gating, unreachable, min-cost optimality, determinism, and action-set validation.
# AI-related: mios_goap
# AI-functions: _check, t_trivial, t_chain, t_gating, t_unreachable, t_optimal, t_deterministic, t_validate, t_lane_wrappers, main
"""Standalone unit test for mios_goap (WS / #53 GOAP planner lane).

Pure stdlib + the sibling module only -- no server.py. Proves the planner finds
correct, minimum-cost, reproducible plans and reports unreachable goals.

Run:  python test_mios_goap.py
"""

import sys

import mios_goap as G

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# A canonical MiOS action set: launch -> type -> verify, with preconditions.
ACTIONS = [
    {"name": "open_app", "pre": {}, "eff": {"app_open": True}, "cost": 1},
    {"name": "type_text", "pre": {"app_open": True}, "eff": {"text_entered": True}, "cost": 1},
    {"name": "verify", "pre": {"text_entered": True}, "eff": {"verified": True}, "cost": 1},
]


def t_trivial() -> None:
    _check("trivial: goal already met -> []",
           G.plan({"verified": True}, {"verified": True}, ACTIONS) == [])


def t_chain() -> None:
    p = G.plan({}, {"verified": True}, ACTIONS)
    _check("chain: full launch->type->verify",
           p == ["open_app", "type_text", "verify"], str(p))


def t_gating() -> None:
    # Goal needs text_entered; from empty, open_app must precede type_text.
    p = G.plan({}, {"text_entered": True}, ACTIONS)
    _check("gating: open precedes type", p == ["open_app", "type_text"], str(p))
    # If the app is already open, the plan skips open_app.
    p2 = G.plan({"app_open": True}, {"text_entered": True}, ACTIONS)
    _check("gating: skips already-met precondition", p2 == ["type_text"], str(p2))


def t_unreachable() -> None:
    # No action produces "deployed" -> unreachable.
    _check("unreachable: returns None",
           G.plan({}, {"deployed": True}, ACTIONS) is None)


def t_optimal() -> None:
    # Two routes to the goal; the planner must pick the cheaper.
    acts = [
        {"name": "cheap", "pre": {}, "eff": {"goal": True}, "cost": 1},
        {"name": "stepA", "pre": {}, "eff": {"mid": True}, "cost": 1},
        {"name": "stepB", "pre": {"mid": True}, "eff": {"goal": True}, "cost": 1},
    ]
    p = G.plan({}, {"goal": True}, acts)
    _check("optimal: picks min-cost route", p == ["cheap"], str(p))


def t_deterministic() -> None:
    a = G.plan({}, {"verified": True}, ACTIONS)
    b = G.plan({}, {"verified": True}, ACTIONS)
    _check("deterministic: same inputs -> same plan", a == b, f"{a} vs {b}")
    _check("budget: exhausted -> None (no hang)",
           G.plan({}, {"verified": True}, ACTIONS, max_expansions=0) is None)


def t_validate() -> None:
    _check("validate: clean set -> no problems", G.validate_actions(ACTIONS) == [])
    bad = [{"name": "x"}, {"name": "x", "eff": {"a": 1}}, {"eff": {"b": 2}}]
    probs = G.validate_actions(bad)
    _check("validate: flags no-eff / dup / no-name", len(probs) >= 3, str(probs))


# Synthetic (non-dictionary) verb + fact tokens for the config-bound lane wrappers
# so the test exercises the SSOT-read path with no baked example words.
SACTS = [
    {"name": "qx_zud", "pre": {}, "eff": {"fz_1": True}, "cost": 1},
    {"name": "qx_vop", "pre": {"fz_1": True}, "eff": {"fz_2": True}, "cost": 1},
]


def t_lane_wrappers() -> None:
    # The wrappers read mios.toml [goap] via mios_config._toml_section; monkeypatch
    # it so the lane's config is controlled (no dependency on the live mios.toml).
    orig = G._toml_section
    try:
        # Lane off (no mode) -> disabled; plan/actions degrade cleanly.
        G._toml_section = lambda s: {} if s == "goap" else orig(s)
        _check("lane: default off -> _goap_enabled False", G._goap_enabled() is False)
        _check("lane: off -> _goap_plan None", G._goap_plan({"fz_2": True}) is None)
        _check("lane: off -> _goap_actions []", G._goap_actions() == [])

        # Lane on (accepted mode) + valid synthetic action set -> plan resolves.
        cfg = {"mode": "available", "actions": SACTS}
        G._toml_section = lambda s: cfg if s == "goap" else orig(s)
        _check("lane: accepted mode -> _goap_enabled True", G._goap_enabled() is True)
        _check("lane: _goap_actions passes the SSOT list through", G._goap_actions() == SACTS)
        plan = G._goap_plan({"fz_2": True})
        _check("lane: enabled plan resolves the synthetic chain",
               plan == ["qx_zud", "qx_vop"], str(plan))

        # Enabled but invalid action set (no effects) -> degrade-open to None.
        invalid = {"mode": "on", "actions": [{"name": "qx_nul"}]}
        G._toml_section = lambda s: invalid if s == "goap" else orig(s)
        _check("lane: invalid actions -> None (degrade-open)",
               G._goap_plan({"fz_2": True}) is None)

        # actions not a list -> [].
        G._toml_section = lambda s: {"actions": "qx_str"} if s == "goap" else orig(s)
        _check("lane: non-list actions -> []", G._goap_actions() == [])
    finally:
        G._toml_section = orig


def main() -> int:
    for t in (t_trivial, t_chain, t_gating, t_unreachable, t_optimal,
              t_deterministic, t_validate, t_lane_wrappers):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
