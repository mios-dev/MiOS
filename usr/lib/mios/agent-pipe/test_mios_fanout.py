#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_fanout (council/swarm fan-out SELECTION; de-hardcoded to model-driven relevance). Pure stdlib, no server.py/DB/network/pytest. Verifies the DETERMINISTIC parts (eligibility filter: opt-out/outage/research-gate; council-equal-weight fallback: sub-lane-diverse + endpoint dedup + cap; force_council all-eligible; council-mode cap) AND the MODEL-DRIVEN default path: _pick_fanout_agents honors the model's chosen subset, degrades OPEN to council-equal-weight when the model returns None, and _model_select parses the micro-model's JSON name array + validates names ⊆ candidates + caps (a fake httpx returns canned content -- NO real network). Proves there is no hand-coded relevance scorer left: relevance is the model's call, width is bounded by the caps.
# AI-related: ./mios_fanout.py
# AI-functions: check, setup, t_eligible, t_council_fallback, t_force_council, t_council_mode, t_default_model, t_default_degrade, t_model_select, main
"""Unit tests for mios_fanout (model-driven selection + deterministic bounds)."""

import asyncio
import json
import sys
import types

import mios_fanout as f

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


REG = {
    "primary": {"lane": "gpu", "role": "general", "endpoint": "e0", "skill_tags": ["chat"]},
    "a":       {"lane": "cpu", "role": "researcher", "endpoint": "e1", "strengths": ["web research"], "skill_tags": ["web", "search"]},
    "b":       {"lane": "gpu", "role": "coder", "endpoint": "e2", "skill_tags": ["code"]},
    "c":       {"lane": "cpu", "role": "telemetry", "endpoint": "e3", "fanout": False, "skill_tags": ["system"]},
    "d":       {"lane": "cpu", "research_only": True, "endpoint": "e4", "skill_tags": ["deep"]},
}


def setup(dispatch_cfg):
    """Inject a synthetic registry + deterministic helper stubs (no server)."""
    f.configure(
        agent_registry=REG, dispatch_cfg=dispatch_cfg,
        depth_exhausted=lambda: False, dispatch_depth=lambda: 0,
        lane_sem_key=lambda cfg: (cfg or {}).get("lane", "gpu"),
        dedup_pool_by_target=lambda names: names,  # identity (distinct endpoints)
        over_global_ceiling=lambda: False,
        agent_lane=lambda cfg: (cfg or {}).get("lane", "gpu"),
        agent_skill_tags=lambda cfg: (cfg or {}).get("skill_tags", []),
        max_dispatch_depth=2, council_max_default=4, admit_enable=False)


def t_eligible():
    setup({"enable": True, "fanout_max": 3})
    names = lambda lst: sorted(n for n, _ in lst)
    check("eligible: opt-out + research-only excluded", names(f._eligible_candidates("primary", None, False)) == ["a", "b"])
    check("eligible: research turn includes research_only", names(f._eligible_candidates("primary", None, True)) == ["a", "b", "d"])
    check("eligible: outage prune by live set", names(f._eligible_candidates("primary", {"a"}, False)) == ["a"])
    check("eligible: primary itself excluded", "primary" not in names(f._eligible_candidates("primary", None, True)))


def t_council_fallback():
    setup({"enable": True, "fanout_max": 3})
    cands = f._eligible_candidates("primary", None, False)  # a(cpu), b(gpu)
    sel = f._council_fallback("primary", cands, want=2)
    check("council_fallback: lane-diverse first (cpu before gpu vs gpu primary)", [n for n, _ in sel] == ["a", "b"])
    check("council_fallback: cap honored", len(f._council_fallback("primary", cands, want=1)) == 1)


def t_force_council():
    setup({"enable": True, "fanout_max": 3})
    sel = asyncio.run(f._pick_fanout_agents("primary", {"refined_text": "x"}, force_council=True))
    check("force_council: every eligible (research-only out on non-research)", sorted(n for n, _ in sel) == ["a", "b"])
    sel_r = asyncio.run(f._pick_fanout_agents("primary", {"refined_text": "x"}, force_council=True, include_research=True))
    check("force_council: research turn adds research_only", sorted(n for n, _ in sel_r) == ["a", "b", "d"])


def t_council_mode():
    setup({"enable": True, "fanout_max": 3, "mode": "council"})
    sel = asyncio.run(f._pick_fanout_agents("primary", {"refined_text": "x"}))
    check("council mode: equal-weight eligible, capped", sorted(n for n, _ in sel) == ["a", "b"])


