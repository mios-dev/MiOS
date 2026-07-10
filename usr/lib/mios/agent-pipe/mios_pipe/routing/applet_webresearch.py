# AI-hint: Web-research SSE applet -- app-ifies the "Discovery / resolution" verb cluster (web_search/web_extract/crawl) as an HTML-over-SSE applet that streams progressively into the Gecko portal's iframe-applet shell (the slot the Configurator already occupies). Reuses the SAME transport as the chat pane (StreamingResponse text/event-stream) and the SAME dispatch chokepoint (dispatch_mios_verb via the configure() DI seam) -- no new language, image, or toolchain. `stream_webresearch(query, dispatch)` is a pure async generator (FastAPI-free) so it is unit-testable in isolation; build_router() wraps it for the portal; server.py mounts it with app.include_router(build_router()) after calling configure(dispatch=dispatch_mios_verb). Named SSE events (status/result/error/done) carry HTML fragments that htmx's SSE extension (hx-ext=sse, sse-swap) patches into the DOM one result at a time.
# AI-related: ./portal.py, ./sse.py, ./chat.py, ../../mios_dispatch.py, ./verbcatalog.py, test_mios_applet_webresearch.py
# AI-functions: configure, _sse, _li, _extract_results, stream_webresearch, build_router
"""Web-research verb cluster streamed as HTML-over-SSE into the portal (app-ification mechanism #3)."""

# NOTE: deliberately NOT `from __future__ import annotations` -- FastAPI resolves
# handler param types by object, and stringized annotations would leave `request:
# Request` (Request imported inside build_router) unresolvable -> FastAPI would
# validate `request` as a query field and 422 every route.

import html
import json
from typing import Any, Awaitable, Callable, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse

# ── DI seam (configure) ─ server.py injects the real dispatch_mios_verb + an
# auth predicate, exactly like every other mios_pipe module. Kept optional so
# the module imports (and unit-tests) with zero server state.
_dispatch: Optional[Callable[..., Awaitable[dict]]] = None
_authed: Optional[Callable[[Any], bool]] = None


def configure(*, dispatch: Optional[Callable[..., Awaitable[dict]]] = None,
              authed: Optional[Callable[[Any], bool]] = None) -> None:
    global _dispatch, _authed
    if dispatch is not None:
        _dispatch = dispatch
    if authed is not None:
        _authed = authed


def _sse(event: str, data: str) -> str:
    """One SSE frame: a named event + one `data:` line per line of the HTML
    fragment (multi-line data is legal only as repeated data: lines)."""
    body = "\n".join("data: " + ln for ln in data.split("\n"))
    return f"event: {event}\n{body}\n\n"


def _li(title: str, url: str, snippet: str = "") -> str:
    """Render one result as an escaped <li> (XSS-safe -- AI/scraped content is
    never trusted raw; the portal streams these straight into the live DOM)."""
    t = html.escape(title or url or "(result)")
    u = html.escape(url or "#")
    s = html.escape(snippet or "")
    return (f'<li class="mios-wr-item"><a href="{u}" target="_blank" '
            f'rel="noopener noreferrer">{t}</a>'
            f'{("<p class=\"mios-wr-snip\">" + s + "</p>") if s else ""}</li>')


def _extract_results(res: Any) -> list:
    """Normalize a web_search dispatch result into a list of {title,url,snippet}
    dicts, tolerating the several shapes a verb cmd can return (envelope dict,
    JSON-in-stdout, bare list)."""
    def _from_dict(d: dict) -> Optional[list]:
        for k in ("results", "data", "hits", "items"):
            v = d.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        return None
    if isinstance(res, dict):
        got = _from_dict(res)
        if got is not None:
            return got
        for k in ("output", "stdout", "result"):
            v = res.get(k)
            if isinstance(v, str) and v.strip():
                try:
                    j = json.loads(v)
                except (ValueError, TypeError):
                    continue
                if isinstance(j, list):
                    return [x for x in j if isinstance(x, dict)]
                if isinstance(j, dict):
                    got = _from_dict(j)
                    if got is not None:
                        return got
    if isinstance(res, list):
        return [x for x in res if isinstance(x, dict)]
    return []


