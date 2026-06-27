# AI-hint: Stdlib assert-script for mios_web_research. No network. Drives
# _web_research_enrich with stubbed subprocess (mios-web-search/extract/crawl/
# firecrawl) + a stubbed micro-LLM judge (httpx) + injected helper/contextvar
# deps, asserting: (1) the LOAD-BEARING judge-satisfied anti-fabrication gate
# loops on answerable=false and STOPS on answerable=true; (2) the step-recording
# shape (_web_steps / _web_sources / _web_stats + the live emit sink); (3) the
# nested _strip_nav_chrome nav-stripping + _rank_article_links 2-hop drill via
# their pipeline effects (nested -> exercised through the public function).
# AI-related: ./mios_web_research.py
import asyncio
import contextvars
import json
import os
import re

# Point MIOS_TOML at the repo's vendor mios.toml BEFORE importing the module so the
# SSOT [search].anchor_stopwords screen loads (the anchor tokenizer resolves it at
# import; absent -> degrade-open to an empty screen). Mirrors test_server_import.
_here = os.path.dirname(os.path.abspath(__file__))
_toml = os.path.abspath(os.path.join(_here, "..", "..", "..", "..",
                                     "usr", "share", "mios", "mios.toml"))
if "MIOS_TOML" not in os.environ and os.path.isfile(_toml):
    os.environ["MIOS_TOML"] = _toml

import mios_web_research as W


# -- stub deps -------------------------------------------------------
_routed = contextvars.ContextVar("routed", default=None)
_cenv = contextvars.ContextVar("cenv", default={})
# Source-registry contextvars the relocated citation cluster reads (the per-turn
# web_search/extract source bucket + the cross-agent turn key/registry).
_sources_var = contextvars.ContextVar("sources", default=None)
_conv_key = contextvars.ContextVar("conv_key", default="")
_src_turn = contextvars.ContextVar("src_turn", default=None)


def _url_has_path(u: str) -> bool:
    try:
        tail = u.split("://", 1)[-1]
        path = tail[tail.find("/"):] if "/" in tail else ""
        path = path.split("?", 1)[0].split("#", 1)[0]
        return any(s for s in path.split("/") if s)
    except Exception:
        return False


def _configure(**over):
    kw = dict(
        is_action_domain=lambda d: False,
        current_date_str=lambda: "2026-06-25",
        current_year=lambda: "2026",
        anchor_tokens=lambda t: set(),          # empty -> anchor filter skipped
        shares_anchor=lambda t, a: True,         # degrade-open
        url_has_path=_url_has_path,
        clean_web_text=lambda s: s,              # identity (isolate _strip_nav_chrome)
        routed_domain_var=_routed,
        client_env_var=_cenv,
        # The citation cluster (_src_record/_SRC_URL_RE) is now NATIVE to the module;
        # inject only the server-owned source-registry contextvars + dict it reads.
        sources_var=_sources_var,
        conv_key_var=_conv_key,
        src_turn_var=_src_turn,
        sources_registry={},
        sources_registry_cap=64,
        max_sources=8,
        web_enrich_verbs={"web_search", "web_extract", "crawl"},
        location_sensitive_phrases=(),
        judge_model="judge",
        judge_endpoint="http://127.0.0.1:1/v1",
        web_research_enabled=True,
        web_research_passes=1,
        web_research_results=8,
        web_research_fanout=1,
        web_research_fetch_n=1,
        web_research_fetch_chars=3000,
        web_research_block_chars=1200,
        web_research_search_timeout=5.0,
        web_research_fetch_timeout=5.0,
        web_research_crawl_fallback=False,
        web_research_min_chars=50,
        web_research_crawl_timeout=5.0,
        web_research_crawl_max=6,
        web_research_use_news_category=False,
        web_research_time_range="",
        web_research_max_attempts=2,
    )
    kw.update(over)
    W.configure(**kw)


# -- subprocess + httpx fakes ---------------------------------------
class _FakeProc:
    def __init__(self, out): self._out = out
    async def communicate(self): return (self._out, b"")
    def kill(self): pass


def _install_exec(router, counter):
    async def _fake_exec(*args, **kw):
        tool = args[0]
        counter[tool] = counter.get(tool, 0) + 1
        payload = router(tool, list(args))
        return _FakeProc(json.dumps(payload).encode("utf-8"))
    asyncio.create_subprocess_exec = _fake_exec


