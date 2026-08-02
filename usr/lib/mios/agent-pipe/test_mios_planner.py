# AI-hint: Stdlib assert-script for mios_planner. No network: the planner LLM call in decompose_intent is exercised only on the early short-prompt-skip / disabled paths (no httpx). Verifies (1) _topological_order on a synthetic DAG -- dependency order + cycle/dangling fall-back to declaration order, no hang; (2) _dag_levels Kahn concurrent-level grouping + cycle progress-forcing; (3) decompose_intent envelope parse on a representative planner output via a STUBBED model call (monkeypatched httpx.AsyncClient) -- agent/tool node validation, <2-node reject, node cap; (4) configure() builds _PLANNER_SYSTEM byte-faithfully from injected sentinel catalogs and embeds them; (5) short-prompt-skip cutoffs read from SSOT injection; (6) the now-native Stage-2 narrowers _action_domain_verbs / _planner_system_for over a synthetic permission-driven SSOT (action-domain union, block-swap, research slice, None/unknown fail-safe).
# AI-related: ./mios_planner.py, ./server.py
# AI-functions: (test script -- no exported functions)
"""Offline assert-script for mios_planner. Run: python test_mios_planner.py"""

import asyncio
import contextvars
import json
import sys
import httpx

import mios_planner


def _ids(nodes):
    return [n.get("id") for n in nodes]


chain = [
    {"id": "n3", "tool": "c", "deps": ["n2"]},
    {"id": "n1", "tool": "a", "deps": []},
    {"id": "n2", "tool": "b", "deps": ["n1"]},
]
order = _ids(mios_planner._topological_order(chain))
assert order.index("n1") < order.index("n2") < order.index("n3"), order
assert set(order) == {"n1", "n2", "n3"}, order

diamond = [
    {"id": "n1", "deps": []},
    {"id": "n2", "deps": ["n1"]},
    {"id": "n3", "deps": ["n1"]},
    {"id": "n4", "deps": ["n2", "n3"]},
]
do = _ids(mios_planner._topological_order(diamond))
assert do[0] == "n1", do
assert do.index("n4") == 3, do
assert do.index("n2") < do.index("n4") and do.index("n3") < do.index("n4"), do

cycle = [
    {"id": "n1", "deps": ["n2"]},
    {"id": "n2", "deps": ["n1"]},
]
co = _ids(mios_planner._topological_order(cycle))
assert set(co) == {"n1", "n2"}, co

dangling = [{"id": "n1", "deps": ["ghost"]}]
assert _ids(mios_planner._topological_order(dangling)) == ["n1"]


lv = mios_planner._dag_levels(diamond)
assert _ids(lv[0]) == ["n1"], lv
assert {n["id"] for n in lv[1]} == {"n2", "n3"}, lv   # concurrent middle level
assert _ids(lv[2]) == ["n4"], lv
flat = [n["id"] for level in lv for n in level]
assert sorted(flat) == ["n1", "n2", "n3", "n4"], flat

fanout = [{"id": "a", "deps": []}, {"id": "b", "deps": []},
          {"id": "c", "deps": ["a"]}]
flv = mios_planner._dag_levels(fanout)
assert {n["id"] for n in flv[0]} == {"a", "b"}, flv
assert _ids(flv[1]) == ["c"], flv

clv = mios_planner._dag_levels(cycle)
cflat = sorted(n["id"] for level in clv for n in level)
assert cflat == ["n1", "n2"], cflat
assert all(len(level) == 1 for level in clv), clv   # forced single-node rounds


VERB = "<<VERB_CATALOG_SENTINEL>>"
RECIPE = "<<RECIPE_CATALOG_SENTINEL>>"
AGENT = "<<AGENT_CATALOG_SENTINEL>>"

_registry = {"hermes": {"lane": "x"}, "opencode": {"lane": "y"}}
_routed = contextvars.ContextVar("routed_domain", default=None)  # no domain routed


def _is_action_domain_stub(domain):
    return False


def _build_dispatch_cmd_stub(tool, args):
    return None if tool == "bogus_verb" else ["mios-launch", tool]


mios_planner.configure(
    verb_catalog_rendered=VERB,
    recipe_catalog_rendered=RECIPE,
    agent_catalog_rendered=AGENT,
    routed_domain_var=_routed,
    is_action_domain=_is_action_domain_stub,
    build_dispatch_cmd=_build_dispatch_cmd_stub,
    agent_registry=_registry,
)

ps = mios_planner._PLANNER_SYSTEM
assert isinstance(ps, str) and ps, "planner system not built"
assert VERB in ps and RECIPE in ps and AGENT in ps, "catalogs not embedded"
assert "You are the MiOS planner (Agentic-OS DAG decomposition layer)." in ps
assert "REASON -> PLAN -> DELEGATE meta-rule:" in ps
assert '{"action":"decompose",' in ps
assert "Cap your DAG at 8 nodes." in ps, "node cap not rendered"


class _FakeResp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    _next_content = None  # set per-test

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        body = {"choices": [{"message": {"content": _FakeClient._next_content}}]}
        return _FakeResp(body)


_orig_httpx_async_client = getattr(httpx, "AsyncClient", None)
mios_planner.httpx.AsyncClient = _FakeClient  # monkeypatch the model call

