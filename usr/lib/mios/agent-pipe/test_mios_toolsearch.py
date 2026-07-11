# AI-hint: Stdlib unit test for mios_toolsearch -- the embedding tool/app semantic-search core extracted from server.py (refactor R10). Stubs the injected deps (embed_one/cosine/verb catalog/MCP registry) with NO network or DB, pre-populates the module embedding caches so _ensure_verb_embeddings short-circuits, and asserts: cosine ranking + cap on /v1/tool-search, namespace/tier filters + detail_level shaping, external-MCP-tool inclusion, the substring fallback when embeddings are unavailable, _tool_embedding lookup precedence, and app_search_logic cosine ranking with _refresh_app_inventory stubbed.
# AI-related: ./mios_toolsearch.py, ./server.py
# AI-functions: _run, _cos, test_tool_search_ranks_and_caps, test_tool_search_filters_and_detail, test_tool_search_includes_mcp, test_tool_search_substring_fallback, test_tool_embedding_lookup, test_app_search_ranks, test_cosine_known_vectors, test_verb_embed_text_shapes, test_verb_embed_fingerprint_deterministic_and_stale
"""Offline unit tests for mios_toolsearch (no network, no DB, no subprocess)."""

import asyncio
import json
import math

import mios_toolsearch as ts


def _run(coro):
    return asyncio.run(coro)


