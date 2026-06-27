# AI-hint: Tiered local web-EXTRACT `WebSearchProvider` for Hermes-Agent: fast offline urllib+regex strip first, escalating JS-heavy/dynamic/thin pages to crawl4ai (headless Chrome over CDP + Camoufox stealth retry) via mios-crawl. No cloud, no firecrawl SDK.
# AI-related: mios-firecrawl, mios-web-extract, mios-crawl, mios-crawl4ai, mios-hermes-browser
# AI-functions: _fetch_one, _crawl_one, name, display_name, is_available, supports_search, supports_extract, extract, class MiosFetchProvider
"""MiOS tiered web-EXTRACT provider for Hermes-Agent.

Why this exists (operator-confirmed): hermes's bundled `firecrawl`
web provider pins the firecrawl-py v4 SDK (firecrawl API v2, POST /v2/scrape),
but MiOS self-hosts an OLDER firecrawl container (mios-firecrawl:v1.0.0, v1
API) -> every web_extract 404s and research turns can never drill past search-
result homepages. tavily/exa/parallel are CLOUD providers (need keys; violate
MiOS full-offline). So this provider grounds extraction in the LOCAL stack only.

Tiering ("web_search should also use crawl4ai and Chrome
CDP, not just firecrawl/searxng"):
  Tier 1 -- fast stdlib urllib fetch + readability HTML->text strip (the proven
            mios-web-extract path). Handles the common static-page case in ~1-2s,
            fully offline.
  Tier 2 -- when urllib yields THIN content (a JS shell / dynamic / blocked page
            < MIOS_MIOSFETCH_CRAWL_MIN_CHARS), escalate the SAME url to crawl4ai
            via `mios-crawl` (headless Chrome over CDP at :9222 + a Camoufox
            stealth-Firefox fail-retry). This is the rich reader urllib can't do
            (renders JS, defeats simple anti-bot). Keep whichever tier yields
            more real content; crawl4ai unavailable/failed -> keep the urllib
            result (never regress, stays offline-capable).

Selected via web.extract_backend: miosfetch in config.yaml. searxng still
handles web_search. Implements agent.web_search_provider.WebSearchProvider
(extract only).
"""
from __future__ import annotations

import asyncio
import html as _html
import json as _json
import os
import re
import shutil
import subprocess
import urllib.request
from typing import Any, Dict, List, Optional

from agent.web_search_provider import WebSearchProvider

# Boilerplate containers stripped WITH their contents (never the article body).
_DROP = re.compile(
    r"(?is)<(script|style|head|nav|footer|aside|svg|noscript|form|button|"
    r"select|dialog|iframe|template)\b[^>]*>.*?</\1>")
