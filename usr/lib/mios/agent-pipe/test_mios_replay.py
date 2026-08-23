#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for the T-225 run-template REPLAY path -- the pure matcher (mios_pipe.routing.replay), the...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_replay_py.md

"""Unit tests for intent-keyed run-template replay (T-225)."""

import asyncio
import contextvars
import os
import sys

from mios_pipe.routing import replay as R

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


A = "search the web for the latest linux kernel CVEs and summarise the top three"


def t_keying():
    check("key: word ORDER does not change the key",
          R.intent_key(A) == R.intent_key(
              "summarise the top three latest linux kernel CVEs and search the web"))
    check("key: punctuation and case do not change the key",
          R.intent_key(A) == R.intent_key(
              "SEARCH the WEB for the LATEST, linux kernel CVEs -- and summarise the top three!"))
    check("key: a different request gets a different key",
          R.intent_key(A) != R.intent_key("what is the weather in Paris tomorrow"))
    check("key: an empty turn keys to nothing", R.intent_key("") == "")
    check("key: an all-stopword turn keys to nothing", R.intent_key("what is the of and") == "")
    check("tokens: stopwords are dropped", "the" not in R.normalize_tokens(A))
    check("tokens: sorted + unique",
          R.normalize_tokens("beta alpha beta") == ("alpha", "beta"))


def t_similarity():
    check("sim: identical sets score 1.0",
          R.similarity(("a", "b"), ("b", "a")) == 1.0)
    check("sim: disjoint sets score 0.0", R.similarity(("a",), ("b",)) == 0.0)
    check("sim: two EMPTY sets score 0.0, not a perfect 1.0",
          R.similarity((), ()) == 0.0)
    check("sim: one empty set scores 0.0", R.similarity(("a",), ()) == 0.0)
    check("sim: half overlap scores 1/3 (Jaccard, not overlap-coefficient)",
          abs(R.similarity(("a", "b"), ("b", "c")) - (1 / 3)) < 1e-9)


def _tpl(intent, nodes=1):
    return {"intent": intent, "intent_key": R.intent_key(intent),
            "dag": {"nodes": [{"id": i + 1, "tool": "web_search"} for i in range(nodes)]}}


def t_match():
    T = [_tpl(A, nodes=2)]
    tpl, score, why = R.match_template(A, T, 0.85)
    check("match: an exact intent key wins outright", tpl is not None and score == 1.0, why)

    tpl, score, why = R.match_template("what is the price of a bicycle in Amsterdam", T, 0.85)
    check("match: an unrelated turn does NOT match", tpl is None and score == 0.0, why)

    tpl, score, why = R.match_template("search the web for linux kernel CVEs", T, 0.85)
    check("match: a merely PARTIAL overlap falls back rather than replaying",
          tpl is None and 0.0 < score < 0.85, why)
    tpl, score, why = R.match_template("search the web for linux kernel CVEs", T, 0.5)
    check("match: the same turn DOES match once the threshold is lowered",
          tpl is not None and score >= 0.5, why)

    check("match: an empty turn matches nothing",
          R.match_template("", T, 0.85)[0] is None)
    check("match: an empty template list matches nothing",
          R.match_template(A, [], 0.85)[0] is None)
    check("match: a row with NO dag never consumes the match",
          R.match_template(A, [{"intent": A, "intent_key": R.intent_key(A), "dag": {}}],
                           0.85)[0] is None)
    check("match: a row with an intent but no stored key still matches by intent",
          R.match_template(A, [{"intent": A, "dag": {"nodes": [{"id": 1}]}}], 0.85)[1] == 1.0)
    check("match: a non-numeric threshold falls back to the default, not a crash",
          R.match_template("search the web for linux kernel CVEs", T, "bogus")[0] is None)
    check("match: the score is returned even on a miss, so the decision is auditable",
          R.match_template("search the web for linux kernel CVEs", T, 0.85)[1] > 0)


def t_capture_roundtrip():
    """A captured template must be matchable by the turn that produced it --
    the whole feature is dead if the capture stores no usable intent key."""
    from mios_pipe.routing import run_template as RT
    rows = []
    RT.configure(run_template_enable=True, pg_primary=True,
                 pg_mirror=lambda t, r: rows.append(r),
                 db_create=lambda *a, **k: "x", db_post=lambda s: s,
                 db_fire=lambda x: None)
    RT._capture_run_template(
        {"summary": "s", "intent": A, "nodes": [{"id": 1, "tool": "web_search"}]}, "sess1")
    check("capture: a row is written", len(rows) == 1)
    check("capture: it carries a NON-EMPTY intent key",
          bool(rows and rows[0].get("intent_key")), str(rows[:1]))
    check("capture: the captured row matches its own turn",
          bool(rows) and R.match_template(A, [dict(rows[0])], 0.85)[1] == 1.0)
    rows.clear()
    RT._capture_run_template({"summary": "s", "nodes": []}, "sess1")
    check("capture: an empty DAG is not stored", rows == [])