class _FakeResp:
    status_code = 200
    def __init__(self, payload): self._p = payload
    def json(self): return self._p


class _FakeClient:
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def post(self, url, **k):
        verdict = _JUDGE_QUEUE.pop(0) if _JUDGE_QUEUE else {"answerable": True}
        return _FakeResp({"choices": [{"message": {"content": json.dumps(verdict)}}]})


class _FakeHttpx:
    AsyncClient = _FakeClient


_JUDGE_QUEUE: list = []
_REAL_EXEC = asyncio.create_subprocess_exec
_REAL_HTTPX = W.httpx

LONG = ("This is a real fetched article body with plenty of substantive prose "
        "describing the actual developments the user asked about, well over the "
        "minimum character threshold so it counts as real content. " * 3)


# ===================================================================
# Test 1: the judge-satisfied gate loops on false, stops on true.
# ===================================================================
def _router_simple(tool, args):
    if tool == "mios-web-search":
        return {"results": [{"url": "https://example.com/article-one-2026",
                             "title": "Story One", "content": "snippet"}]}
    if tool == "mios-web-extract":
        return {"content": LONG}
    return {"success": False}


def test_judge_gate_loop_vs_stop():
    global _JUDGE_QUEUE
    W.httpx = _FakeHttpx
    try:
        # STOP: judge satisfied on attempt 1 -> exactly ONE search.
        _configure()
        _JUDGE_QUEUE = [{"answerable": True}]
        counter = {}
        _install_exec(_router_simple, counter)
        refined = {"web": True}
        out = asyncio.run(W._web_research_enrich("recent xyz developments", refined))
        assert out.startswith("LIVE WEB RESEARCH"), out[:60]
        assert counter.get("mios-web-search") == 1, counter
        # LOOP: judge unsatisfied then satisfied -> TWO searches (re-search fired).
        _configure()
        _JUDGE_QUEUE = [{"answerable": False, "better_query": "sharper angle q",
                         "scrape_url": ""},
                        {"answerable": True}]
        counter = {}
        _install_exec(_router_simple, counter)
        out2 = asyncio.run(W._web_research_enrich("recent xyz developments", {"web": True}))
        assert counter.get("mios-web-search") == 2, counter
        assert out2.startswith("LIVE WEB RESEARCH"), out2[:60]
    finally:
        asyncio.create_subprocess_exec = _REAL_EXEC
        W.httpx = _REAL_HTTPX
    print("test_judge_gate_loop_vs_stop OK")


# ===================================================================
# Test 2: step-recording shape + the live emit sink.
# ===================================================================
def test_step_recording_shape():
    global _JUDGE_QUEUE
    W.httpx = _FakeHttpx
    try:
        _configure(web_research_max_attempts=1)   # no judge call needed
        _JUDGE_QUEUE = []
        counter = {}
        _install_exec(_router_simple, counter)
        captured: list = []
        refined = {"web": True}
        out = asyncio.run(W._web_research_enrich(
            "recent xyz developments", refined, emit=captured.append))
        # grounding present
        assert out.startswith("LIVE WEB RESEARCH"), out[:60]
        assert "real fetched article body" in out
        # step-recording shape stashed on refined
        steps = refined.get("_web_steps")
        assert isinstance(steps, list) and steps, steps
        assert all(isinstance(s, dict) and "emoji" in s and "label" in s
                   and "detail" in s for s in steps), steps
        assert any(s["emoji"] == "\U0001F50E" for s in steps), "no search step"
        assert any(s["emoji"] == "\U0001F4D6" for s in steps), "no read step"
        # web stats + sources survive the handoff
        stats = refined.get("_web_stats")
        assert stats and stats["real"] == 1 and stats["sources"] >= 1, stats
        assert refined.get("_web_sources"), "no _web_sources block"
        # the live emit sink received the SAME steps
        assert captured == steps, (captured, steps)
    finally:
        asyncio.create_subprocess_exec = _REAL_EXEC
        W.httpx = _REAL_HTTPX
    print("test_step_recording_shape OK")


# ===================================================================
# Test 3: nested _strip_nav_chrome strips a nav line + _rank_article_links
# fires the 2-hop article drill (both exercised through the public fn).
# ===================================================================
NAV = ("[Home](https://news.example.com/) [About](https://news.example.com/about) "
       "[Contact](https://news.example.com/contact)")