def tearDownModule():
    if _orig_httpx_async_client is not None:
        httpx.AsyncClient = _orig_httpx_async_client
        if hasattr(mios_planner, "httpx") and hasattr(mios_planner.httpx, "AsyncClient"):
            mios_planner.httpx.AsyncClient = _orig_httpx_async_client

GOOD = (
    "```json\n"
    '{"action":"decompose","summary":"find then launch",'
    '"nodes":['
    '{"id":"n1","tool":"directory_lookup","args":{"query":"x"},"deps":[]},'
    '{"id":"n2","agent":"hermes","prompt":"pick the best","deps":["n1"]}'
    "]}\n"
    "```"
)
LONG_TEXT = ("please find my report file and then open it in the editor "
             "after locating the most recent revision on disk")


async def _run(text, content):
    _FakeClient._next_content = content
    return await mios_planner.decompose_intent(text)


parsed = asyncio.run(_run(LONG_TEXT, GOOD))
assert parsed is not None, "good DAG was rejected"
assert parsed["action"] == "decompose", parsed
ids = [n["id"] for n in parsed["nodes"]]
assert ids == ["n1", "n2"], ids
assert parsed["nodes"][1]["agent"] == "hermes", parsed

BAD_AGENT = (
    '{"action":"decompose","summary":"",'
    '"nodes":[{"id":"n1","tool":"directory_lookup","args":{},"deps":[]},'
    '{"id":"n2","agent":"ghost_agent","prompt":"x","deps":["n1"]}]}'
)
assert asyncio.run(_run(LONG_TEXT, BAD_AGENT)) is None, "unknown agent not rejected"

BAD_VERB = (
    '{"action":"decompose","summary":"",'
    '"nodes":[{"id":"n1","tool":"directory_lookup","args":{},"deps":[]},'
    '{"id":"n2","tool":"bogus_verb","args":{},"deps":["n1"]}]}'
)
assert asyncio.run(_run(LONG_TEXT, BAD_VERB)) is None, "unknown verb not rejected"

ONE_NODE = ('{"action":"decompose","summary":"",'
            '"nodes":[{"id":"n1","tool":"directory_lookup","args":{},"deps":[]}]}')
assert asyncio.run(_run(LONG_TEXT, ONE_NODE)) is None, "single-node DAG not rejected"

N = mios_planner.PLANNER_MAX_NODES + 3
many = ",".join(
    '{"id":"m%d","tool":"directory_lookup","args":{},"deps":[]}' % i
    for i in range(N))
MANY = '{"action":"decompose","summary":"","nodes":[' + many + "]}"
capped = asyncio.run(_run(LONG_TEXT, MANY))
assert capped is not None, "valid many-node DAG rejected"
assert len(capped["nodes"]) == mios_planner.PLANNER_MAX_NODES, len(capped["nodes"])

assert asyncio.run(_run("open steam", GOOD)) is None, "short prompt not skipped"


assert mios_planner.PLANNER_SHORT_PROMPT_CHARS == 60, mios_planner.PLANNER_SHORT_PROMPT_CHARS
assert mios_planner.PLANNER_SHORT_PROMPT_WORDS == 10, mios_planner.PLANNER_SHORT_PROMPT_WORDS

mios_planner.configure(short_prompt_chars=4)
assert mios_planner.PLANNER_SHORT_PROMPT_CHARS == 4
assert asyncio.run(_run("open steam", GOOD)) is not None, "char cutoff not read from SSOT"

mios_planner.configure(short_prompt_chars=60, short_prompt_words=1)
assert asyncio.run(_run("open steam", GOOD)) is not None, "word cutoff not read from SSOT"

mios_planner.configure(short_prompt_words=10)
assert asyncio.run(_run("open steam", GOOD)) is None, "short prompt not skipped after restore"


SYN_CATALOG = {
    "qq_write_a": {"permission": "write"},
    "qq_probe_a": {"permission": "read"},
    "zz_read_b":  {"permission": "read"},
}
SYN_DOMAINS = {
    "doma": {"verbs": ["qq_write_a", "qq_probe_a"]},   # action: has a write verb
    "domb": {"verbs": ["zz_read_b"]},                  # research: no write verb
}


def _is_action_domain_real(domain):
    verbs = (SYN_DOMAINS.get(domain) or {}).get("verbs") or []
    return any((SYN_CATALOG.get(v) or {}).get("permission") == "write" for v in verbs)


mios_planner.configure(
    verb_catalog=SYN_CATALOG,
    routing_domains=SYN_DOMAINS,
    is_action_domain=_is_action_domain_real,
    verb_catalog_rendered=VERB,
)

assert mios_planner._action_domain_verbs() == {"qq_write_a", "qq_probe_a"}, \
    mios_planner._action_domain_verbs()

sys_a = mios_planner._planner_system_for("doma")
assert "qq_write_a" in sys_a and "qq_probe_a" in sys_a, sys_a
assert VERB not in sys_a, "full catalog block not narrowed for action domain"

sys_b = mios_planner._planner_system_for("domb")
assert "zz_read_b" in sys_b and "qq_write_a" not in sys_b, sys_b

assert mios_planner._planner_system_for(None) == mios_planner._PLANNER_SYSTEM
assert mios_planner._planner_system_for("ghost_domain") == mios_planner._PLANNER_SYSTEM

print("test_mios_planner: ALL PASS")
tearDownModule()