# Main-content containers -- prefer the largest <article>/<main> subtree so
# site chrome (menus, promos, section lists) is dropped (the news-page win).
_MAIN = re.compile(r"(?is)<(?:article|main)\b[^>]*>(.*?)</(?:article|main)>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_TAGS = re.compile(r"(?s)<[^>]+>")

# Tier-2 escalation knobs (SSOT-overridable; defaults work offline). When urllib
# extracts fewer than MIN_CHARS of text the page is treated as a JS shell /
# dynamic / blocked page and re-read via crawl4ai (CDP + Camoufox).
_CRAWL_BIN = shutil.which("mios-crawl") or "/usr/libexec/mios/mios-crawl"
_CRAWL_ENABLE = os.environ.get(
    "MIOS_MIOSFETCH_CRAWL", "true").strip().lower() in {"1", "true", "yes", "on"}
_CRAWL_MIN_CHARS = int(os.environ.get("MIOS_MIOSFETCH_CRAWL_MIN_CHARS", "500"))
_CRAWL_TIMEOUT = float(os.environ.get("MIOS_MIOSFETCH_CRAWL_TIMEOUT", "55"))


def _fetch_one(url: str, max_chars: int, timeout: float) -> Dict[str, Any]:
    """Tier 1: fetch ONE url via stdlib urllib + readability strip. Mirrors
    mios-web-extract; never fabricates -- on failure returns an error field
    with empty content."""
    if not re.match(r"^https?://", url):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (MiOS web_extract; +local)",
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(3_000_000)  # cap the download
        page = raw.decode("utf-8", "replace")
        tm = _TITLE.search(page)
        title = _html.unescape(_TAGS.sub(" ", tm.group(1))).strip() if tm else ""
        body = _DROP.sub(" ", page)
        mains = _MAIN.findall(body)
        if mains:
            biggest = max(mains, key=len)
            if len(biggest) > 500:   # only when the marked region is the real body
                body = biggest
        text = _html.unescape(_TAGS.sub(" ", body))
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()[:max_chars]
        return {
            "url": url, "title": title, "content": text,
            "raw_content": text, "metadata": {"extractor": "miosfetch"},
        }
    except Exception as e:  # be HONEST -- never invent page content
        return {
            "url": url, "title": "", "content": "", "raw_content": "",
            "error": f"miosfetch failed: {e}", "metadata": {"extractor": "miosfetch"},
        }


def _crawl_one(url: str, max_chars: int, timeout: float) -> Optional[Dict[str, Any]]:
    """Tier 2: re-read a JS-heavy/dynamic/blocked page via crawl4ai (headless
    Chrome over CDP + Camoufox stealth retry) by shelling to `mios-crawl`, which
    already does the engine orchestration and returns clean markdown. Returns the
    WebSearchProvider extract dict, or None when crawl4ai is unavailable/failed
    (the caller then keeps the urllib result -- never regress, stays offline)."""
    if not _CRAWL_ENABLE or not _CRAWL_BIN:
        return None
    if not re.match(r"^https?://", url):
        url = "https://" + url
    try:
        p = subprocess.run(
            [_CRAWL_BIN, url], capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "").strip()
        if not out:
            return None
        d = _json.loads(out)
        if not d.get("success"):
            return None
        md = (d.get("markdown") or "").strip()
        if not md:
            return None
        return {
            "url": url, "title": (d.get("title") or "").strip(),
            "content": md[:max_chars], "raw_content": md[:max_chars],
            "metadata": {"extractor": "crawl4ai", "engine": d.get("engine")},
        }
    except Exception:
        # crawl4ai down / mios-crawl missing / timeout -> graceful: keep urllib.
        return None


class MiosFetchProvider(WebSearchProvider):
    """Tiered extract-only provider: urllib (offline) -> crawl4ai (CDP) escalation."""

    @property
    def name(self) -> str:
        return "miosfetch"

    @property
    def display_name(self) -> str:
        return "MiOS tiered fetch (offline urllib -> crawl4ai/CDP escalation)"

    def is_available(self) -> bool:
        return True  # urllib tier is pure stdlib; always usable (crawl4ai is a bonus)

    def supports_search(self) -> bool:
        return False  # searxng handles web_search

    def supports_extract(self) -> bool:
        return True

    async def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        max_chars = int(kwargs.get("max_chars") or 8000)
        timeout = float(kwargs.get("timeout") or 15.0)
        if isinstance(urls, str):
            urls = [urls]

        async def _one(u: str) -> Dict[str, Any]:
            # Tier 1: fast offline urllib.
            base = await asyncio.to_thread(_fetch_one, u, max_chars, timeout)
            content = base.get("content") or ""
            # Tier 2: thin/JS/blocked -> escalate to crawl4ai (CDP + Camoufox).
            # Keep whichever tier returns more real content.
            if len(content) < _CRAWL_MIN_CHARS:
                rich = await asyncio.to_thread(_crawl_one, u, max_chars, _CRAWL_TIMEOUT)
                if rich and len(rich.get("content") or "") > len(content):
                    return rich
            return base

        return list(await asyncio.gather(*[_one(u) for u in urls]))