PROSE = ("Real prose paragraph reporting the substantive facts the user asked "
         "about, with enough words to be retained as body content not chrome. " * 3)
INDEX_MD = NAV + "\n\n" + PROSE
STORY_URL = "https://news.example.com/story-about-the-big-thing-2026-01-02"


def _router_drill(tool, args):
    url = args[-1]
    if tool == "mios-web-search":
        # a bare HOMEPAGE result (no path) -> index page -> 2-hop drill
        return {"results": [{"url": "https://news.example.com/",
                             "title": "News Home", "content": "x"}]}
    if tool == "mios-web-extract":
        # the homepage extract is thin; the drilled story extract is rich
        if url == STORY_URL:
            return {"content": "STORY BODY " + LONG}
        return {"content": "thin"}
    if tool == "mios-crawl":
        if url == "https://news.example.com/":
            return {"success": True, "markdown": INDEX_MD,
                    "links": [{"href": STORY_URL}]}
        return {"success": True, "markdown": "STORY BODY " + LONG, "links": []}
    if tool == "mios-firecrawl":
        return {"success": False}
    return {"success": False}


def test_nav_strip_and_two_hop_drill():
    global _JUDGE_QUEUE
    W.httpx = _FakeHttpx
    _orig_port = W._is_port_open
    try:
        _configure(web_research_max_attempts=1, web_research_crawl_fallback=True,
                   web_research_fetch_n=2, web_research_passes=1)
        W._is_port_open = lambda *a, **k: True   # crawl + firecrawl engines "up"
        _JUDGE_QUEUE = []
        counter = {}
        _install_exec(_router_drill, counter)
        refined = {"web": True}
        out = asyncio.run(W._web_research_enrich("the big thing", refined))
        steps = refined.get("_web_steps") or []
        # _rank_article_links picked the deep story link -> a "reading the story" step
        assert any(s.get("label") == "reading the story" for s in steps), steps
        # the drilled story body reached the grounding
        assert "STORY BODY" in out, out[:120]
        # _strip_nav_chrome dropped the nav menu line from the index body
        assert "/about" not in out and "/contact" not in out, "nav chrome leaked"
    finally:
        asyncio.create_subprocess_exec = _REAL_EXEC
        W.httpx = _REAL_HTTPX
        W._is_port_open = _orig_port
    print("test_nav_strip_and_two_hop_drill OK")


# ===================================================================
# Test 4: the MODEL recency flag (refine.news / refine.needs_recency) is the SOLE
# authority for recency + SearXNG time-range -- NOT an English temporal-word list.
# Asserts: (a) news/needs_recency -> broad SSOT recency_range passed + current year
# appended; (b) a query CONTAINING a temporal word ("today") but NO flag does NOT
# trigger recency (proves the deleted lexical gate is gone).
# ===================================================================
def _capturing_router(sink):
    def _router(tool, args):
        if tool == "mios-web-search":
            sink.append(list(args))
            return {"results": [{"url": "https://example.com/article-one-x",
                                 "title": "Story One", "content": "snippet"}]}
        if tool == "mios-web-extract":
            return {"content": LONG}
        return {"success": False}
    return _router