def t_planner_replay():
    """The Done-When, counted at the HTTP layer: a repeat spends ZERO planning
    calls; a fuzzy variant spends one; the default flag spends one."""
    try:
        import httpx
    except ModuleNotFoundError:                      # pragma: no cover
        print("[SKIP] planner replay: httpx absent")
        return
    import mios_planner as P

    calls = []

    class _Counting:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, **kw):
            calls.append(url)
            return httpx.Response(200, json={"choices": [{"message": {"content":
                '{"action":"decompose","summary":"fresh","nodes":['
                '{"id":1,"tool":"web_search","args":{}},'
                '{"id":2,"tool":"web_search","args":{},"deps":[1]}]}'}}]},
                request=httpx.Request("POST", url))

    real_httpx = P.httpx
    P.httpx = type("H", (), {"AsyncClient": _Counting, "Timeout": httpx.Timeout})
    prev_build = P._build_dispatch_cmd
    P.configure(replay_templates=lambda limit=50: _rows(),
                routed_domain_var=contextvars.ContextVar("d", default=None),
                is_action_domain=lambda d: False,
                build_dispatch_cmd=lambda tool, args: "echo ok")
    enabled, chars, words = P.PLANNER_ENABLED, P.PLANNER_SHORT_PROMPT_CHARS, P.PLANNER_SHORT_PROMPT_WORDS
    P.PLANNER_ENABLED, P.PLANNER_SHORT_PROMPT_CHARS, P.PLANNER_SHORT_PROMPT_WORDS = True, 0, 0

    async def _rows(limit=50):
        return [_tpl(A, nodes=2)]

    try:
        os.environ["MIOS_RUN_TEMPLATE_REPLAY"] = "true"
        calls.clear()
        dag = asyncio.run(P.decompose_intent(A))
        check("planner: a repeated intent spends ZERO planning calls", len(calls) == 0, str(calls))
        check("planner: it returns the STORED dag, marked replayed",
              bool(dag) and dag.get("replayed") is True and len(dag.get("nodes") or []) == 2)

        calls.clear()
        asyncio.run(P.decompose_intent(
            "SEARCH the WEB for the LATEST, linux kernel CVEs -- summarise the top three!"))
        check("planner: a rephrasing of the same intent also spends zero calls",
              len(calls) == 0, str(calls))

        calls.clear()
        fuzzy_text = "what is the current price of a second-hand bicycle in Amsterdam right now"
        dag = asyncio.run(P.decompose_intent(fuzzy_text))
        check("planner: a fuzzy variant FALLS BACK to planning", len(calls) == 1, str(calls))
        check("planner: the fuzzy variant is not marked replayed",
              not (dag or {}).get("replayed"))
        # The link between planning and capture: without this stamp every stored
        # template is unreplayable, and the whole feature is silently dead.
        check("planner: a freshly planned DAG carries the TURN's intent",
              (dag or {}).get("intent") == fuzzy_text, str((dag or {}).get("intent")))
        from mios_pipe.routing import run_template as _RT
        check("planner: that intent yields a usable capture key",
              bool(_RT._replay.intent_key((dag or {}).get("intent") or "")))

        calls.clear()
        asyncio.run(P.decompose_intent("search the web for linux kernel CVEs"))
        check("planner: a merely partial overlap also falls back", len(calls) == 1, str(calls))

        os.environ["MIOS_RUN_TEMPLATE_REPLAY"] = "false"
        calls.clear()
        dag = asyncio.run(P.decompose_intent(A))
        check("planner: at the DEFAULT flag the replay path is inert",
              len(calls) == 1 and not (dag or {}).get("replayed"), str(calls))
    finally:
        os.environ.pop("MIOS_RUN_TEMPLATE_REPLAY", None)
        P.httpx = real_httpx
        P.PLANNER_ENABLED, P.PLANNER_SHORT_PROMPT_CHARS, P.PLANNER_SHORT_PROMPT_WORDS = enabled, chars, words
        P.configure(build_dispatch_cmd=prev_build)


def main():
    t_keying()
    t_similarity()
    t_match()
    t_capture_roundtrip()
    t_planner_replay()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