def t_default_model():
    # default (relevance) path -> model-driven: the model's chosen subset is honored.
    setup({"enable": True, "fanout_max": 3, "mode": "relevance", "fanout_select_mode": "model"})
    orig = f._model_select
    async def _stub(corpus, candidates, want):
        return ["b"]
    f._model_select = _stub
    try:
        sel = asyncio.run(f._pick_fanout_agents("primary", {"refined_text": "write code"}))
        check("default model: honors model-chosen subset", [n for n, _ in sel] == ["b"])
    finally:
        f._model_select = orig


def t_default_degrade():
    # model returns None -> degrade OPEN to council-equal-weight (never primary-only).
    setup({"enable": True, "fanout_max": 3, "mode": "relevance", "fanout_select_mode": "model"})
    orig = f._model_select
    async def _none(corpus, candidates, want):
        return None
    f._model_select = _none
    try:
        sel = asyncio.run(f._pick_fanout_agents("primary", {"refined_text": "anything"}))
        check("default degrade-open: council fallback engages secondaries", sorted(n for n, _ in sel) == ["a", "b"])
    finally:
        f._model_select = orig


def _fake_httpx(content, status=200):
    """A minimal httpx stand-in: AsyncClient(...).post() -> resp.json() canned."""
    class _Resp:
        status_code = status
        def json(self):
            return {"choices": [{"message": {"content": content}}]}
    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _Resp()
    return types.SimpleNamespace(AsyncClient=_Client)


def t_model_select():
    setup({"enable": True, "fanout_max": 3, "mode": "relevance", "fanout_select_mode": "model"})
    cands = f._eligible_candidates("primary", None, False)  # a, b
    orig = f.httpx
    # model returns a name array with one valid + one hallucinated name -> validated
    f.httpx = _fake_httpx('Here you go: ["b", "ghost"]')
    try:
        sel = asyncio.run(f._model_select("write some code", cands, want=2))
        check("model_select: validates names (ghost dropped, b kept)", sel == ["b"], str(sel))
        check("model_select: caps at want", len(asyncio.run(f._model_select("x", cands, want=1))) <= 1)
        # off-mode short-circuits (no model call attempted)
        setup({"enable": True, "fanout_max": 3, "mode": "relevance", "fanout_select_mode": "off"})
        check("model_select: off -> None", asyncio.run(f._model_select("x", cands, want=2)) is None)
        # non-200 -> None (degrade-open)
        setup({"enable": True, "fanout_max": 3, "mode": "relevance", "fanout_select_mode": "model"})
        f.httpx = _fake_httpx("nope", status=503)
        check("model_select: non-200 -> None", asyncio.run(f._model_select("x", cands, want=2)) is None)
    finally:
        f.httpx = orig


# ── FED-G7 (T-051): route on the FULL published AgentCard skills[], flag-gated. ──
# A federated peer publishes rich skills (name/description/tags); the peer
# registration collapses them to strength-token ids. With ROUTE_ON_CARD_SKILLS the
# full skills[] (stored as cfg["card_skills"]) is folded into the relevance corpus
# so the model routes on the ADVERTISED skill, not just token proximity.
_CARD_SKILL = {"id": "cr", "name": "Code Review",
               "description": "reviews source code for correctness and bugs",
               "tags": ["code-review"]}


def t_card_skills_corpus():
    # OFF -> byte-identical (published skill text absent); ON -> name+desc+tags folded in.
    setup({"enable": True, "fanout_max": 3})
    cfg = {"role": "general", "strengths": ["chat"], "skill_tags": ["chat"],
           "card_skills": [_CARD_SKILL]}
    f.ROUTE_ON_CARD_SKILLS = False
    off = f._agent_card("peer", cfg)
    check("card OFF: byte-identical (no published-skill text)",
          "code-review" not in off and "reviews source code" not in off, off)
    f.ROUTE_ON_CARD_SKILLS = True
    on = f._agent_card("peer", cfg)
    check("card ON: full published skill name/description/tags folded into corpus",
          ("code-review" in on and "Code Review" in on
           and "reviews source code" in on), on)
    check("card ON: OFF card is a strict prefix (purely additive)", on.startswith(off), on)
    f.ROUTE_ON_CARD_SKILLS = False