def test_recency_flag_drives_time_range():
    global _JUDGE_QUEUE
    W.httpx = _FakeHttpx
    try:
        # (a) model flag news=True -> time-sensitive -> broad SSOT recency window
        # ("month") handed to the search + current year appended (no query keyword).
        _configure(web_research_max_attempts=1, web_research_recency_range="month")
        _JUDGE_QUEUE = []
        sink_a: list = []
        _install_exec(_capturing_router(sink_a), {})
        out = asyncio.run(W._web_research_enrich("xyz developments", {"news": True}))
        assert out.startswith("LIVE WEB RESEARCH"), out[:60]
        assert sink_a, "no search fired"
        a = sink_a[0]
        assert "--time-range" in a and a[a.index("--time-range") + 1] == "month", a
        assert a[-1].endswith("2026"), a[-1]   # current year appended (time-sensitive)

        # (a2) needs_recency ALSO drives recency (news absent) -- second model flag.
        _configure(web_research_max_attempts=1, web_research_recency_range="month")
        sink_a2: list = []
        _install_exec(_capturing_router(sink_a2), {})
        asyncio.run(W._web_research_enrich(
            "xyz developments", {"web": True, "needs_recency": True}))
        a2 = sink_a2[0]
        assert "--time-range" in a2 and a2[a2.index("--time-range") + 1] == "month", a2

        # (a3) the SSOT recency_range is honoured (not a frozen literal): set "week".
        _configure(web_research_max_attempts=1, web_research_recency_range="week")
        sink_a3: list = []
        _install_exec(_capturing_router(sink_a3), {})
        asyncio.run(W._web_research_enrich("xyz developments", {"news": True}))
        a3 = sink_a3[0]
        assert "--time-range" in a3 and a3[a3.index("--time-range") + 1] == "week", a3

        # (b) NO model recency flag, but the query CONTAINS the English word "today":
        # the DELETED word list would have made this time-sensitive; now it must NOT
        # -> no time_range arg, no year appended. Flag is the sole authority.
        _configure(web_research_max_attempts=1, web_research_recency_range="month")
        sink_b: list = []
        _install_exec(_capturing_router(sink_b), {})
        asyncio.run(W._web_research_enrich("what happened today", {"web": True}))
        b = sink_b[0]
        assert "--time-range" not in b, b      # no lexical recency from a query word
        assert "2026" not in b[-1], b[-1]      # no year appended without the model flag
    finally:
        asyncio.create_subprocess_exec = _REAL_EXEC
        W.httpx = _REAL_HTTPX
    print("test_recency_flag_drives_time_range OK")


# ===================================================================
# Test 5: the relocated per-turn SOURCE registry + citation cluster.
# Pure functions (no network); drive them through the injected contextvars
# + registry exactly as the pipeline does.
# ===================================================================
def test_source_registry_cluster():
    _configure()   # wires _sources_var/_conv_key/_src_turn/_SOURCES_REGISTRY + caps

    def _run():
        # Open a fresh turn bucket keyed off the conv key, then record real
        # (title,url) pairs into BOTH the contextvar bucket and the registry.
        _conv_key.set("chat-xyz")
        _sources_var.set([])
        W._src_turn_init()
        assert W._src_turn_key() == "chat-xyz"
        W._src_record([
            {"title": "Story One", "url": "https://example.com/article-one"},
            {"title": "Home", "url": "https://example.com/"},          # bare homepage
            {"title": "junk", "url": "not-a-url"},                      # dropped
            {"title": "Story One dup", "url": "https://example.com/article-one"},  # dup url
        ])
        refs = W._src_collected()
        # path-bearing URL preferred over the bare homepage; deduped by url.
        urls = [u for _t, u in refs]
        assert urls == ["https://example.com/article-one"], urls

        # markdown / metadata / annotations rendering off the same refs.
        md = W._sources_markdown(refs)
        assert "**Sources:**" in md and "https://example.com/article-one" in md
        meta = W._sources_metadata(refs)
        assert meta == [{"n": 1, "title": "Story One",
                         "url": "https://example.com/article-one"}], meta
        text = "see https://example.com/article-one for details"
        ann = W._sources_annotations(refs, text)
        assert ann[0]["type"] == "url_citation"
        assert ann[0]["start_index"] == text.find("https://example.com/article-one")

        # _filter_relevant_sources: keep title-overlapping, degrade-open to all
        # when nothing matches (never strip to empty).
        kept = W._filter_relevant_sources(refs, "a Story about One")
        assert kept == refs, kept
        kept_none = W._filter_relevant_sources(refs, "completely unrelated zzzz")
        assert kept_none == refs, "degrade-open: never strip citations to empty"

    import contextvars as _cv
    _cv.copy_context().run(_run)
    print("test_source_registry_cluster OK")


def test_src_record_from_text_harvest():
    _configure()

    def _run():
        _conv_key.set("chat-harvest")
        _sources_var.set([])
        W._src_turn_init()
        # Numbered '**Sources:**' block parses back into citable items.
        W._src_record_from_text(
            "answer body\n\n**Sources:**\n1. Title A — https://site.test/a\n"
            "2. Title B — https://site.test/b\n")
        urls = [u for _t, u in W._src_collected()]
        assert "https://site.test/a" in urls and "https://site.test/b" in urls, urls

        # _harvest_sub_sources prefers a structured mios_sources list.
        _sources_var.set([])
        W._SOURCES_REGISTRY[W._src_turn_key()] = []
        W._harvest_sub_sources({"mios_sources": [
            {"title": "Struct", "url": "https://site.test/structured"}]}, "ignored")
        urls2 = [u for _t, u in W._src_collected()]
        assert "https://site.test/structured" in urls2, urls2

    import contextvars as _cv
    _cv.copy_context().run(_run)
    print("test_src_record_from_text_harvest OK")


