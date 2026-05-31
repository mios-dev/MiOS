"""MiOS offline direct-fetch web-EXTRACT provider for Hermes-Agent.

Why this exists (operator-confirmed 2026-05-31): hermes's bundled `firecrawl`
web provider pins the firecrawl-py v4 SDK (firecrawl API v2, POST /v2/scrape),
but MiOS self-hosts an OLDER firecrawl container (mios-firecrawl:v1.0.0, v1
API) -> every web_extract 404s and research turns can never drill past search-
result homepages. tavily/exa/parallel are CLOUD providers (need keys; violate
MiOS full-offline). So this provider does what the proven `mios-web-extract`
verb already does: a plain stdlib urllib fetch + readability HTML->text strip.
No firecrawl, no SDK, no container coupling, no version fragility -- works
fully offline against any reachable URL. Selected via web.extract_backend:
miosfetch in config.yaml. searxng still handles web_search.

Implements the agent.web_search_provider.WebSearchProvider ABC (extract only).
"""
from __future__ import annotations

import asyncio
import html as _html
import re
import urllib.request
from typing import Any, Dict, List

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


def _fetch_one(url: str, max_chars: int, timeout: float) -> Dict[str, Any]:
    """Fetch ONE url and return the WebSearchProvider extract-result dict.
    Mirrors mios-web-extract's readability strip; never fabricates -- on
    failure returns an error field with empty content."""
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


class MiosFetchProvider(WebSearchProvider):
    """Extract-only provider: stdlib fetch + readability strip (offline)."""

    @property
    def name(self) -> str:
        return "miosfetch"

    @property
    def display_name(self) -> str:
        return "MiOS direct fetch (offline readability extract)"

    def is_available(self) -> bool:
        return True  # pure stdlib; no env/dep/network check needed

    def supports_search(self) -> bool:
        return False  # searxng handles web_search

    def supports_extract(self) -> bool:
        return True

    async def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        max_chars = int(kwargs.get("max_chars") or 8000)
        timeout = float(kwargs.get("timeout") or 15.0)
        if isinstance(urls, str):
            urls = [urls]
        results = await asyncio.gather(
            *[asyncio.to_thread(_fetch_one, u, max_chars, timeout) for u in urls])
        return list(results)
