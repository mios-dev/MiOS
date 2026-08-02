# AI-hint: Worker-tool surface assembly + child-tool selection extracted from server.py.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/routing/toolsurface.py
"""Worker tool surface and child tool selection module."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from mios_pipe.memory.worker_tools import (
    _fuse_then_diversify,
    _is_core_tool,
    _priority_fallback_score,
    _tok,
    _tool_priority,
    _ensure_verb_lexicon,
)

log = logging.getLogger("mios-agent-pipe")

_WORKER_TOOLS_CACHE: Optional[list] = None
_WORKER_TOOLS_FULL_CACHE: Optional[list] = None
_WORKER_TOOLS_CORE_CACHE: Optional[list] = None

WORKER_TOOLS_SCOPE = "all"
CHILD_TOOL_SELECT = True
STABLE_PREFIX = True
STABLE_PREFIX_TAIL = 15
CHILD_TOOL_FLOOR = 6

CODE_MODE_ENABLE = False

_VERB_CATALOG: dict = {}
_RECIPE_CATALOG: dict = {}
_ROUTING_DOMAINS: dict = {}
_routed_domain_var = None
_DISPATCH_TOML: dict = {}

_MCP_CLIENT_LOCK: Optional[asyncio.Lock] = None
_MCP_CLIENT_TOOLS: dict = {}
_VERB_EMBEDDINGS: dict = {}

_verb_to_openai_tool = None
_recipe_to_openai_tool = None
_skill_to_openai_tool = None
_mcp_tool_to_openai_tool = None
_skill_list = None
_resolve_verb_key = None
_tool_embedding = None
_cosine = None
_ensure_verb_embeddings = None
_embed_one = None


def configure(*, worker_tools_scope=None, child_tool_select=None,
              stable_prefix=None, stable_prefix_tail=None,
              child_tool_floor=None, verb_catalog=None, recipe_catalog=None,
              routing_domains=None, routed_domain_var=None, dispatch_toml=None,
              mcp_client_lock=None, mcp_client_tools=None,
              verb_embeddings=None, verb_to_openai_tool=None,
              recipe_to_openai_tool=None, skill_to_openai_tool=None,
              mcp_tool_to_openai_tool=None, skill_list=None,
              resolve_verb_key=None, tool_embedding=None, cosine=None,
              ensure_verb_embeddings=None, embed_one=None,
              code_mode_enable=None) -> None:
    """Inject catalogs, config, and helper callbacks."""
    global WORKER_TOOLS_SCOPE, CHILD_TOOL_SELECT, STABLE_PREFIX
    global STABLE_PREFIX_TAIL, CHILD_TOOL_FLOOR, _VERB_CATALOG
    global _RECIPE_CATALOG, _ROUTING_DOMAINS, _routed_domain_var
    global _DISPATCH_TOML, _MCP_CLIENT_LOCK, _MCP_CLIENT_TOOLS
    global _VERB_EMBEDDINGS, _verb_to_openai_tool, _recipe_to_openai_tool
    global _skill_to_openai_tool, _mcp_tool_to_openai_tool, _skill_list
    global _resolve_verb_key, _tool_embedding, _cosine
    global _ensure_verb_embeddings, _embed_one, CODE_MODE_ENABLE
    global _WORKER_TOOLS_CACHE, _WORKER_TOOLS_FULL_CACHE, _WORKER_TOOLS_CORE_CACHE

    _WORKER_TOOLS_CACHE = None
    _WORKER_TOOLS_FULL_CACHE = None
    _WORKER_TOOLS_CORE_CACHE = None

    if worker_tools_scope is not None:
        WORKER_TOOLS_SCOPE = worker_tools_scope
    if child_tool_select is not None:
        CHILD_TOOL_SELECT = child_tool_select
    if stable_prefix is not None:
        STABLE_PREFIX = stable_prefix
    if stable_prefix_tail is not None:
        STABLE_PREFIX_TAIL = stable_prefix_tail
    if child_tool_floor is not None:
        CHILD_TOOL_FLOOR = child_tool_floor
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if recipe_catalog is not None:
        _RECIPE_CATALOG = recipe_catalog
    if routing_domains is not None:
        _ROUTING_DOMAINS = routing_domains
    if routed_domain_var is not None:
        _routed_domain_var = routed_domain_var
    if dispatch_toml is not None:
        _DISPATCH_TOML = dispatch_toml
    if mcp_client_lock is not None:
        _MCP_CLIENT_LOCK = mcp_client_lock
    if mcp_client_tools is not None:
        _MCP_CLIENT_TOOLS = mcp_client_tools
    if verb_embeddings is not None:
        _VERB_EMBEDDINGS = verb_embeddings
    if verb_to_openai_tool is not None:
        _verb_to_openai_tool = verb_to_openai_tool
    if recipe_to_openai_tool is not None:
        _recipe_to_openai_tool = recipe_to_openai_tool
    if skill_to_openai_tool is not None:
        _skill_to_openai_tool = skill_to_openai_tool
    if mcp_tool_to_openai_tool is not None:
        _mcp_tool_to_openai_tool = mcp_tool_to_openai_tool
    if skill_list is not None:
        _skill_list = skill_list
    if resolve_verb_key is not None:
        _resolve_verb_key = resolve_verb_key
    if tool_embedding is not None:
        _tool_embedding = tool_embedding
    if cosine is not None:
        _cosine = cosine
    if ensure_verb_embeddings is not None:
        _ensure_verb_embeddings = ensure_verb_embeddings
    if embed_one is not None:
        _embed_one = embed_one
    if code_mode_enable is not None:
        CODE_MODE_ENABLE = code_mode_enable


def _worker_tools_surface() -> list:
    """The MiOS verb + RECIPE catalog in OpenAI tools[] shape (SYNC)."""
    global _WORKER_TOOLS_CACHE
    if _WORKER_TOOLS_CACHE is None:
        try:
            out = []
            if _verb_to_openai_tool and _VERB_CATALOG:
                out = [
                    _verb_to_openai_tool(n, c)
                    for n, c in _VERB_CATALOG.items()
                    if not c.get("hidden")
                    and (WORKER_TOOLS_SCOPE != "read"
                         or str(c.get("permission", "")).lower() == "read")
                ]
            if _recipe_to_openai_tool and _RECIPE_CATALOG and not CODE_MODE_ENABLE:
                for rn, rc in (_RECIPE_CATALOG or {}).items():
                    if (WORKER_TOOLS_SCOPE == "read"
                            and str(rc.get("permission", "")).lower() != "read"):
                        continue
                    out.append(_recipe_to_openai_tool(rn, rc))
            _WORKER_TOOLS_CACHE = out
        except Exception:
            _WORKER_TOOLS_CACHE = []
    return _WORKER_TOOLS_CACHE


async def _worker_tools_surface_async(cap: int = 0, intent: str = "") -> list:
    """The COMPLETE worker tool surface -- verbs + recipes + SKILLS (ASYNC)."""
    global _WORKER_TOOLS_FULL_CACHE, _WORKER_TOOLS_CORE_CACHE
    if _WORKER_TOOLS_FULL_CACHE is None:
        base = list(_worker_tools_surface())
        if WORKER_TOOLS_SCOPE != "read" and _skill_list and _skill_to_openai_tool:
            try:
                rows = (await _skill_list(status="promoted")) or []
                for srow in rows:
                    base.append(_skill_to_openai_tool(srow))
            except Exception:
                log.debug("worker skills surface fetch failed; verbs+recipes only")
        if str(os.environ.get("MIOS_WORKER_MCP_TOOLS")
               or _DISPATCH_TOML.get("worker_mcp_tools", "true")).lower() \
                not in {"false", "0", "no"}:
            try:
                if _MCP_CLIENT_LOCK:
                    async with _MCP_CLIENT_LOCK:
                        _mcp_items = list(_MCP_CLIENT_TOOLS.items())
                else:
                    _mcp_items = list(_MCP_CLIENT_TOOLS.items())
                if _mcp_tool_to_openai_tool:
                    for _k, _info in _mcp_items:
                        base.append(_mcp_tool_to_openai_tool(_k, _info))
            except Exception:
                log.debug("worker MCP tools surface fetch failed")

        def _stable_key(t):
            return (_tool_priority(t),
                    str((t.get("function") or {}).get("name") or ""))

        _core = sorted([t for t in base if _is_core_tool(t)], key=_stable_key)
        _tail = sorted([t for t in base if not _is_core_tool(t)], key=_stable_key)
        _WORKER_TOOLS_CORE_CACHE = _core
        log.info("stable tool core block: %d core + %d tail", len(_core), len(_tail))
        _WORKER_TOOLS_FULL_CACHE = _core + _tail

    surface = _WORKER_TOOLS_FULL_CACHE
    _dom = _routed_domain_var.get(None) if _routed_domain_var else None
    if _dom and _dom in _ROUTING_DOMAINS:
        _allowed = set(_ROUTING_DOMAINS[_dom].get("verbs") or [])
        if _allowed:
            surface = [t for t in surface
                       if (t.get("function", {}).get("name") not in _VERB_CATALOG)
                       or (t.get("function", {}).get("name") in _allowed)]
    if cap and cap > 0:
        return await _select_child_tools(surface, intent, cap)
    return surface


async def _select_child_tools(surface: list, intent_text: str, cap: int) -> list:
    """Per-child intent-relevant tool subset."""
    if not (cap and cap > 0):
        return surface
    if STABLE_PREFIX and _WORKER_TOOLS_CORE_CACHE is not None:
        core = list(_WORKER_TOOLS_CORE_CACHE)
        if cap and cap < len(core):
            return core[:cap]
        core_names = {str((t.get("function") or {}).get("name") or "") for t in core}
        tail_pool = [t for t in surface
                     if str((t.get("function") or {}).get("name") or "") not in core_names]
        tail_budget = (max(0, min(STABLE_PREFIX_TAIL, cap - len(core)))
                       if cap > len(core) else 0)
        if tail_budget <= 0 or not (CHILD_TOOL_SELECT and intent_text and intent_text.strip()):
            return core
        try:
            if _ensure_verb_embeddings:
                await _ensure_verb_embeddings()
            qvec = await _embed_one(intent_text) if _embed_one else None
            if not qvec:
                return core + tail_pool[:tail_budget]

            def _b2(t):
                nm = str((t.get("function") or {}).get("name") or "").split("__", 1)[-1]
                return _resolve_verb_key(nm) if _resolve_verb_key else nm

            db_scores = {}
            try:
                import mios_pg as _mios_pg
                rows = await _mios_pg.execute(
                    "SELECT name, 1 - (emb <=> %(qvec)s::vector) AS score FROM verb "
                    "WHERE hidden = false AND emb IS NOT NULL",
                    {"qvec": qvec},
                    fetch=True
                )
                if rows is not None:
                    for r in rows:
                        if r.get("name"):
                            db_scores[r["name"]] = r["score"]
            except Exception as e_pg:
                log.debug("Database native vector search failed for child tools: %s", e_pg)

            scored = []
            for t in tail_pool:
                b2_key = _b2(t)
                vec = _tool_embedding(b2_key) if _tool_embedding else None
                if b2_key in db_scores:
                    score = db_scores[b2_key]
                elif vec and _cosine:
                    score = _cosine(qvec, vec)
                else:
                    score = _priority_fallback_score(t)
                scored.append((score, t, vec))
            scored.sort(key=lambda x: x[0], reverse=True)
            await _ensure_verb_lexicon()
            return core + _fuse_then_diversify(
                scored, _tok(intent_text), tail_budget, _b2)
        except Exception:
            return core + tail_pool[:tail_budget]

    if not CHILD_TOOL_SELECT or not (intent_text and intent_text.strip()):
        return surface[:cap]
    try:
        if _ensure_verb_embeddings:
            await _ensure_verb_embeddings()
        qvec = await _embed_one(intent_text) if _embed_one else None
        if not qvec:
            return surface[:cap]

        def _nm(t):
            return str((t.get("function") or {}).get("name") or "")

        def _base(t):
            b = _nm(t).split("__", 1)[-1]
            return _resolve_verb_key(b) if _resolve_verb_key else b

        floor, seen = [], set()
        for t in surface:
            pr = _tool_priority(t)
            if pr in (0, 1):
                if _nm(t) not in seen and len(floor) < max(CHILD_TOOL_FLOOR, 0):
                    floor.append(t)
                    seen.add(_nm(t))

        db_scores = {}
        try:
            import mios_pg as _mios_pg
            rows = await _mios_pg.execute(
                "SELECT name, 1 - (emb <=> %(qvec)s::vector) AS score FROM verb "
                "WHERE hidden = false AND emb IS NOT NULL",
                {"qvec": qvec},
                fetch=True
            )
            if rows is not None:
                for r in rows:
                    if r.get("name"):
                        db_scores[r["name"]] = r["score"]
        except Exception as e_pg:
            log.debug("Database native vector search failed for child tools: %s", e_pg)

        scored = []
        for t in surface:
            if _nm(t) in seen:
                continue
            base_key = _base(t)
            vec = _tool_embedding(base_key) if _tool_embedding else None
            if base_key in db_scores:
                score = db_scores[base_key]
            elif vec and _cosine:
                score = _cosine(qvec, vec)
            else:
                score = _priority_fallback_score(t)
            scored.append((score, t, vec))
        scored.sort(key=lambda x: x[0], reverse=True)
        await _ensure_verb_lexicon()
        ranked = _fuse_then_diversify(
            scored, _tok(intent_text), max(0, cap - len(floor)), _base)
        out = list(floor) + ranked
        return out[:cap]
    except Exception:
        return surface[:cap]


async def _tool_pref_block(intent_text: str, k: int = 6) -> str:
    """The per-turn cosine 'prefer these tools' signal."""
    if not (STABLE_PREFIX and CHILD_TOOL_SELECT
            and intent_text and intent_text.strip()):
        return ""
    try:
        if _ensure_verb_embeddings:
            await _ensure_verb_embeddings()
        qvec = await _embed_one(intent_text) if _embed_one else None
        if not qvec or not _VERB_EMBEDDINGS or not _cosine:
            return ""
        ranked = sorted(((_cosine(qvec, v), n) for n, v in _VERB_EMBEDDINGS.items() if v),
                        key=lambda x: x[0], reverse=True)
        names = [n for s, n in ranked[:max(0, k)] if s > 0]
        if not names:
            return ""
        return ("Likely-relevant tools for this request (a hint from semantic match -- "
                "use the best fit, or any other tool, or none): " + ", ".join(names) + ".")
    except Exception:
        return ""