# ===================================================================
# Test 0: the relocated structural web-text + topical-anchor helpers, now NATIVE
# to the module. Run FIRST -- before any _configure() rebinds the overridable
# names -- so the native implementations are exercised directly.
# ===================================================================
def test_web_text_anchor_helpers_native():
    # Structure-only assertions on SYNTHETIC non-dictionary tokens -- the test bakes in
    # NO English/topic word list of its own; the one stopword reference is pulled from
    # the module's OWN set so behavior, not a duplicated literal, is what's checked.

    # _url_has_path: a bare host / front page -> False; a real path -> True.
    assert W._url_has_path("https://x.com/") is False
    assert W._url_has_path("https://x.com") is False
    assert W._url_has_path("https://x.com/aaa/bbb/ccc/ddd") is True

    # _clean_web_text: drop a pure nav-link bullet LINE, flatten an inline link to its
    # anchor text, strip an image, collapse 3+ blank lines to 2.
    raw = ("* [Navlbl](https://s.test/)\n"
           "Prose Zzqqx with an [Anchortxt](https://s.test/x) retained.\n"
           "![Imgalt](https://s.test/img.png)\n\n\n\nTailz.")
    cleaned = W._clean_web_text(raw)
    assert "https://s.test/x" not in cleaned          # inline URL flattened away
    assert "Anchortxt" in cleaned                      # anchor text retained
    assert "](https://s.test/)" not in cleaned         # nav bullet line dropped
    assert "![Imgalt]" not in cleaned                  # image stripped
    assert "\n\n\n" not in cleaned                      # blank runs collapsed
    assert W._clean_web_text("") == ""

    # _anchor_tokens STRUCTURAL rules: alpha-initial + len>=3 kept (lowercased), len<3
    # dropped, trailing-s plural fold (len>=5). Synthetic tokens -> no baked words.
    toks = W._anchor_tokens("Zorptel ab Quibblers")
    assert "zorptel" in toks                            # alpha-initial, len>=3, lowercased
    assert "quibbler" in toks                           # 'Quibblers' (len>=5, -s) folded
    assert "ab" not in toks                             # len<3 dropped
    # A stopword is removed -- proven against the module's OWN SSOT set, never a literal.
    _sw = next((w for w in W._ANCHOR_STOPWORDS if len(w) >= 3 and w.isalpha()), None)
    assert _sw is not None
    assert _sw not in W._anchor_tokens(f"Zorptel {_sw} Quibblers")

    # _shares_anchor: content overlap -> True; disjoint -> False; too-thin (<2) anchor
    # degrades OPEN (never over-filter).
    anchor = W._anchor_tokens("Zorptel Quibblers Frobnak")
    assert len(anchor) >= 2
    assert W._shares_anchor("brand Zorptel item", anchor) is True
    assert W._shares_anchor("aaaa bbbb cccc", anchor) is False
    assert W._shares_anchor("whatever", {"single"}) is True
    print("test_web_text_anchor_helpers_native OK")


