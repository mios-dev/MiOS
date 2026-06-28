# AI-hint: WEB-RESEARCH enrichment subsystem extracted verbatim from server.py. The pipeline-side web toolchain loop (_web_research_enrich): a satisfaction-gated SearXNG metasearch -> concurrent fetch-engine race (web_extract + crawl4ai/Chrome-CDP & Camoufox deep render + Firecrawl) -> 2-hop article-link drill -> a MODEL-driven anti-fabrication "judge-satisfied" Definition-of-Done gate (the LOAD-BEARING decision of when enough REAL evidence was gathered vs. fabricating), plus the local _is_port_open render-engine probe it uses. ALSO OWNS the per-turn web-SOURCE registry + citation cluster (_src_turn_key/_src_turn_init/_src_record/_src_collected/_sources_markdown/_sources_metadata/_sources_annotations/_filter_relevant_sources/_src_record_from_text/_harvest_sub_sources + the _SRC_LINE_RE/_SRC_URL_RE parsers), relocated here because the web loop itself calls _src_record as it fetches. ALSO OWNS the structural web-text + topical-anchor helpers it relies on (_url_has_path article-vs-homepage signal, _clean_web_text markdown/URL site-chrome stripper + its _MD_*/_INLINE_LINK_RE/_NAV_BULLET_RE/_EMPTY_*/_DATA_URI_RE/_MULTI_BLANK_RE patterns, _anchor_tokens/_shares_anchor topical-overlap guard + _ANCHOR_STOPWORDS/_ANCHOR_TOKEN_RE) -- relocated home because the web loop is their primary caller; mios_knowledge reuses the anchor pair via server's broker; configure() still accepts all four as optional overrides (test isolation). The remaining server-side runtime helpers (_is_action_domain/_current_date_str/_current_year), request contextvars (_routed_domain_var/_client_env_var/_sources_var/_conv_key_var/_src_turn_var), the module-level _SOURCES_REGISTRY dict + its caps, MAX_SOURCES and WEB_RESEARCH_*/_JUDGE_*/_WEB_ENRICH_VERBS/_LOCATION_SENSITIVE_PHRASES config constant the moved code reads is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). _loads_lenient is imported directly from mios_jsonsalvage; live step-emits flow through the caller-supplied sync `emit` sink. server.py re-imports every name under its exact original alias so the importable surface stays byte-identical.
# AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_knowledge.py, ./test_mios_web_research.py
# AI-functions: _is_port_open, _web_research_enrich, configure, _url_has_path, _clean_web_text, _anchor_tokens, _shares_anchor, _src_turn_key, _src_turn_init, _src_record, _src_collected, _sources_markdown, _sources_metadata, _sources_annotations, _filter_relevant_sources, _src_record_from_text, _harvest_sub_sources
"""Pipeline-side WEB-RESEARCH enrichment: search -> multi-engine fetch -> judge.

Extracted verbatim from ``server.py``. ``_web_research_enrich`` runs the FULL
web toolchain itself (SearXNG metasearch with fan-out, concurrent web_extract +
crawl4ai + Firecrawl fetch race, a 2-hop article-link drill) under a
MODEL-driven satisfaction gate (``_judge_satisfied``) that is the load-bearing
anti-fabrication Definition-of-Done -- it decides when enough REAL evidence was
gathered instead of letting the swarm fabricate. The functions are unchanged;
``server.py`` re-imports every name under its original alias so the public
surface is byte-identical. Every server-side runtime helper, request contextvar
and ``WEB_RESEARCH_*``/``_JUDGE_*`` config constant the moved code reads is
dependency-injected via :func:`configure` (one-way module boundary -- this
module never imports ``server``); ``_loads_lenient`` is imported directly from
``mios_jsonsalvage``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional

import httpx

from mios_config import _toml_section
from mios_jsonsalvage import loads_lenient as _loads_lenient

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# server.py calls configure() with its runtime helpers + the request
# contextvars + the WEB_RESEARCH_*/_JUDGE_*/etc config constants AFTER
# every one is defined (one-way boundary: this module never imports
# server). They stay None/default until injected; every consumer that
# uses them is async/runtime so a standalone ``import mios_web_research``
# still succeeds.
_is_action_domain = None
_current_date_str = None
_current_year = None
# _anchor_tokens/_shares_anchor/_url_has_path/_clean_web_text are now NATIVE to this
# module (defined below) -- the web loop + citation cluster call them and mios_knowledge
# reuses the anchor pair via server's broker. configure() still accepts them as optional
# overrides (the unit test injects stubs to isolate the nav-chrome/anchor paths).
_routed_domain_var = None
_client_env_var = None
# Per-turn web-SOURCE registry plumbing the relocated citation cluster reads
# (the cluster's own _src_record/_SRC_URL_RE are now native to this module, so
# they are NOT injected -- only the server-owned request contextvars + the
# module-level registry dict + its caps stay injected by reference).
_sources_var = None
_conv_key_var = None
_src_turn_var = None
_SOURCES_REGISTRY = None
_SOURCES_REGISTRY_CAP = 64
MAX_SOURCES = 8
_WEB_ENRICH_VERBS = frozenset()
_LOCATION_SENSITIVE_PHRASES = ()
_JUDGE_MODEL = None
_JUDGE_ENDPOINT = None
WEB_RESEARCH_ENABLED = True
WEB_RESEARCH_PASSES = 4
WEB_RESEARCH_RESULTS = 8
WEB_RESEARCH_FANOUT = 3
WEB_RESEARCH_FETCH_N = 5
WEB_RESEARCH_FETCH_CHARS = 3000
WEB_RESEARCH_BLOCK_CHARS = 1200
WEB_RESEARCH_SEARCH_TIMEOUT = 30.0
WEB_RESEARCH_FETCH_TIMEOUT = 12.0
WEB_RESEARCH_CRAWL_FALLBACK = True
WEB_RESEARCH_MIN_CHARS = 300
WEB_RESEARCH_CRAWL_TIMEOUT = 45.0
WEB_RESEARCH_CRAWL_MAX = 6
WEB_RESEARCH_USE_NEWS_CATEGORY = False
WEB_RESEARCH_TIME_RANGE = ""
# Broader SearXNG `time_range` window applied to a model-classified time-sensitive
# turn (refine.news/needs_recency) when no explicit override is set -- the
# degrade-open default that replaced the deleted English temporal-word gate.
WEB_RESEARCH_RECENCY_RANGE = "month"
WEB_RESEARCH_MAX_ATTEMPTS = 5


def configure(*, is_action_domain=None, current_date_str=None, current_year=None,
              anchor_tokens=None, shares_anchor=None, url_has_path=None,
              clean_web_text=None, routed_domain_var=None,
              client_env_var=None, sources_var=None, conv_key_var=None,
              src_turn_var=None, sources_registry=None, sources_registry_cap=None,
              max_sources=None, web_enrich_verbs=None,
              location_sensitive_phrases=None, judge_model=None,
              judge_endpoint=None, web_research_enabled=None, web_research_passes=None,
              web_research_results=None, web_research_fanout=None,
              web_research_fetch_n=None, web_research_fetch_chars=None,
              web_research_block_chars=None, web_research_search_timeout=None,
              web_research_fetch_timeout=None, web_research_crawl_fallback=None,
              web_research_min_chars=None, web_research_crawl_timeout=None,
              web_research_crawl_max=None, web_research_use_news_category=None,
              web_research_time_range=None, web_research_recency_range=None,
              web_research_max_attempts=None) -> None:
    """Inject server.py runtime helpers, request contextvars and config consts.

    Constants are mapped to the EXACT original server-side global names; injected
    via ``is not None`` guards so a falsey-but-real value (0, 0.0, False, "")
    still overrides the placeholder."""
    global _is_action_domain, _current_date_str, _current_year, _anchor_tokens
    global _shares_anchor, _url_has_path, _clean_web_text
    global _routed_domain_var, _client_env_var, _WEB_ENRICH_VERBS
    global _sources_var, _conv_key_var, _src_turn_var, _SOURCES_REGISTRY
    global _SOURCES_REGISTRY_CAP, MAX_SOURCES
    global _LOCATION_SENSITIVE_PHRASES, _JUDGE_MODEL, _JUDGE_ENDPOINT
    global WEB_RESEARCH_ENABLED, WEB_RESEARCH_PASSES, WEB_RESEARCH_RESULTS
    global WEB_RESEARCH_FANOUT, WEB_RESEARCH_FETCH_N, WEB_RESEARCH_FETCH_CHARS
    global WEB_RESEARCH_BLOCK_CHARS, WEB_RESEARCH_SEARCH_TIMEOUT
    global WEB_RESEARCH_FETCH_TIMEOUT, WEB_RESEARCH_CRAWL_FALLBACK
    global WEB_RESEARCH_MIN_CHARS, WEB_RESEARCH_CRAWL_TIMEOUT, WEB_RESEARCH_CRAWL_MAX
    global WEB_RESEARCH_USE_NEWS_CATEGORY, WEB_RESEARCH_TIME_RANGE
    global WEB_RESEARCH_RECENCY_RANGE, WEB_RESEARCH_MAX_ATTEMPTS
    if is_action_domain is not None: _is_action_domain = is_action_domain
    if current_date_str is not None: _current_date_str = current_date_str
    if current_year is not None: _current_year = current_year
    if anchor_tokens is not None: _anchor_tokens = anchor_tokens
    if shares_anchor is not None: _shares_anchor = shares_anchor
    if url_has_path is not None: _url_has_path = url_has_path
    if clean_web_text is not None: _clean_web_text = clean_web_text
    if routed_domain_var is not None: _routed_domain_var = routed_domain_var
    if client_env_var is not None: _client_env_var = client_env_var
    if sources_var is not None: _sources_var = sources_var
    if conv_key_var is not None: _conv_key_var = conv_key_var
    if src_turn_var is not None: _src_turn_var = src_turn_var
    if sources_registry is not None: _SOURCES_REGISTRY = sources_registry
    if sources_registry_cap is not None: _SOURCES_REGISTRY_CAP = sources_registry_cap
    if max_sources is not None: MAX_SOURCES = max_sources
    if web_enrich_verbs is not None: _WEB_ENRICH_VERBS = web_enrich_verbs
    if location_sensitive_phrases is not None: _LOCATION_SENSITIVE_PHRASES = location_sensitive_phrases
    if judge_model is not None: _JUDGE_MODEL = judge_model
    if judge_endpoint is not None: _JUDGE_ENDPOINT = judge_endpoint
    if web_research_enabled is not None: WEB_RESEARCH_ENABLED = web_research_enabled
    if web_research_passes is not None: WEB_RESEARCH_PASSES = web_research_passes
    if web_research_results is not None: WEB_RESEARCH_RESULTS = web_research_results
    if web_research_fanout is not None: WEB_RESEARCH_FANOUT = web_research_fanout
    if web_research_fetch_n is not None: WEB_RESEARCH_FETCH_N = web_research_fetch_n
    if web_research_fetch_chars is not None: WEB_RESEARCH_FETCH_CHARS = web_research_fetch_chars
    if web_research_block_chars is not None: WEB_RESEARCH_BLOCK_CHARS = web_research_block_chars
    if web_research_search_timeout is not None: WEB_RESEARCH_SEARCH_TIMEOUT = web_research_search_timeout
    if web_research_fetch_timeout is not None: WEB_RESEARCH_FETCH_TIMEOUT = web_research_fetch_timeout
    if web_research_crawl_fallback is not None: WEB_RESEARCH_CRAWL_FALLBACK = web_research_crawl_fallback
    if web_research_min_chars is not None: WEB_RESEARCH_MIN_CHARS = web_research_min_chars
    if web_research_crawl_timeout is not None: WEB_RESEARCH_CRAWL_TIMEOUT = web_research_crawl_timeout
    if web_research_crawl_max is not None: WEB_RESEARCH_CRAWL_MAX = web_research_crawl_max
    if web_research_use_news_category is not None: WEB_RESEARCH_USE_NEWS_CATEGORY = web_research_use_news_category
    if web_research_time_range is not None: WEB_RESEARCH_TIME_RANGE = web_research_time_range
    if web_research_recency_range is not None: WEB_RESEARCH_RECENCY_RANGE = web_research_recency_range
    if web_research_max_attempts is not None: WEB_RESEARCH_MAX_ATTEMPTS = web_research_max_attempts


# ── Web-text + topical-anchor helpers (relocated home from server.py). The web loop
# below + the citation cluster call them, and mios_knowledge reuses the anchor pair via
# server's broker (re-imported there). Pure/structural -- markdown + URL shape only, no
# topic/keyword list. configure() can still override them for test isolation.
def _url_has_path(u: str) -> bool:
    """True when a URL points DEEPER than a site front page (has a real path) --
    a STRUCTURAL article-vs-homepage signal for ranking news results (no topic /
    English content). 'https://x.com/' and 'https://x.com' -> False; a story URL
    '.../world/region/a-story-slug/...' -> True. Import-free (called on the hot path)."""
    try:
        after = u.split("://", 1)[-1]
        path = after.split("/", 1)[1] if "/" in after else ""
        path = path.split("?", 1)[0].split("#", 1)[0]
        return bool(path.strip("/"))
    except Exception:  # noqa: BLE001
        return True


# Structural web-boilerplate strippers (a web answer punted +
# stayed vague because the fetched blocks were full of site chrome -- "* [link]
# (...)" nav bullets, SVG data: URIs, "![](...)" images, "[](javascript:void(0))"
# share buttons -- which ate the per-block char budget so the real article
# text was truncated out before the model saw it). These key off markdown / URL
# STRUCTURE ONLY -- no topic or English
# keyword list (operator binding: no hardcodes). Order matters: drop pure
# nav-link bullet LINES while they still carry the [..](..) shape, THEN flatten
# inline links in prose to their anchor text (kills the long URLs that also
# burn budget; the [n] block header still carries the citable source URL).
_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_EMPTY_LINK_RE = re.compile(r"\[\s*\]\([^)]*\)")
_NAV_BULLET_RE = re.compile(r"(?m)^\s*[\*\-+]\s*\[[^\]]*\]\([^)]*\)\s*$")
_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:https?|ftp|mailto|javascript)[^)]*\)")
_DATA_URI_RE = re.compile(r"\(data:[^)]*\)")
# Leftover empty list bullets after the link/image strips (e.g. "* )" / "* ").
_EMPTY_BULLET_RE = re.compile(r"(?m)^\s*[\*\-+]\s*[)\]\s]*$")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def _clean_web_text(s: str) -> str:
    """Strip structural site-chrome from one fetched page's text so the block
    char budget holds real article content. Language-agnostic (markdown/URL
    structure only). Best-effort: any failure returns the input unchanged."""
    if not s:
        return s
    try:
        s = _MD_IMG_RE.sub("", s)
        s = _EMPTY_LINK_RE.sub("", s)
        s = _NAV_BULLET_RE.sub("", s)
        s = _INLINE_LINK_RE.sub(r"\1", s)
        s = _DATA_URI_RE.sub("", s)
        s = _EMPTY_BULLET_RE.sub("", s)
        s = _MULTI_BLANK_RE.sub("\n\n", s)
        return s.strip()
    except Exception:  # noqa: BLE001 -- never let cleanup break grounding
        return s


# Topical query-anchor: a multi-word but OFF-TOPIC invented sub-query can pass a
# degenerate word-count filter yet fetch junk (an age-calculator from a "minus" sub-
# query, an iCloud Find-My page) that then poisons the grounding. These helpers require
# a generated query / fetched result to share >=1 CONTENT token with the ORIGINAL ask.
# The low-signal function-word screen is SSOT-sourced (mios.toml [search].anchor_stopwords,
# env MIOS_WEB_ANCHOR_STOPWORDS CSV) -- NO word list baked in code; degrade-open to empty
# (fewer stopwords -> MORE permissive overlap, never over-filter). The tokenizer is
# unicode-aware (CJK split per ideograph, every other script keeps whole letter+digit
# runs) so a non-Latin ask tokenizes instead of dropping to zero; bare numbers + sub-3
# ASCII fragments are excluded, Latin plurals fold on a trailing -s.
def _load_anchor_stopwords() -> frozenset:
    """Resolve the anchor stopword screen from SSOT: a CSV env override (rendered from
    mios.toml by the userenv slot map) -> the layered mios.toml [search].anchor_stopwords
    -> empty (degrade-open: no baked list in code, never over-filter). Lowercased."""
    _csv = os.environ.get("MIOS_WEB_ANCHOR_STOPWORDS")
    if _csv not in (None, ""):
        return frozenset(t.strip().lower() for t in _csv.split(",") if t.strip())
    _v = _toml_section("search").get("anchor_stopwords")
    if isinstance(_v, list):
        return frozenset(str(x).strip().lower() for x in _v if str(x).strip())
    return frozenset()


_ANCHOR_STOPWORDS = _load_anchor_stopwords()
# Unicode-aware content tokenizer (a Latin-only [A-Za-z]... screen tokenized CJK/accented
# text to ZERO, dropping every non-Latin anchor). CJK/Kana/Hangul are spaceless +
# information-dense so each ideograph is its own token; every other script keeps whole
# runs of unicode letters+digits (so accented/non-Latin words survive intact).
_CJK = ("぀-ヿ㄀-ㄯ㐀-䶿一-鿿"
        "豈-﫿가-힯")
_ANCHOR_TOKEN_RE = re.compile(rf"[{_CJK}]|[^\W_{_CJK}]+")


def _anchor_tokens(text: str) -> set:
    """Content tokens of `text` for topical-overlap anchoring: unicode-aware word tokens
    (CJK per-ideograph, other scripts whole), lowercased, bare numbers + the SSOT stopword
    screen removed, sub-3 ASCII fragments dropped (never length-gate non-Latin), Latin
    trailing-s plural fold."""
    out: set = set()
    for t in _ANCHOR_TOKEN_RE.findall(text or ""):
        t = t.lower()
        if t.isdigit():
            continue                            # a bare number / year is too weak an anchor
        if t.isascii() and len(t) < 3:
            continue                            # ASCII noise floor; never gate non-Latin
        if t in _ANCHOR_STOPWORDS:
            continue
        if len(t) >= 5 and t.endswith("s"):     # Latin plural fold (trailing -s)
            t = t[:-1]
        out.add(t)
    return out


def _shares_anchor(text: str, anchor: set) -> bool:
    """True when `text` shares >=1 content token with `anchor`. Degrades OPEN
    when the anchor is too thin (<2 tokens) to judge -- never over-filter."""
    if len(anchor) < 2:
        return True
    return bool(_anchor_tokens(text) & anchor)


# ── Article-link "real-headline" scorer (the 2-hop drill's link ranker) ──────────
# An INDEX page links out to many URLs; this ranks the most ARTICLE-LIKE ones by URL
# STRUCTURE ONLY -- NO hardcoded domain/keyword/topic list (operator binding). Every
# weight, length threshold, score cutoff and top-N is SSOT from mios.toml
# [web_research], layered over a degrade-open fallback whose literals EQUAL the
# long-standing structural defaults: with NO [web_research] override present the
# ranking is byte-identical. Model/embedding ranking is OPT-IN (link_rank_mode) and
# degrades OPEN to this structural path -- nothing here is a frozen magic weight.
_LINK_RANK_DEFAULTS = {
    "link_rank_mode": "heuristic",  # "heuristic" (structural, default) | "embed" (opt-in; degrade-open)
    "seg_base": 1,        # score per path segment (path depth = article-ness signal)
    "slug_weight": 2,     # bonus when the last segment is a long hyphenated headline slug
    "slug_min_len": 12,   # min last-segment length to count as a headline slug
    "digit_weight": 1,    # bonus when the path carries a digit (a date / article id)
    "anchor_weight": 2,   # bonus when the anchor text is long (a real headline)
    "anchor_min_len": 25, # min anchor-text length to count as a real headline
    "min_score": 2,       # drop shallow generic / utility links scoring below this
    "top_n": 6,           # keep at most this many ranked article links
}


def _link_rank_cfg() -> dict:
    """Resolve the article-link scorer's mode + weights/thresholds from SSOT
    (mios.toml [web_research]) layered over the degrade-open defaults. Each key
    falls back INDEPENDENTLY, so a partial or malformed [web_research] table still
    yields the byte-identical structural ranking for every key it omits. Never
    raises (degrade-open): any read/parse error returns the full defaults."""
    cfg = dict(_LINK_RANK_DEFAULTS)
    try:
        sect = _toml_section("web_research")
        if isinstance(sect, dict):
            for k, default in _LINK_RANK_DEFAULTS.items():
                v = sect.get(k)
                if v is None:
                    continue
                try:
                    if isinstance(default, str):
                        if isinstance(v, str) and v:
                            cfg[k] = v
                    elif isinstance(v, bool):
                        continue              # a stray bool never poisons an int weight
                    else:
                        cfg[k] = int(v)
                except (TypeError, ValueError):
                    continue                  # one bad key keeps its default, never raises
    except Exception:  # noqa: BLE001 -- degrade-open: any error -> full structural defaults
        return dict(_LINK_RANK_DEFAULTS)
    return cfg


def _rank_links_by_structure(cands: list, src_url: str, anchor: set,
                             cfg: Optional[dict] = None) -> list:
    """Structural 'real-headline' ranker (link_rank_mode='heuristic', the default).
    Scores each (anchor_text, url) candidate by URL STRUCTURE ONLY -- path depth, a
    long hyphenated headline slug, a date/id digit, and a long anchor -- with NO
    hardcoded domain/keyword/topic list. Every weight/threshold/cutoff/top-N comes
    from `cfg` (SSOT via _link_rank_cfg); the default `cfg` reproduces today's ranking
    byte-for-byte. Returns the top-N article URLs, score-descending."""
    if cfg is None:
        cfg = _link_rank_cfg()
    scored: list = []
    _seen_l: set = set()
    for atext, u in cands:
        if not u.startswith(("http://", "https://")) or u == src_url:
            continue
        if u in _seen_l or not _url_has_path(u):
            continue
        # Skip a NESTED linked-image `[![alt](img)](link)`: the simple markdown regex
        # captures the IMAGE url + an anchor that begins with image markdown. A
        # markdown-SHAPE test, not an asset-extension list.
        if atext.startswith("!") or "](" in atext:
            continue
        if len(anchor) >= 2 and not _shares_anchor(u + " " + atext, anchor):
            continue
        _tail = u.split("://", 1)[-1]
        _path = _tail[_tail.find("/"):] if "/" in _tail else ""
        _path = _path.split("?", 1)[0].split("#", 1)[0]
        _segs = [s for s in _path.split("/") if s]
        _last = (_segs[-1] if _segs else "").replace("_", "-")
        _score = cfg["seg_base"] * len(_segs)
        if "-" in _last and len(_last) >= cfg["slug_min_len"]:
            _score += cfg["slug_weight"]            # long hyphenated headline slug
        if any(c.isdigit() for c in _path):         # str.isdigit() is unicode-aware
            _score += cfg["digit_weight"]           # date / article id
        if len(atext) >= cfg["anchor_min_len"]:
            _score += cfg["anchor_weight"]          # long anchor = real headline
        if _score < cfg["min_score"]:               # shallow generic / utility link
            continue
        _seen_l.add(u)
        scored.append((_score, u))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [u for _s, u in scored[:cfg["top_n"]]]


def _rank_links_embed(cands: list, src_url: str, anchor: set, cfg: dict):
    """OPT-IN embedding-cosine link ranker (link_rank_mode='embed'). STUB: no
    embeddings client is reachable from THIS module today (the embeddings lane lives
    behind the agent-pipe broker, not imported here), so this returns None to
    DEGRADE-OPEN to the structural ranker. The hook exists so enabling model ranking
    is an SSOT flip + a wired embed client -- never a fabricated/invented path. A real
    impl would cosine each candidate's anchor/url text against the turn's topical
    `anchor` (or query) embedding and return the top-N URLs."""
    return None


def _rank_links(cands: list, src_url: str, anchor: set,
                cfg: Optional[dict] = None) -> list:
    """Rank candidate article links per the SSOT link_rank_mode. Default 'heuristic'
    = the structural ranker. A non-default mode is tried first and DEGRADES OPEN to
    the structural ranker on a None result or ANY error (operator binding: a mode flip
    never breaks the drill)."""
    if cfg is None:
        cfg = _link_rank_cfg()
    mode = cfg.get("link_rank_mode") or "heuristic"
    if mode != "heuristic":
        try:
            ranked = _rank_links_embed(cands, src_url, anchor, cfg)
            if ranked is not None:
                return ranked
        except Exception:  # noqa: BLE001 -- degrade-open: non-default mode error -> structural
            log.debug("link-rank %r mode failed; degrading to structural", mode,
                      exc_info=True)
    return _rank_links_by_structure(cands, src_url, anchor, cfg)


def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            s.connect((host, port))
            return True
    except Exception:
        return False


async def _web_research_enrich(query: str, refined: Optional[dict],
                               emit=None, quick: bool = False) -> str:
    """Pipeline-side WEB-RESEARCH loop ("the MiOS pipeline
    ITSELF loops for web use and web tools"). For a web-needing turn the PIPELINE
    runs the web toolchain itself: SearXNG web_search WITH FAN-OUT (multiple
    diverse sub-queries) then web_extract the top result pages for their REAL
    text, over WEB_RESEARCH_PASSES drill passes. The fetched content is injected
    as grounding for EVERY agent (primary + reasoning-only secondaries), so the
    swarm answers from actual stories instead of shallow homepage snippets,
    regardless of any single agent's tool-loop depth. Best-effort + bounded;
    '' when disabled / not a web turn / nothing fetched."""
    if not WEB_RESEARCH_ENABLED or not query or not query.strip():
        return ""
    if (refined or {}).get("intent") == "chat":
        return ""
    # LOCAL-STATE short-circuit : a query about THIS
    # machine's own state ("summarize recent activity", "check service status")
    # must NEVER web-search -- the web returns irrelevant junk (random .xlsx
    # files that merely contain "mios", a dictionary def of "list", the "Next"
    # fashion brand). _read_tool_enrich grounds these on real local tools
    # instead. This overrides the web-verb hint below (refine sometimes hints
    # web_search for a local query too).
    if (refined or {}).get("local_state"):
        return ""
    # GATE: fire ONLY when refine hinted an ACTUAL web verb (relevance-gating,
    # "internal MiOS prompt? probably don't need full web
    # tools"). Match the EXPLICIT web-verb set -- NOT a "search"/"web" substring,
    # which also matched the LOCAL search verbs (knowledge_search /
    # everything_search / fs_search / app_search / tool_search) and made an
    # internal system/file query wastefully run full web research (caught live
    # a "MiOS system status" turn deep-crawled 3 web pages). open_url
    # counts as a web need too.
    _webverbs = _WEB_ENRICH_VERBS | {"open_url"}
    hints = [str(t).lower().strip() for t in ((refined or {}).get("hint_tools") or [])]
    # Fire on an explicit web-verb hint OR the model's news/web/deep classification
    # : the tiny refine model frequently malforms the
    # `hint_tools` array (it's line 11 of the envelope -> the recurring parse-fail);
    # _loads_lenient still recovers intent/refined_text/news, so a NEWS / web /
    # deep-research turn must NOT lose its web grounding just because hint_tools was
    # dropped. news/web/deep are MODEL-driven flags (no hardcoded keyword), and the
    # local_state short-circuit above already excludes machine-state queries.
    _web_flagged = bool((refined or {}).get("news") or (refined or {}).get("web")
                        or (refined or {}).get("deep")
                        or (refined or {}).get("deep_research")
                        # ROUTER-reliable signal (fabrication-root fix):
                        # the tiny refine model frequently DROPS hint_tools/web, so an
                        # obvious web turn never grounded (research_chars=0) and the
                        # swarm FABRICATED "search results". The domain router already
                        # classified this turn web -- trust it to fire web grounding.
                        # (local_state machine-state queries short-circuited above.)
                        or _routed_domain_var.get(None) == "web")
    # ACTION-domain HARD skip : an action turn NEVER
    # web-researches -- even if refine mis-set web OR carried a web_search HINT
    # ("open discord and send a message" still web-searched a fabricated URL after
    # the dispatch + browser guards, because hint_tools held web_search). Return
    # immediately. Data-driven on verb permission (_is_action_domain); no literals.
    if _is_action_domain(_routed_domain_var.get(None)):
        return ""
    if not _web_flagged and not any(h in _webverbs for h in hints):
        return ""

    async def _search(q: str, news: bool = False, time_range: str = "") -> list:
        # news=True targets SearXNG's NEWS category (dated stories) instead of
        # the general web -- set by refine's MODEL-DRIVEN `news` flag for
        # current-events / breaking / trending asks (a vague
        # 'current global trending' hit the 'Current' banking app on a general
        # search; the news index returns real dated stories). NOT a Python
        # keyword check -- the refine model classifies the intent. time_range
        # recency-filters the GENERAL search (the news ENGINES are IP-blocked, so
        # this is how a current ask gets CURRENT content --).
        args = ["mios-web-search", "-n", str(WEB_RESEARCH_RESULTS),
                "--fanout", str(WEB_RESEARCH_FANOUT)]
        if news:
            args.append("--news")   # SearXNG news category -> real dated stories
        if time_range:
            args += ["--time-range", time_range]
        args.append(q[:400])
        try:
            p = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_SEARCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            return [r for r in (d.get("results") or []) if r.get("url")]
        except Exception as e:  # noqa: BLE001 -- best-effort
            try: p.kill()
            except: pass
            log.debug("web-research search failed: %s", e)
            return []

    async def _extract(url: str) -> str:
        try:
            p = await asyncio.create_subprocess_exec(
                "mios-web-extract", "-n", str(WEB_RESEARCH_FETCH_CHARS), url,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_FETCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            return (d.get("content") or "").strip()
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return ""

    async def _crawl(url: str) -> tuple:
        # Deep render via the local crawl engine (crawl4ai+CDP / Camoufox).
        # Returns (markdown, links) -- links feed the 2-hop article drill below.
        if not _is_port_open(11235):
            return "", []
        try:
            p = await asyncio.create_subprocess_exec(
                "mios-crawl", "--json", "--max-chars", str(WEB_RESEARCH_FETCH_CHARS),
                url, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_CRAWL_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            if d.get("success"):
                return (d.get("markdown") or "").strip(), (d.get("links") or [])
            return "", []
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return "", []

    async def _firecrawl(url: str) -> tuple:
        # Clean article/news markdown via the self-hosted Firecrawl (web_scrape
        # backend). A THIRD fetch engine raced beside extract + crawl4ai so the
        # pipeline uses ALL web tools (operator) -- richest wins in _fetch_all.
        # Returns (markdown, links).
        # Gate ONLY on :3002 (the host-published Firecrawl proxy mios-firecrawl
        # targets). Redis :6379 is the firecrawl pod's INTERNAL job queue, reached
        # only by the firecrawl-api/worker containers -- never from this host-side
        # broker -- so probing it here always failed and silently dropped the
        # firecrawl engine out of the _fetch_all race once the pod was deployed.
        if not _is_port_open(3002):
            return "", []
        try:
            p = await asyncio.create_subprocess_exec(
                "mios-firecrawl", "--max-chars", str(WEB_RESEARCH_FETCH_CHARS),
                url, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_CRAWL_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            if d.get("success"):
                return (d.get("markdown") or "").strip(), (d.get("links") or [])
            return "", []
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return "", []

    async def _judge_satisfied(user_q: str, gathered: str) -> tuple:
        # MODEL-DRIVEN Definition-of-Done (operator "loop until satisfied"): the
        # warm micro judges whether the gathered web content ANSWERS the query;
        # if NOT it returns BOTH a sharper search query AND a concrete source URL
        # to fetch directly (chose "model picks the source" --
        # no hardcoded news list; the MODEL names an authoritative page and the
        # loop Firecrawl-scrapes it, bypassing junk search results). No hardcoded
        # topic/keyword check. Returns (answerable, better_query, scrape_url).
        # Degrade OPEN (satisfied) on any error so a judge hiccup never blocks.
        if not gathered.strip():
            return False, "", ""
        sys_p = (
            "You decide whether the GATHERED web content actually DELIVERS what "
            "the USER QUERY asks for -- not merely whether it is on-topic. Reply "
            "JSON ONLY: {\"answerable\": true|false, "
            "\"better_query\": \"<sharper web-search query if NOT answerable, else "
            "empty>\", \"scrape_url\": \"<a concrete authoritative http(s) URL "
            "whose page most likely HAS the answer, to fetch directly -- e.g. a "
            "major outlet's lite/text news index for a current-events ask -- else "
            "empty>\"}. STRICT: answerable=true ONLY when the content contains the "
            "SPECIFIC deliverable the user asked for -- e.g. if they asked to "
            "'compile reviews', you need actual REVIEW verdicts/scores from named "
            "outlets, NOT pre-launch hype or 'the game exists' pages; if they "
            "asked 'what's new', you need actual DATED headlines/stories, NOT news "
            "homepages or nav text. answerable=false when the content is off-topic, "
            "junk (dictionary/brand/homepage), pre-launch filler, or missing the "
            "specific facts -- then KEEP LOOPING: give a sharper better_query (a "
            "DIFFERENT angle than before) + a concrete scrape_url. Better to loop "
            "again than to declare a thin/wrong page answerable. better_query + "
            "scrape_url must be concrete and AVOID vague words a search engine "
            "mis-matches to a brand/product. Prefer lightweight text/lite endpoints. "
            "STRICT RECENCY: If the USER QUERY asks for 'today', 'recent', 'latest', "
            "'now', or a specific year/date, the GATHERED content MUST contain facts "
            "or stories from that exact timeframe. If the content is stale or from "
            "a past year/timeframe relative to the CURRENT DATE (e.g. last year's "
            "results when the query asks for the current year/today), set answerable=false and you "
            "MUST suggest a sharper query with the correct year/date or a concrete "
            "authoritative news URL to scrape. Don't accept year-old listicles or posts as 'today'.")
        _msgs = [{"role": "system", "content": sys_p},
                 {"role": "user",
                  "content": f"CURRENT DATE: {_current_date_str()}\nUSER QUERY: {user_q}\n\nGATHERED:\n{gathered}"}]
        # ENDPOINT-AWARE (the judge can run on the iGPU,
        # which is llama.cpp serving OpenAI /v1 -- NOT Ollama /api/chat). Ollama
        # lanes (:11434/:11435) use native /api/chat + think:False (the /v1 compat
        # path strands a qwen3 'think' answer in an empty content field); a
        # non-ollama /v1 endpoint (the iGPU's qwen2.5, no think-split) uses
        # /chat/completions with response_format json_object.
        _url = (f"{_JUDGE_ENDPOINT}/chat/completions" if _JUDGE_ENDPOINT.endswith("/v1")
                else f"{_JUDGE_ENDPOINT}/v1/chat/completions")
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                r = await c.post(_url, json={
                    "model": _JUDGE_MODEL, "messages": _msgs, "stream": False,
                    "temperature": 0.0, "max_tokens": 200,
                    "response_format": {"type": "json_object"}},
                    headers={"Content-Type": "application/json"})
                if r.status_code != 200:
                    return True, "", ""        # degrade open
                msg = (((r.json().get("choices") or [{}])[0]
                        .get("message") or {}).get("content")) or "{}"
            obj = _loads_lenient(msg)
            return (bool(obj.get("answerable")),
                    str(obj.get("better_query") or ""),
                    str(obj.get("scrape_url") or ""))
        except Exception:  # noqa: BLE001 -- never block the answer on the judge
            log.warning("Judge satisfied check encountered unexpected error", exc_info=True)
            return True, "", ""

    # Search the MODEL-SHARPENED query (refine's refined_text) or query argument,
    # prioritizing query since it might carry caller-anchored years.
    search_q = query.strip() if (query and query.strip()) else str((refined or {}).get("refined_text") or "").strip()
    # LOCATION-SCOPE the query ("weather + local news grounded
    # to the WRONG city -- New York / Chicago sources mislabeled as Cobourg"): a
    # location-sensitive ask (weather / 'near me' / local / local news) MUST carry
    # the user's REAL resolved location into the SEARCH STRING, else the engine
    # returns generic/foreign hits the model then passes off as local. Inject the
    # location from THIS turn's env grounding when the ask needs it and it isn't
    # already present. NEVER fabricate -- only a real, resolved location is used.
    try:
        _cenv = _client_env_var.get() if isinstance(_client_env_var.get(), dict) else {}
        _q_loc = str(_cenv.get("location") or "").strip()
        # PRIMARY: the model-classified needs_location flag (refine). FALLBACK: an SSOT
        # [routing].location_sensitive_phrases match -- NOT a hardcoded English list in
        # code (operator binding: model-classified, no hardcoded keyword lists).
        _ql = search_q.lower()
        _loc_sensitive = bool((refined or {}).get("needs_location")) or any(
            _ph in _ql for _ph in _LOCATION_SENSITIVE_PHRASES)
        if (_q_loc and _loc_sensitive
                and _q_loc.split(",")[0].strip().lower() not in search_q.lower()):
            search_q = f"{search_q} {_q_loc}".strip()
            log.info("web-research: location-scoped the query to %r", _q_loc)
    except Exception:  # noqa: BLE001
        pass
    # TIME-SENSITIVE / RECENCY detection: the MODEL-emitted refine flags are the
    # SOLE authority (no hardcoded keyword law). refine.news (current-events /
    # "latest" asks) and refine.needs_recency (when the classifier emits it) decide
    # whether the turn wants fresh content. An English/ASCII temporal-word list here
    # GATED this decision and silently MISSED every paraphrased / non-English
    # temporal ask while the file claimed "no hardcoded keyword" -- deleted. Degrade
    # OPEN: an absent flag => not time-sensitive (no lexical guess from the query).
    _time_sensitive = bool((refined or {}).get("news") or (refined or {}).get("needs_recency"))
    # Append the CURRENT YEAR to a time-sensitive query that names no explicit year.
    # The 4-digit-year probe is STRUCTURAL (is a literal year already present?), not
    # a keyword match, so it stays.
    if (_time_sensitive and not re.search(r"\b(?:19|20)\d{2}\b", search_q)):
        search_q = f"{search_q} {_current_year()}".strip()
    # News category is GATED OFF by default (WEB_RESEARCH_USE_NEWS_CATEGORY): the
    # news engines are IP-blocked on this instance -> news category = stale
    # wikinews only, which PUNTED "latest <X> news" turns (live debug).
    # General search works, so route news asks through it too until news engines
    # are unblocked. refine's `news` flag still gates IF news is ever re-enabled.
    _use_news = WEB_RESEARCH_USE_NEWS_CATEGORY and bool((refined or {}).get("news"))
    # TIME-SENSITIVE general search : when refine flags the
    # turn `news` (current/recent/trending), recency-filter the general web so it
    # returns CURRENT content instead of evergreen Wikipedia / stale listicles --
    # the news ENGINES are blocked, so this (not the news category) is the lever.
    # The explicit override (WEB_RESEARCH_TIME_RANGE) wins; else a model-classified
    # time-sensitive turn DEGRADES OPEN to the broader SSOT recency window
    # (WEB_RESEARCH_RECENCY_RANGE, default "month"). The narrower-vs-broader choice
    # used an English word list ("today"/"now"/"yesterday" -> week) that GATED the
    # window and missed any paraphrased / non-English temporal ask -- deleted; the
    # broad SSOT window is the safe non-lexical default.
    _time_range = WEB_RESEARCH_TIME_RANGE
    if not _time_range and _time_sensitive:
        _time_range = WEB_RESEARCH_RECENCY_RANGE
    # Per-STEP emit log ("need emitters for every step
    # end-to-end" -- not one whole-loop summary). Each web step is recorded here;
    # the streaming path replays them as individual emits. Stashed on refined.
    _steps: list = []

    def _rec(_s: dict) -> None:
        # record the step AND emit it LIVE (stream every step
        # throughout the pipeline, not a dump at the end). `emit` is a sync sink
        # (e.g. queue.put_nowait) supplied by a streaming caller; best-effort.
        _steps.append(_s)
        if emit:
            try:
                emit(_s)
            except Exception:  # noqa: BLE001
                pass

    # SATISFACTION-GATED LOOP ("loop until satisfied...
    # across all nodes"): search -> drill across ALL fetch engines (web_extract +
    # crawl4ai/real-Chrome + Firecrawl) -> a MODEL judge decides if the gathered
    # content actually ANSWERS the query; if not, the warm micro hands back a
    # SHARPER query and we SEARCH AGAIN (different angle), accumulating content,
    # until satisfied or MIOS_WEB_RESEARCH_MAX_ATTEMPTS. So a junk first search
    # ("current" -> the banking app) no longer surrenders a non-answer. The
    # resulting grounding is injected into EVERY agent's prompt (council prefix +
    # per-facet swarm) -> the loop's payoff reaches agents on ALL nodes (local
    # dGPU, the Windows iGPU, the phone, any cluster node).
    content: dict = {}          # url -> REAL article text (>= MIN_CHARS)
    snippets: dict = {}         # url -> fallback snippet (thin/blocked page)
    touched: list = []          # results considered, in drill order
    seen: set = set()           # urls already fetched (dedup ACROSS attempts)
    crawl_budget = WEB_RESEARCH_CRAWL_MAX
    link_budget = WEB_RESEARCH_CRAWL_MAX   # 2-hop article-link drill budget
    # QUICK mode : a research facet that only feeds an ACTION
    # (e.g. "launch the best game" -> rank then launch_verified) needs a FAST
    # ranking, so it does ONE search pass (not the full multi-attempt 2-hop drill).
    # It STILL fans out across all fetch engines per URL ("use
    # all web tools") -- just not the multi-attempt re-search loop. Standalone
    # research (news, reports; no action) keeps the full deep loop.
    _max_att = 1 if quick else WEB_RESEARCH_MAX_ATTEMPTS
    want = max(1, WEB_RESEARCH_FETCH_N)
    n_crawled = 0               # pages whose richest text came from a deep engine
    passes = 0
    search_q_now = search_q
    # STABLE topical anchor = the ORIGINAL ask (user/facet query + refined text),
    # NOT the drifting search_q_now. Used to drop off-topic results + re-search
    # queries the weak micro invents (flight-query derail).
    _anchor = _anchor_tokens(f"{query} {(refined or {}).get('refined_text') or ''}")

    async def _fetch_all(url: str) -> tuple:
        # Race ALL fetch engines CONCURRENTLY (operator "use ALL web tools"):
        # web_extract (fast readable text) + crawl4ai (real Chrome/CDP + Camoufox)
        # + Firecrawl (clean article/news markdown). RICHEST result wins; the slow
        # renders run in parallel so they add no latency to the fast path. The
        # deep engines are turn-budgeted (crawl_budget) to protect the renderers.
        nonlocal crawl_budget
        jobs = [("read", _extract(url))]
        # ALWAYS fan out across ALL web tools on EVERY
        # node/facet -- web_extract + crawl4ai (real Chrome/CDP + Camoufox) +
        # Firecrawl race on every fetch, even the quick action-feeding path
        # (which keeps its single PASS but no longer grounds on a thin homepage
        # when a renderer could pull the real article). Budget-bounded only to
        # protect the renderers from a runaway drill.
        if WEB_RESEARCH_CRAWL_FALLBACK and crawl_budget > 0:
            crawl_budget -= 1
            jobs += [("deep-crawl", _crawl(url)), ("firecrawl", _firecrawl(url))]
        outs = await asyncio.gather(*[j for _, j in jobs])
        # _extract returns str; _crawl/_firecrawl return (text, links). Normalise
        # + harvest the page's outbound links (article links for the 2-hop drill).
        cand: dict = {}
        links: list = []
        for (label, _), out in zip(jobs, outs):
            if isinstance(out, tuple):
                _txt, _lks = out
                cand[label] = _txt or ""
                links.extend(_lks or [])
            else:
                cand[label] = out or ""
        # PREFER Firecrawl's CLEAN markdown when it's substantial: it strips nav/
        # chrome (onlyMainContent), whereas crawl4ai often out-LENGTHS it with the
        # page's NAV MENU, so pure 'longest wins' picked junk -- operator
        # saw wikinews "Main menu / Newsroom / Recent changes"
        # boilerplate win. Fall back to the longest of the rest when Firecrawl is
        # thin/blocked. No hardcoded domains; purely engine-quality preference.
        fc = cand.get("firecrawl", "")
        if len(fc) >= WEB_RESEARCH_MIN_CHARS:
            return fc, "firecrawl", links
        best, eng = "", "read"
        for label, text in cand.items():
            if len(text) > len(best):
                best, eng = text, label
        return best, eng, links

    # Markdown link `[anchor](url)` -- crawl4ai/Camoufox returns the index page's
    # article links INLINE in the rendered markdown (not a links[] array), and the
    # anchor text IS the headline. NOT an image (`![..](..)`). Compiled once/turn.
    _md_link_re = re.compile(r"(?<!\!)\[([^\]]{0,200})\]\((https?://[^)\s]+)\)")

    def _rank_article_links(links: list, text: str, anchor: set,
                            src_url: str) -> list:
        # From an INDEX page, pick the most ARTICLE-LIKE URLs for the 2-hop drill --
        # by STRUCTURE ONLY, NO hardcoded domain/keyword/topic list (operator
        # binding). Candidates = the engine links[] PLUS every markdown
        # [headline](url) parsed from the rendered text; the module-level ranker
        # (_rank_links) scores a STORY (deep path, long hyphenated slug, a date/id
        # digit, a long real-headline anchor) above a shallow section/utility link,
        # with every weight/threshold SSOT from [web_research] (model/embed ranking
        # opt-in + degrade-open). A strong topical anchor (>=2 tokens) still requires
        # overlap (enforced inside _rank_links).
        cands: list = []   # (anchor_text, url)
        for it in (links or []):
            u = it if isinstance(it, str) else (
                (it.get("href") or it.get("url") or "") if isinstance(it, dict) else "")
            if u:
                cands.append(("", u.strip()))
        for m in _md_link_re.finditer(text or ""):
            cands.append((m.group(1).strip(), m.group(2).strip()))
        return _rank_links(cands, src_url, anchor)

    _md_any_re = re.compile(r"!?\[[^\]]*\]\([^)\s]*\)")

    def _strip_nav_chrome(md: str) -> str:
        # Strip NAV/MENU/footer chrome from rendered markdown (crawl4ai/Camoufox
        # keep it; Firecrawl's onlyMainContent already drops it). STRUCTURAL
        # link-density heuristic -- NO hardcoded selectors/keywords (operator
        # binding): a line that is MULTIPLE markdown links dominating its width
        # with almost no prose is chrome; a real heading or sentence (prose words)
        # is body and is kept. Conservative -- only clearly link-dominated lines
        # drop, so an in-prose citation link ("per [Reuters](u), ...") survives.
        # Run AFTER link harvest (which needs the raw links) -- see the loop below.
        if not md:
            return md
        out: list = []
        for ln in md.splitlines():
            s = ln.strip()
            if not s:
                out.append(ln)
                continue
            spans = _md_any_re.findall(s)
            link_chars = sum(len(x) for x in spans)
            prose = _md_any_re.sub(" ", s)
            prose_words = len(re.findall(r"[A-Za-z]{2,}", prose))
            if len(spans) >= 2 and link_chars >= 0.6 * len(s) and prose_words <= 6:
                continue   # link-dominated menu/nav/footer line -> drop
            out.append(ln)
        # Collapse the runs of blank lines the drops leave behind.
        _txt = "\n".join(out)
        return re.sub(r"\n{3,}", "\n\n", _txt).strip()

    # DIRECT URL EXTRACT ("Read <url>..." test gap): when the
    # request explicitly NAMES a url, FETCH THAT PAGE + cite it -- never web_search the
    # leftover verb ("read"/"open"), which anchored on the dictionary (merriam-webster
    # "read") and shipped junk sources. The named url IS the authoritative grounding;
    # skip the search entirely when it yields real content (no junk-anchor), else fall
    # through to the normal search.
    _named_urls = [u.rstrip('.,);]}>"\'') for u in _SRC_URL_RE.findall(
        f"{query or ''} {(refined or {}).get('refined_text') or ''}")]
    for _nu in _named_urls[:3]:
        if not _nu.startswith("http") or _nu in seen:
            continue
        seen.add(_nu)
        try:
            _ntxt = await _extract(_nu)
        except Exception:  # noqa: BLE001
            _ntxt = ""
        if _ntxt and len(_ntxt) >= WEB_RESEARCH_MIN_CHARS:
            content[_nu] = _strip_nav_chrome(_ntxt)
            touched.append({"url": _nu, "title": "named source", "content": ""})
            _src_record([{"url": _nu, "title": "named source"}])
            log.info("web-research: direct-extracted named url %s (%dB) -> skip search",
                     _nu, len(_ntxt))
        elif _ntxt:
            snippets[_nu] = _ntxt
            _src_record([{"url": _nu, "title": "named source"}])
    if content:   # a named url grounded the turn -> skip web_search (no junk-anchor)
        _max_att = 0

    for attempt in range(1, _max_att + 1):
        _rec({"emoji": "🔎", "label": "searching the web",
              "detail": (("news · " if _use_news else
                          (_time_range + " · " if _time_range else ""))
                         + search_q_now)[:72]})
        results = await _search(search_q_now, news=_use_news, time_range=_time_range)
        # RELEVANCE ANCHOR: drop results with ZERO topical overlap with the
        # ORIGINAL ask so an off-topic fan-out sub-query's hits (age calculators,
        # iCloud Find-My, discount-store junk) can't reach the grounding. Degrade
        # OPEN -- if nothing passes, keep all (junk beats an empty answer).
        if _anchor and results:
            _rel = [r for r in results if _shares_anchor(
                f"{r.get('title', '')} {r.get('url', '')} {r.get('content', '')}",
                _anchor)]
            if len(_rel) < len(results):
                log.info("web-research: anchor-filtered %d/%d off-topic results",
                         len(results) - len(_rel), len(results))
            # Keep ONLY the on-topic results. A WEAK anchor (<2 tokens) already
            # passed everything via _shares_anchor's degrade-open, so this is safe;
            # a STRONG anchor that matched NOTHING means the whole set is off-topic
            # junk -> ground on NOTHING so the agent answers from KNOWLEDGE (a clean
            # estimate) instead of summarising an Overstock / dictionary-'cheap'
            # page that slipped in (junk grounding < no
            # grounding for an all-junk facet).
            results = _rel
        ordered: list = []
        for r in (results or []):
            u = r.get("url", "")
            if u and u not in seen:
                ordered.append(r)
        # DROP bare-homepage results (no URL path AND no publishedDate) on EVERY
        # turn when better results exist ("MULTIPLE FAILURES":
        # research kept fetching site FRONT PAGES -- kayak.com/, cheapflights.com/,
        # local-dealer homepages for "Honda CRX", aggregator landings for
        # "trends" -- which yield only nav/marketing/UI chrome, NEVER the query's
        # data or article, so agents fabricated or punted). A path-bearing or
        # dated URL (.../flight-routes/..., /wiki/Honda_CRX, a news article)
        # carries real content. Keep ONLY those when ANY exist; else degrade
        # OPEN (a thin homepage still beats nothing -> no empty grounding).
        _pathful = [r for r in ordered
                    if r.get("publishedDate") or _url_has_path(r.get("url", ""))]
        if _pathful:
            # Keep article/dated URLs for direct reading PLUS the top homepage(s)
            # as 2-hop link SEEDS (mine the index for article
            # links, don't just drop it). The homepage's own thin chrome demotes to
            # a snippet below; its harvested article links carry the real stories.
            _homes = [r for r in ordered if r not in _pathful]
            ordered = _pathful + _homes[:2]
            if _homes:
                log.info("web-research: %d content URLs + %d index seed(s) for the "
                         "2-hop article drill", len(_pathful), min(len(_homes), 2))
        idx = 0
        for _p in range(1, WEB_RESEARCH_PASSES + 1):
            passes += 1
            batch = ordered[idx:idx + want]
            if not batch:
                break
            idx += len(batch)
            touched.extend(batch)
            for r in batch:
                seen.add(r.get("url", ""))
            fetched = await asyncio.gather(*[_fetch_all(r["url"]) for r in batch])
            _hop2: list = []   # article links harvested from index pages this batch
            for r, (best, eng, _links) in zip(batch, fetched):
                if eng != "read" and best:
                    n_crawled += 1
                if len(best) >= WEB_RESEARCH_MIN_CHARS:
                    # strip nav/menu chrome AFTER the link harvest below reads the
                    # raw `best` (the harvest needs the links the strip removes).
                    content[r["url"]] = _strip_nav_chrome(best)   # clean article body
                    _src_record([r])   # REAL article fetched -> a citable source
                elif best:
                    snippets[r["url"]] = best          # thin/blocked -> snippet
                    _src_record([r])   # thin but a real, fetched source
                _ttl = (str(r.get("title", "")).strip() or r.get("url", ""))[:60]
                # casual FUNCTION label, never the engine/tool name (operator
                # "not internal naming... indicative of the function")
                _rec({"emoji": "📖",
                      "label": ("reading the page deeply"
                                if eng in ("deep-crawl", "firecrawl")
                                else "reading the page"),
                      "detail": _ttl})
                # 2-HOP ARTICLE DRILL ("use the WHOLE web stack
                # ... drill into the stories, not the index"): when this page is an
                # INDEX (bare homepage URL or thin article body) but the engines
                # returned outbound links, harvest its top on-topic ARTICLE links so
                # the SAME concurrent engine race reads the actual stories next.
                _indexish = (not _url_has_path(r.get("url", ""))
                             or len(best) < WEB_RESEARCH_MIN_CHARS)
                if link_budget > 0 and _indexish and (_links or best):
                    _hop2.extend(_rank_article_links(
                        _links, best, _anchor, r.get("url", "")))
            # Drill the harvested article links through the FULL engine race
            # concurrently (bounded by link_budget + `want`), merging real article
            # bodies into the grounding alongside the directly-fetched results.
            _hop2 = [u for u in dict.fromkeys(_hop2)
                     if u not in seen][:max(0, min(link_budget, want))]
            if _hop2:
                link_budget -= len(_hop2)
                for u in _hop2:
                    seen.add(u)
                _drilled = await asyncio.gather(*[_fetch_all(u) for u in _hop2])
                for u, (best, eng, _l) in zip(_hop2, _drilled):
                    if eng != "read" and best:
                        n_crawled += 1
                    if len(best) >= WEB_RESEARCH_MIN_CHARS:
                        content[u] = _strip_nav_chrome(best)   # clean article body
                    elif best:
                        snippets[u] = best
                    touched.append({"url": u, "title": "story", "content": ""})
                    _rec({"emoji": "📖", "label": "reading the story",
                          "detail": u[:60]})
            if len(content) >= want:
                break
        # DEFINITION-OF-DONE: does what we hold actually ANSWER the query? If yes
        # (or attempts exhausted) stop; else re-search with the judge's sharper
        # query. This is the "loop until satisfied" -- model-driven, no hardcode.
        if attempt >= _max_att:
            break
        _gathered = "\n\n".join(
            ((content.get(r.get("url", "")) or snippets.get(r.get("url", ""))
              or str(r.get("content", "")))[:600]) for r in touched)[:5000]
        ok, better_q, scrape_url = await _judge_satisfied(query, _gathered)
        if ok:
            break
        # MODEL-PICKED SOURCE ("model picks the source"): the
        # judge names an authoritative page; Firecrawl-scrape it DIRECTLY, bypass-
        # ing the junk search results (e.g. wikinews) with a clean index/article.
        # No hardcoded source -- the model chose the URL. Best-effort.
        su = scrape_url.strip()
        _scraped = False
        if su.startswith(("http://", "https://")) and su not in seen:
            seen.add(su)
            _rec({"emoji": "📖", "label": "reading the best source",
                  "detail": su[:60]})
            _md, _ = await _firecrawl(su)
            if len(_md) >= WEB_RESEARCH_MIN_CHARS:
                content[su] = _strip_nav_chrome(_md)
                touched.append({"url": su, "title": "news source (judge-picked)",
                                "content": ""})
                _src_record([{"url": su, "title": "news source"}])  # citable source
                n_crawled += 1
                _scraped = True
        # Adopt the judge's sharper query ONLY if it stays ON-TOPIC. A weak judge
        # shown junk content drifts (it once drifted to an unrelated age-calculator
        # arithmetic query after being fed age-calculator pages); an off-anchor
        # re-search just fetches more junk, so keep the on-topic query for the next pass.
        _bq = better_q.strip() if better_q else ""
        _usable_bq = bool(_bq and _bq != search_q_now and _shares_anchor(_bq, _anchor))
        if _usable_bq:
            search_q_now = _bq
        elif _bq:
            log.info("web-research: dropped off-anchor re-search %r", better_q)
        # STOP DRILLING when the judge gave NO usable sharper query and we didn't
        # just fetch a judge-picked source: re-running the SAME query only hits the
        # seen-dedup (empty) and burns the attempt budget. This is what made an
        # UNSATISFIABLE ask ("cheap flights near me" -> the model can't fill the
        # location, so the judge is NEVER satisfied) run the full MAX_ATTEMPTS on
        # EVERY facet + deepen pass -> minutes with no answer.
        # We keep the on-topic grounding already gathered and let the agents answer.
        if not _usable_bq and not _scraped:
            log.info("web-research: no usable sharper query -> stop drilling "
                     "(gathered %d real / %d snippet)", len(content), len(snippets))
            break
        _rec({"emoji": "🔁", "label": f"retry {attempt + 1}",
              "detail": ("not answered -> " + search_q_now)[:60]})
    # ORDER the grounding so the BEST content LEADS (the
    # wikinews NAV boilerplate was [1]). Judge-picked authoritative sources first
    # (clean, requested precisely because the search results were junk), then
    # pages with REAL article bodies, then thin snippets last. Dedup by URL.
    def _rank(r: dict) -> tuple:
        u = r.get("url", "")
        picked = 0 if "judge-picked" in str(r.get("title", "")) else 1
        real = 0 if u in content else (1 if u in snippets else 2)
        return (picked, real)
    _ranked = sorted({r.get("url", ""): r for r in touched}.values(), key=_rank)
    blocks: list = []
    for i, r in enumerate(_ranked, start=1):
        u = r.get("url", "")
        title = str(r.get("title", "")).strip()
        body = (content.get(u) or snippets.get(u)
                or str(r.get("content", "")).strip())
        body = _clean_web_text(body)  # strip nav/image/share chrome before the cap
        if body:
            blocks.append(f"[{i}] {title} ({u})\n{body[:WEB_RESEARCH_BLOCK_CHARS]}")
    if not blocks:
        return ""
    log.info("web-research: %d results, %d real / %d snippet, %d deep-crawled "
             "over %d pass(es) for %.60r",
             len(touched), len(content), len(snippets), n_crawled, passes, query)
    # Stash stats for the live emitter (operator "fix emits"): name the FULL web
    # toolchain + real counts, not the old "SearXNG fan-out" under-sell.
    if isinstance(refined, dict):
        refined["_web_stats"] = {"sources": len(blocks), "real": len(content),
                                 "crawled": n_crawled, "passes": passes}
        refined["_web_steps"] = _steps
        # SOURCES survive the handoff ("this is why all
        # sources survive handoffs"): keep the [n] blocks (title + URL + text) so
        # the FINAL verity/answer pass can cite [n] + verify the draft against the
        # real fetched content -- not just the agents' paraphrase of it.
        refined["_web_sources"] = "\n\n".join(blocks)
    return ("LIVE WEB RESEARCH -- the MiOS pipeline ran its FULL web toolchain "
            "concurrently (SearXNG metasearch -> readable extract + crawl4ai/"
            "Chrome-CDP & Camoufox deep render) and FETCHED the top pages below. "
            "ANSWER THE USER DIRECTLY FROM THIS REAL CONTENT: synthesise the "
            "actual stories / facts / developments across the sources and cite "
            "[n] inline. The DATED items below ARE the answer -- a story from the "
            "last days or weeks fully counts as 'recent' / 'this week' / 'latest' "
            "/ 'today'; present what you found, with its date. Do NOT PUNT: never "
            "reply 'no stories were found', 'no specific developments', 'consult "
            "reliable sources', or tell the user to check elsewhere WHEN the "
            "content below contains relevant facts -- that is a FAILED answer. "
            "Lead with the concrete findings; if one specific sub-detail is "
            "genuinely absent, give everything that IS here and note only that "
            "one gap. Do NOT just list source homepages. "
            "BUT do the OPPOSITE check too: if the content "
            "below is IRRELEVANT to the question -- unrelated files, dictionary "
            "entries, marketing/homepage text, or documents that merely CONTAIN a "
            "query word (e.g. a spreadsheet that happens to contain 'mios', a "
            "dictionary def of 'list', a clothing brand named 'Next') -- do NOT "
            "bend it into an answer and do NOT cite it. Say plainly the fetched "
            "sources did not cover the question, then answer from your own "
            "reliable knowledge if you have it, else say it isn't available. "
            "Forcing an answer out of irrelevant data is as wrong as fabricating "
            "one; NEVER invent a system spec, price, or fact the content lacks:\n\n"
            + "\n\n".join(blocks))


# ── Per-turn web-SOURCE registry + citation rendering ─────────────────────
# Relocated VERBATIM from server.py: the cross-turn web-source registry and
# the citation renderers/harvesters. This module already OWNS the web toolchain
# and calls _src_record as it fetches, so home is here. server.py re-imports
# every name under its EXACT original alias (surface-parity zero-diff) and
# injects the request contextvars (_sources_var/_conv_key_var/_src_turn_var),
# the module-level registry dict (_SOURCES_REGISTRY) + its caps, MAX_SOURCES,
# and _url_has_path via configure(). The _SRC_LINE_RE/_SRC_URL_RE parsers and
# _src_record are now NATIVE here -- no longer injected.
def _src_turn_key() -> str:
    """Stable per-turn key shared by the primary + every council/DAG secondary.
    Prefers the explicit turn-id (propagated to sub-requests) over the per-request
    conv key, so a re-entrant secondary records into the parent turn's bucket."""
    try:
        _t = _src_turn_var.get()
        if _t:
            return str(_t)
    except Exception:  # noqa: BLE001
        pass
    try:
        return str(_conv_key_var.get() or "")
    except Exception:  # noqa: BLE001
        return ""


def _src_turn_init() -> None:
    """Open a fresh registry bucket for THIS turn (call once at chat_completions
    entry, after _conv_key_var is set). Trims the registry to its cap."""
    _k = _src_turn_key()
    if not _k:
        return
    _SOURCES_REGISTRY[_k] = []
    if len(_SOURCES_REGISTRY) > _SOURCES_REGISTRY_CAP:
        try:  # drop oldest insertion-ordered entries (dict preserves order)
            for _old in list(_SOURCES_REGISTRY.keys())[:-_SOURCES_REGISTRY_CAP]:
                _SOURCES_REGISTRY.pop(_old, None)
        except Exception:  # noqa: BLE001
            pass


def _src_record(items) -> None:
    """Record real (title,url) pairs from a web_search/extract result list into BOTH
    the turn-scoped contextvar bucket AND the module-level registry (keyed by the
    turn key) so the parent finalize sees sources collected by child agents too.
    Degrade-open: odd shape / no turn key -> safe no-op."""
    if not items:
        return
    _bucket = _sources_var.get()
    _reg = _SOURCES_REGISTRY.get(_src_turn_key()) if _src_turn_key() else None
    if _bucket is None and _reg is None:
        return
    try:
        _added = 0
        for _it in items:
            if not isinstance(_it, dict):
                continue
            _u = str(_it.get("url") or _it.get("link") or "").strip()
            # Strip trailing junk a model leaks onto a URL (an escaped line-break
            # '\', markdown/sentence punctuation) so 'url' and 'url\' don't survive
            # as two un-deduped citations.
            _u = _u.rstrip("\\").rstrip(".,;:)]}>\"'").rstrip("\\")
            _t = str(_it.get("title") or _it.get("name") or "").strip()
            if not _u.startswith("http"):
                continue
            if _bucket is not None:
                _bucket.append((_t, _u))
            if _reg is not None:
                _reg.append((_t, _u))
            _added += 1
        if _added:
            log.debug("src: recorded %d into turn %s", _added, _src_turn_key()[:40])
    except Exception:  # noqa: BLE001 -- never break tool execution
        pass


def _src_collected() -> list:
    """Deduped (by url, order-preserved) sources from the contextvar bucket AND the
    turn registry (cross-agent), capped to MAX_SOURCES."""
    _merged: list = []
    _b = _sources_var.get()
    if _b:
        _merged.extend(_b)
    _r = _SOURCES_REGISTRY.get(_src_turn_key()) if _src_turn_key() else None
    if _r:
        _merged.extend(_r)
    if not _merged:
        return []
    # Prefer real ARTICLE URLs (path-bearing) over bare homepages -- a judge-picked
    # lite news index or a generic 'cnn.com/' is a weak citation; keep them ONLY
    # when no article URL was collected (degrade-open, never strip to empty).
    _pathful = [(_t, _u) for (_t, _u) in _merged if _url_has_path(_u)]
    _use = _pathful if _pathful else _merged
    _seen: set = set()
    _out: list = []
    for _t, _u in _use:
        if _u in _seen:
            continue
        _seen.add(_u)
        _out.append((_t, _u))
        if len(_out) >= MAX_SOURCES:
            break
    return _out


def _sources_markdown(refs: list) -> str:
    """A deterministic '**Sources:**' markdown list of the REAL urls (numbered)."""
    if not refs:
        return ""
    return "\n\n**Sources:**\n" + "\n".join(
        f"{i + 1}. {(_t or _u)[:90]} — {_u}" for i, (_t, _u) in enumerate(refs))


def _sources_metadata(refs: list) -> list:
    """Structured citation metadata (operator 'A2A or metadata'): real {n,title,url}
    objects attached to the response so clients render citations from REAL sources."""
    return [{"n": i + 1, "title": _t, "url": _u} for i, (_t, _u) in enumerate(refs)]


def _sources_annotations(refs: list, text: str) -> list:
    """OpenAI url_citation annotations (Chat/Responses parity): one
    {type:'url_citation', url, title, start_index, end_index} per cited source.
    start/end are char offsets into `text` where the URL appears inline (so a UI
    renders a clickable cite); 0/0 when the source is a turn-source not inlined.
    This is OpenAI's canonical citation contract -- attaching it lets MiOS clients
 render web citations the same way ChatGPT does. web-tools hardening."""
    out: list = []
    _txt = text or ""
    for _ref in (refs or []):
        try:
            _t, _u = _ref
        except (ValueError, TypeError):
            continue
        if not _u:
            continue
        _i = _txt.find(_u)
        out.append({
            "type": "url_citation",
            "url": _u,
            "title": (_t or _u),
            "start_index": (_i if _i >= 0 else 0),
            "end_index": (_i + len(_u) if _i >= 0 else 0),
        })
    return out


def _filter_relevant_sources(refs: list, *texts: str) -> list:
    """OpenAI grounding rule: 'include only search results/citations that support
    the cited response text -- irrelevant sources permanently degrade user trust.'
    Keep a source only when its title shares a content word (>=4 chars) with the
    answer/query, OR its registrable-domain stem appears in them. DEGRADE-OPEN: if
    the filter would drop EVERYTHING (the answer echoed no source token), return the
    originals -- never strip citations to empty. Kills the off-topic-source bleed
 (a Fedora answer citing 'Shaolin monks'). web-tools hardening."""
    if not refs:
        return refs
    _blob = " ".join(t for t in texts if t).lower()
    if not _blob:
        return refs
    _kept: list = []
    for _ref in refs:
        try:
            _t, _u = _ref
        except (ValueError, TypeError):
            continue
        _dom = re.sub(r"^https?://(www\.)?", "", str(_u or "")).split("/")[0].lower()
        _stem = _dom.split(".")[0] if _dom else ""
        _words = set(re.findall(r"[a-z0-9]{4,}", str(_t or "").lower()))
        if (_stem and len(_stem) >= 4 and _stem in _blob) or any(_w in _blob for _w in _words):
            _kept.append((_t, _u))
    return _kept if _kept else refs


# Parse a sub-agent's appended '**Sources:**\nN. title — url' block (or any bare
# http URLs) back into citable items. A council/DAG facet is dispatched to a leaf
# agent (hermes/opencode) that re-calls :8640 WITHOUT the turn-id header, so its
# real web sources live in ITS OWN turn bucket -- but they ALSO ride back in its
# answer's appended Sources list (or its mios_sources JSON). The parent harvests
# them here, in the PARENT turn context, so they unify into the final citation set.
_SRC_LINE_RE = re.compile(
    r"^\s*\d+\.\s+(.*?)\s+[—\-]+\s+(https?://\S+?)\s*$", re.MULTILINE)
_SRC_URL_RE = re.compile(r"https?://[^\s\)\]\}<>\"']+")


def _src_record_from_text(text: str) -> None:
    """Harvest sources from an answer's appended Sources block; fall back to bare
    URLs only if no numbered block is present. Records into the current turn bucket."""
    if not text or "http" not in text:
        return
    _items = [{"title": _m.group(1).strip(), "url": _m.group(2).strip()}
              for _m in _SRC_LINE_RE.finditer(text)]
    if not _items:
        _items = [{"title": "", "url": _u} for _u in _SRC_URL_RE.findall(text)]
    if _items:
        _src_record(_items)


def _harvest_sub_sources(rj, content: str) -> None:
    """Pull a dispatched sub-agent's REAL sources into the parent turn: prefer the
    structured mios_sources JSON (survives when the leaf passes custom fields
    through), else parse the answer's appended Sources block / bare URLs."""
    try:
        _ms = rj.get("mios_sources") if isinstance(rj, dict) else None
    except Exception:  # noqa: BLE001
        _ms = None
    if _ms:
        _src_record(_ms)
        return
    _src_record_from_text(content or "")