async def stream_webresearch(query: str, dispatch: Callable[..., Awaitable[dict]],
                             *, limit: int = 5):
    """Async generator of SSE HTML frames for one web-research query. Pure of
    FastAPI so it is unit-testable: pass any `dispatch(tool, args) -> awaitable
    dict`. Emits: status (progress), result (one <li> per hit), error, done."""
    q = (query or "").strip()
    if not q:
        yield _sse("error", '<p class="mios-wr-err">empty query</p>')
        yield _sse("done", "")
        return
    yield _sse("status", f'<p class="mios-wr-status">searching &ldquo;{html.escape(q)}&rdquo;&hellip;</p>')
    try:
        res = await dispatch("web_search", {"query": q, "limit": limit})
    except Exception as exc:  # noqa: BLE001 -- surface any dispatch failure to the pane
        yield _sse("error", f'<p class="mios-wr-err">search failed: {html.escape(str(exc))}</p>')
        yield _sse("done", "")
        return
    results = _extract_results(res)
    if not results:
        yield _sse("status", '<p class="mios-wr-status">no results.</p>')
    n = 0
    for r in results[:limit]:
        n += 1
        yield _sse("result", _li(r.get("title") or r.get("name"),
                                 r.get("url") or r.get("link") or r.get("href"),
                                 r.get("snippet") or r.get("description") or r.get("content")))
    yield _sse("status", f'<p class="mios-wr-status">done &mdash; {n} result(s).</p>')
    yield _sse("done", "")


# The applet HTML fragment: htmx SSE extension patches named events into #mios-wr-out.
_APPLET_HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="/portal/theme.css">
<link rel="stylesheet" href="/branding/mios-app-shell.css">
<script src="/portal/vendor/htmx.min.js"></script>
<script src="/portal/vendor/htmx-sse.min.js"></script></head>
<body class="mios-window"><div class="mios-titlebar">Web Research</div>
<form class="mios-panel" hx-get="/portal/app/webresearch/render" hx-target="#mios-wr-out" hx-swap="innerHTML">
  <input name="q" class="mios-input" placeholder="search the web&hellip;" autofocus>
  <button class="mios-btn" type="submit">Search</button>
</form>
<ul id="mios-wr-out" class="mios-panel mios-wr-list"></ul>
</body></html>"""


# ── Module-level router (server.py mounts it via app.include_router(router)) ──
# MUST be module-level with static @router.get decorators: the AST surface
# projector (mios_surface.project_package -> gate check 15 AND test_mios_approutes'
# live-app parity) only discovers routes that are statically visible. Routes hidden
# inside a function are invisible to the projector yet served by the live app, so
# the two route-parity gates disagree (the live app has "extra" routes). Matches the
# established dispatch_router / a2a_router pattern.
router = APIRouter()


@router.get("/portal/app/webresearch")
async def _page(request: Request):
    if _authed is not None and not _authed(request):
        return HTMLResponse("unauthorized", status_code=401)
    return HTMLResponse(_APPLET_HTML)


@router.get("/portal/app/webresearch/render")
async def _render(request: Request, q: str = ""):
    # htmx swaps this <div>, which then opens the SSE connection to stream results.
    if _authed is not None and not _authed(request):
        return HTMLResponse("unauthorized", status_code=401)
    qq = html.escape(q or "")
    frag = (f'<div hx-ext="sse" sse-connect="/portal/app/webresearch/stream?q={qq}" '
            f'sse-swap="result" hx-swap="beforeend"><li class="mios-wr-status" '
            f'sse-swap="status" hx-swap="innerHTML"></li></div>')
    return HTMLResponse(frag)


@router.get("/portal/app/webresearch/stream")
async def _stream(request: Request, q: str = ""):
    if _authed is not None and not _authed(request):
        return HTMLResponse("unauthorized", status_code=401)
    dispatch = _dispatch
    if dispatch is None:
        async def _nodispatch(_t, _a):
            raise RuntimeError("web-research applet not configured (no dispatch)")
        dispatch = _nodispatch

    async def _gen():
        async for frame in stream_webresearch(q, dispatch):
            yield frame

    return StreamingResponse(_gen(), media_type="text/event-stream")


def build_router():
    """Back-compat: the router is module-level; return it for app.include_router."""
    return router