def _fake_httpx_cardpick(phrase):
    """A body-inspecting httpx stand-in that simulates a SEMANTIC selector: it reads
    the agent cards from the request and returns the names whose card ADVERTISES the
    phrase. So the winner is decided by what each card actually says -- proving the
    published skill (only in the corpus when ROUTE_ON_CARD_SKILLS is on) is decisive."""
    class _Resp:
        status_code = 200
        def __init__(self, names): self._names = names
        def json(self):
            return {"choices": [{"message": {"content": json.dumps(self._names)}}]}
    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, **k):
            user = ((json or {}).get("messages") or [{}, {}])[1].get("content", "")
            picked = []
            for line in user.splitlines():
                s = line.strip()
                if s.startswith("- ") and phrase in s.lower():
                    picked.append(s[2:].split(" -- ", 1)[0].strip())
            return _Resp(picked)
    return types.SimpleNamespace(AsyncClient=_Client)


# tokenmatch: strengths lexically overlap the task ("code", "review") but it does NOT
# publish a code-review skill. skillcard: strengths are unrelated ("chat") but it
# publishes the code-review skill. They CONFLICT -- a strength-token scorer favours
# tokenmatch; card-skills routing must pick skillcard.
_CS_REG = {
    "primary":    {"lane": "gpu", "role": "general", "endpoint": "e0", "skill_tags": ["chat"]},
    "tokenmatch": {"lane": "gpu", "role": "general", "endpoint": "e1",
                   "strengths": ["code", "review"], "skill_tags": ["code", "review"]},
    "skillcard":  {"lane": "gpu", "role": "general", "endpoint": "e2",
                   "strengths": ["chat"], "skill_tags": ["chat"],
                   "card_skills": [_CARD_SKILL]},
}


def _cs_setup(*, db=None):
    f.configure(
        agent_registry=_CS_REG,
        dispatch_cfg={"enable": True, "fanout_max": 3, "mode": "relevance",
                      "fanout_select_mode": "model"},
        depth_exhausted=lambda: False, dispatch_depth=lambda: 0,
        lane_sem_key=lambda cfg: (cfg or {}).get("lane", "gpu"),
        dedup_pool_by_target=lambda names: names,
        over_global_ceiling=lambda: False,
        agent_lane=lambda cfg: (cfg or {}).get("lane", "gpu"),
        agent_skill_tags=lambda cfg: (cfg or {}).get("skill_tags", []),
        max_dispatch_depth=2, council_max_default=4, admit_enable=False,
        route_on_card_skills=True,
        **(db or {}))


def t_card_skills_route():
    _cs_setup()
    f.ROUTE_ON_CARD_SKILLS = True
    orig = f.httpx
    f.httpx = _fake_httpx_cardpick("code-review")
    try:
        sel = asyncio.run(f._pick_fanout_agents(
            "primary", {"refined_text": "please code-review this pull request"}))
        names = [n for n, _ in sel]
        check("card-skills ON: published-skill agent wins over strength-token proximity",
              names == ["skillcard"], str(names))
        # Same conflict, gate OFF: skillcard no longer advertises the skill in its
        # card, so the semantic selector no longer prefers it -> the skill-card no
        # longer beats the token-match agent (the corpus, hence the routing, differs).
        f.ROUTE_ON_CARD_SKILLS = False
        sel_off = asyncio.run(f._pick_fanout_agents(
            "primary", {"refined_text": "please code-review this pull request"}))
        check("card-skills OFF: no code-review edge -> skillcard does NOT win",
              [n for n, _ in sel_off] != ["skillcard"], str(sel_off))
    finally:
        f.httpx = orig
        f.ROUTE_ON_CARD_SKILLS = False


def t_route_event():
    captured = []
    _cs_setup(db={
        "db_create": lambda table, fields, now_fields=None: {"table": table, "fields": fields},
        "db_post": lambda row: row,
        "db_fire": lambda row: captured.append(row)})
    f.ROUTE_ON_CARD_SKILLS = True
    orig = f.httpx
    f.httpx = _fake_httpx_cardpick("code-review")
    try:
        asyncio.run(f._pick_fanout_agents(
            "primary", {"refined_text": "please code-review this pull request"}))
        rows = [r for r in captured
                if (r.get("fields") or {}).get("kind") == "fanout_route"]
        check("route event: fan-out routing decision written to the event table", len(rows) == 1,
              str(captured))
        if rows:
            payload = (rows[0]["fields"].get("payload") or {})
            check("route event: payload carries the chosen secondaries",
                  payload.get("secondaries") == ["skillcard"], str(payload))
    finally:
        f.httpx = orig
        f.ROUTE_ON_CARD_SKILLS = False
        f._db_create = f._db_post = f._db_fire = None


def main():
    t_eligible()
    t_council_fallback()
    t_force_council()
    t_council_mode()
    t_default_model()
    t_default_degrade()
    t_model_select()
    t_card_skills_corpus()
    t_card_skills_route()
    t_route_event()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