# ===================================================================
# Test 6: the de-hardcoded article-link "real-headline" scorer. Every weight /
# length threshold / drop cutoff / top-N is SSOT (W._LINK_RANK_DEFAULTS / mios.toml
# [web_research]); these assertions pull EVERY boundary DYNAMICALLY from that fallback
# dict over SYNTHETIC urls/anchors -- no real-site name or English word is the test's
# source of truth. Proves: (a) the DEFAULT cfg reproduces the structural ranking/
# selection byte-for-byte; (b) an injected SSOT override changes the weights/
# thresholds/top-N (incl. the live _toml_section read with independent per-key
# fallback); (c) a malformed config degrades OPEN to the heuristic without raising;
# plus the 'embed' mode degrades OPEN to the structural ranker (no client wired).
# ===================================================================
def test_link_rank_scorer_ssot():
    d = W._LINK_RANK_DEFAULTS
    src = "https://syn.invalid/"                       # the index page itself (skipped)

    # SYNTHETIC candidates whose scores derive ENTIRELY from the SSOT dict:
    #   rich   = deep path + long hyphenated slug + a digit + a long anchor
    #   medium = a long hyphenated slug only (one shallow segment, empty anchor)
    #   weak   = one short plain segment + short anchor -> below min_score -> dropped
    _slug = ("a" * d["slug_min_len"]) + "-z"           # has '-', len >= slug_min_len
    _slug_digit = ("a" * d["slug_min_len"]) + "-7"     # same, but carries a digit
    _long_anchor = "h" * d["anchor_min_len"]           # len >= anchor_min_len
    rich = "https://syn.invalid/sec/" + _slug_digit
    medium = "https://syn.invalid/" + _slug
    weak = "https://syn.invalid/ab"
    cands = [(_long_anchor, rich), ("", medium), ("", weak)]

    # expected scores recomputed from the dict (NO baked literals):
    rich_score = (d["seg_base"] * 2 + d["slug_weight"]
                  + d["digit_weight"] + d["anchor_weight"])
    medium_score = d["seg_base"] * 1 + d["slug_weight"]
    weak_score = d["seg_base"] * 1
    assert weak_score < d["min_score"]                 # weak below the drop cutoff
    assert medium_score >= d["min_score"] and rich_score > medium_score

    # (a) DEFAULT cfg (None -> _link_rank_cfg() -> mios.toml == defaults): rich story
    # first, medium second, weak dropped -> byte-identical structural selection.
    ranked = W._rank_links_by_structure(cands, src, set())
    assert ranked == [rich, medium], ranked

    # (b) injected SSOT override changes behavior:
    over_top = {**d, "top_n": 1}                        # keep only the top result
    assert W._rank_links_by_structure(cands, src, set(), cfg=over_top) == [rich], "top_n"
    over_min = {**d, "min_score": rich_score}           # raise cutoff -> medium drops
    assert W._rank_links_by_structure(cands, src, set(), cfg=over_min) == [rich], "min_score"
    over_slug = {**d, "slug_weight": 0}                 # zero the slug bonus -> medium falls
    assert medium not in W._rank_links_by_structure(cands, src, set(), cfg=over_slug), "slug_weight"

    # (b2) the SSOT read itself: a monkeypatched [web_research] table is honored and
    # every UNSPECIFIED key still falls back to its own default (independent fallback).
    _orig = W._toml_section
    try:
        W._toml_section = lambda name: ({"top_n": 1, "slug_weight": 9}
                                        if name == "web_research" else {})
        cfg = W._link_rank_cfg()
        assert cfg["top_n"] == 1 and cfg["slug_weight"] == 9, cfg
        assert cfg["anchor_min_len"] == d["anchor_min_len"], cfg   # omitted -> default
        assert cfg["link_rank_mode"] == d["link_rank_mode"], cfg

        # (c) degrade-open: a config read that RAISES -> full defaults, no exception.
        def _boom(name):
            raise RuntimeError("malformed config")
        W._toml_section = _boom
        assert W._link_rank_cfg() == d, "raise -> defaults"
        W._toml_section = lambda name: ["not", "a", "table"]   # non-dict section
        assert W._link_rank_cfg() == d, "non-dict -> defaults"
        W._toml_section = lambda name: {"slug_weight": "NaN", "top_n": 2}  # garbage value
        cfg_bad = W._link_rank_cfg()
        assert cfg_bad["slug_weight"] == d["slug_weight"], cfg_bad   # bad key keeps default
        assert cfg_bad["top_n"] == 2, cfg_bad                        # good key still applies
    finally:
        W._toml_section = _orig

    # the 'embed' mode is a stub that degrades OPEN to the structural ranker -> output
    # identical to the default heuristic path (no embeddings client is wired here).
    over_embed = {**d, "link_rank_mode": "embed"}
    assert (W._rank_links(cands, src, set(), cfg=over_embed)
            == W._rank_links_by_structure(cands, src, set(), cfg=d)), "embed degrade-open"
    print("test_link_rank_scorer_ssot OK")


if __name__ == "__main__":
    test_web_text_anchor_helpers_native()
    test_link_rank_scorer_ssot()
    test_judge_gate_loop_vs_stop()
    test_step_recording_shape()
    test_nav_strip_and_two_hop_drill()
    test_recency_flag_drives_time_range()
    test_source_registry_cluster()
    test_src_record_from_text_harvest()
    print("ALL mios_web_research tests passed")