def _cos(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# A query embedding pointing along the "search" axis; the verb vectors below put
# web_search closest, read_file orthogonal.
_QVEC = {"find on the web": [1.0, 0.0], "": None}


def _embed_stub(text, prefix=None):
    async def _inner():
        return _QVEC.get(text, [1.0, 0.0])
    return _inner()


def _reset(*, verb_emb=None, mcp_emb=None, catalog=None, mcp_tools=None,
           embed_one=_embed_stub):
    # _cosine is native to mios_toolsearch now (moved from server.py), so it is no
    # longer an injected dep -- configure() only takes the embedder + catalog/registry.
    ts.configure(
        embed_one=embed_one,
        verb_catalog=catalog if catalog is not None else {},
        mcp_client_tools=mcp_tools if mcp_tools is not None else {},
    )
    # Pre-populate caches so _ensure_verb_embeddings() short-circuits (no embed flood).
    ts._VERB_EMBEDDINGS.clear()
    ts._VERB_EMBEDDINGS.update(verb_emb or {})
    ts._MCP_EMBEDDINGS.clear()
    ts._MCP_EMBEDDINGS.update(mcp_emb or {})


_CATALOG = {
    "web_search": {"tier": "core", "sig": "web_search(q)", "desc": "search the web"},
    "read_file": {"tier": "common", "sig": "read_file(p)", "desc": "read a file"},
    "reboot": {"tier": "rare", "sig": "reboot()", "desc": "reboot the host"},
}
_VERB_EMB = {"web_search": [1.0, 0.0], "read_file": [0.0, 1.0]}


def test_tool_search_ranks_and_caps():
    _reset(verb_emb=_VERB_EMB, catalog=_CATALOG)
    resp = _run(ts.tool_search_logic(query="find on the web", limit=1))
    data = json.loads(resp.body)
    assert data["embedded"] is True, data
    assert len(data["hits"]) == 1, data
    assert data["hits"][0]["name"] == "web_search", data
    assert data["hits"][0]["score"] >= 0.99, data


def test_tool_search_filters_and_detail():
    _reset(verb_emb=_VERB_EMB, catalog=_CATALOG)
    # tier filter to "common" drops web_search (core); detail_level "names" trims shape.
    resp = _run(ts.tool_search_logic(query="find on the web", limit=5,
                                     tier="common", detail_level="names"))
    data = json.loads(resp.body)
    names = [h["name"] for h in data["hits"]]
    assert names == ["read_file"], data
    assert set(data["hits"][0].keys()) == {"name", "score"}, data["hits"][0]


def test_tool_search_includes_mcp():
    mcp_tools = {"mcp.srv.query": {"namespace": "duckdb_", "tier": "rare",
                                   "description": "run a SQL query"}}
    _reset(verb_emb=_VERB_EMB, mcp_emb={"mcp.srv.query": [1.0, 0.0]},
           catalog=_CATALOG, mcp_tools=mcp_tools)
    resp = _run(ts.tool_search_logic(query="find on the web", limit=5))
    data = json.loads(resp.body)
    names = [h["name"] for h in data["hits"]]
    assert "mcp.srv.query" in names, data
    # filter by namespace keeps only the MCP tool.
    resp2 = _run(ts.tool_search_logic(query="find on the web", limit=5,
                                      namespace="duckdb_"))
    names2 = [h["name"] for h in json.loads(resp2.body)["hits"]]
    assert names2 == ["mcp.srv.query"], names2


def test_tool_search_substring_fallback():
    # embed_one returns None -> substring path over name+desc.
    def _none(_t, *args, **kwargs):
        async def _inner():
            return None
        return _inner()
    _reset(verb_emb=_VERB_EMB, catalog=_CATALOG, embed_one=_none)
    resp = _run(ts.tool_search_logic(query="file", limit=5))
    data = json.loads(resp.body)
    assert data["embedded"] is False, data
    names = [h["name"] for h in data["hits"]]
    assert "read_file" in names and "web_search" not in names, data


def test_tool_embedding_lookup():
    _reset(verb_emb={"a": [1.0]}, mcp_emb={"mcp.x.y": [2.0]})
    assert ts._tool_embedding("a") == [1.0]
    assert ts._tool_embedding("mcp.x.y") == [2.0]
    assert ts._tool_embedding("missing") is None


def test_app_search_ranks():
    _reset()
    ts._APP_EMBEDDINGS.clear()
    ts._APP_EMBEDDINGS.update({
        "cat::Browser::b": {"vec": [1.0, 0.0],
                            "record": {"name": "Browser", "description": "surf the web",
                                       "category": "cat", "launch": "b"}},
        "cat::Editor::e": {"vec": [0.0, 1.0],
                           "record": {"name": "Editor", "description": "edit text",
                                      "category": "cat", "launch": "e"}},
    })

    async def _noop(force=False):
        return None
    orig = ts._refresh_app_inventory
    ts._refresh_app_inventory = _noop
    try:
        resp = _run(ts.app_search_logic(query="find on the web", limit=1))
    finally:
        ts._refresh_app_inventory = orig
    data = json.loads(resp.body)
    assert data["embedded"] is True, data
    assert len(data["hits"]) == 1 and data["hits"][0]["name"] == "Browser", data
    assert data["inventory_size"] == 2, data


def test_cosine_known_vectors():
    # Pure vector math (moved verbatim from server.py): identical unit vectors -> 1.0,
    # orthogonal -> 0.0, anti-parallel -> -1.0, and it cross-checks the reference _cos.
    assert ts._cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert ts._cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert abs(ts._cosine([1.0, 0.0], [-1.0, 0.0]) + 1.0) < 1e-9
    # scale-invariant: magnitude does not change cosine.
    assert abs(ts._cosine([2.0, 0.0], [5.0, 0.0]) - 1.0) < 1e-9
    assert abs(ts._cosine([3.0, 4.0], [3.0, 4.0]) - _cos([3.0, 4.0], [3.0, 4.0])) < 1e-9
    # degenerate inputs return 0.0 (empty / length-mismatch / zero-norm).
    assert ts._cosine([], [1.0]) == 0.0
    assert ts._cosine([1.0, 2.0], [1.0]) == 0.0
    assert ts._cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_verb_embed_text_shapes():
    # model_name alias takes precedence over the key; examples append after the desc.
    txt = ts._verb_embed_text("web_search",
                              {"model_name": "search_the_web", "desc": "search the web",
                               "examples": ["find news", " ", "look it up"]})
    assert txt == ("search_the_web: search the web\n"
                   "Example requests: find news | look it up"), txt
    # no model_name -> falls back to the verb key; no examples -> just "key: desc".
    assert ts._verb_embed_text("reboot", {"desc": "reboot the host"}) == "reboot: reboot the host"


def test_verb_embed_fingerprint_deterministic_and_stale():
    cat = {
        "web_search": {"tier": "core", "desc": "search the web"},
        "read_file": {"tier": "common", "desc": "read a file"},
        "reboot": {"tier": "rare", "desc": "reboot the host"},
    }
    _reset(catalog=cat)
    fp1 = ts._verb_embed_fingerprint()
    # Deterministic: same catalog -> same hash.
    assert ts._verb_embed_fingerprint() == fp1
    assert isinstance(fp1, str) and len(fp1) == 64  # sha256 hexdigest
    # 'rare' tier verbs are excluded -> changing a rare verb's desc must NOT move the fp.
    cat2 = {**cat, "reboot": {"tier": "rare", "desc": "totally different"}}
    _reset(catalog=cat2)
    assert ts._verb_embed_fingerprint() == fp1
    # A non-rare desc edit DOES move the fp (stale-cache invalidation).
    cat3 = {**cat, "read_file": {"tier": "common", "desc": "read a file slowly"}}
    _reset(catalog=cat3)
    assert ts._verb_embed_fingerprint() != fp1


def test_embedding_prefix_hygiene():
    embedded_calls = []

    async def _embed_tracker(text, prefix=None):
        embedded_calls.append((text, prefix))
        return [1.0, 0.0]

    mcp_tools = {"mcp.srv.query": {"namespace": "duckdb_", "tier": "rare",
                                   "description": "run a SQL query"}}
    _reset(verb_emb={}, mcp_emb={}, catalog=_CATALOG, mcp_tools=mcp_tools, embed_one=_embed_tracker)

    # 1. Run tool_search_logic (query search)
    _run(ts.tool_search_logic(query="find on the web"))
    assert any(prefix == "search_query: " for _, prefix in embedded_calls), embedded_calls

    # 2. Run _mcp_embed_new_tools (document storage)
    _run(ts._mcp_embed_new_tools())
    assert any(prefix == "search_document: " for _, prefix in embedded_calls), embedded_calls


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"all {len(fns)} tests passed")
