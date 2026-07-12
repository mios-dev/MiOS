# AI-hint: Layer-1 micro-LLM CLASSIFIER cluster, extracted verbatim from server.py
#   (strangler-fig; unblocked by the R14 config relocation). classify_intent calls
#   the micro classifier on the CPU light-lane and returns a {action: dispatch|chat|
#   agent} verdict (native json_schema enum-constrained to REAL verbs; fail-open to
#   None -> full surface). _route_domain is the stage-1 domain classifier (constrained
#   enum over mios.toml [routing.domains], thinking-off, code-validated, fail-open).
#   NOTE: distinct from mios_router (the pure intent->RouteDecision router). Static
#   config (ROUTER_*/PLANNER_ENDPOINT/PLANNER_TIMEOUT_S/_ROUTER_SYSTEM) is imported
#   DIRECTLY from mios_config (SSOT); the server-owned HOT verb catalog, the computed
#   routing domains, and the event-DB helpers are dependency-INJECTED via configure()
#   (one-way boundary -- this module NEVER imports server).
# AI-related: server.py, mios_config.py, mios_jsonsalvage.py, mios_chat.py, mios_refine.py
# AI-functions: classify_intent, _route_domain, configure
"""Layer-1 micro-LLM classifiers (classify_intent + _route_domain), from server.py."""

from __future__ import annotations

import asyncio
import json
import os
import re
import logging
from typing import Optional

import httpx

from mios_config import (
    ROUTER_ENABLED,
    ROUTER_MODEL,
    ROUTER_ENDPOINT,
    ROUTER_TIMEOUT_S,
    ROUTER_MAX_TOKENS,
    _ROUTER_SYSTEM,
    PLANNER_ENDPOINT,
    PLANNER_TIMEOUT_S,
)
from mios_jsonsalvage import loads_lenient as _loads_lenient

# Same logger name server.py uses, so log output is byte-identical post-extraction.
log = logging.getLogger("mios-agent-pipe")

# Injected via configure() (server-owned). Placeholders until configured: the HOT
# verb catalog (built once at startup, never rebound -> a plain ref is safe), the
# computed [routing.domains] table + enable flag, and the event-DB helpers.
_VERB_CATALOG: dict = {}
_ROUTING_DOMAINS: dict = {}
_ROUTING_ENABLE: bool = False
_db_create = None
_db_post = None
_db_fire = None


def configure(*, verb_catalog=None, routing_domains=None, routing_enable=None,
              db_create=None, db_post=None, db_fire=None) -> None:
    """Inject the server-owned hot globals + event-DB helpers. One-way boundary:
    mios_classify never imports server. routing_enable may legitimately be False, so
    each field is gated on ``is not None`` (not truthiness)."""
    global _VERB_CATALOG, _ROUTING_DOMAINS, _ROUTING_ENABLE
    global _db_create, _db_post, _db_fire
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if routing_domains is not None:
        _ROUTING_DOMAINS = routing_domains
    if routing_enable is not None:
        _ROUTING_ENABLE = routing_enable
    if db_create is not None:
        _db_create = db_create
    if db_post is not None:
        _db_post = db_post
    if db_fire is not None:
        _db_fire = db_fire


async def classify_intent(user_text: str) -> Optional[dict]:
    """Call the micro-LLM router. Returns the parsed verdict dict
    or None to fall through to backend proxy. Best-effort: any error
    falls through cleanly."""
    if not ROUTER_ENABLED or not user_text or not user_text.strip():
        return None
    # /v1 with enable_thinking=False: ROUTER_MODEL is a qwen3 micro
    # that ignores /no_think and otherwise dumps its answer into
    # message.reasoning with EMPTY content (operator test) --
    # which made the router slow (full think pass) and unreliable.
    payload = {
        "model": ROUTER_MODEL,
        "messages": [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user",   "content": user_text[:2000]},
        ],
        "temperature": 0.0,
        "max_tokens": ROUTER_MAX_TOKENS,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    # NATIVE structured outputs (WS-H2): upgrade json_object (valid
    # JSON, NOT schema-adherent -> the reason the parse below still defensively
    # checks "action" not in parsed) to a strict json_schema so `action` is enum-
    # constrained and `tool` can only be a REAL verb. Same proven _route_domain
    # pattern (json_schema + enable_thinking=False; llama.cpp #20345 drops the
    # grammar when thinking is on). Gated MIOS_ROUTER_STRUCTURED (default on); the
    # router is fail-open (any miss -> full surface) so an unsupported backend
    # degrades cleanly. The defensive parse guard below stays (belt + suspenders).
    if os.environ.get("MIOS_ROUTER_STRUCTURED", "true").strip().lower() not in {
            "0", "false", "no", "off"}:
        payload["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "mios_route", "strict": True, "schema": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "action": {"type": "string",
                               "enum": ["dispatch", "chat", "agent"]},
                    "tool": {"type": ["string", "null"],
                             "enum": sorted(_VERB_CATALOG.keys()) + [None]},
                    "args": {"type": ["object", "null"], "additionalProperties": True},
                    "reason": {"type": ["string", "null"]},
                    "reply": {"type": ["string", "null"]}},
                "required": ["action", "tool", "args", "reason", "reply"]}}}
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    url = f"{ROUTER_ENDPOINT}/v1/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=ROUTER_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("router unexpected error: %s", e)
        return None
    # OpenAI /v1 choices[] shape (MiOS is /v1-only).
    choices = body.get("choices") or []
    msg = (choices[0].get("message") if choices else {}) or {}
    content = (msg.get("content") or "").strip()
    if not content:
        return None
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = _loads_lenient(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "action" not in parsed:
        return None
    # Best-effort event row for the router verdict.
    _db_fire(_db_post(_db_create("event", {
        "source": "mios-agent-pipe",
        "kind": "classify",
        "severity": "info",
        "summary": str(parsed.get("action", "?"))[:120],
        "payload": parsed,
    }, now_fields=("ts",))))
    return parsed


async def _route_domain(user_text: str) -> Optional[str]:
    """Stage-1 of the domain router: classify the query into ONE [routing.domains]
    label via a constrained enum (response_format json_schema), THINKING-OFF
    (llama.cpp #20345 silently drops the grammar when thinking is on). Returns the
    validated domain, or None to fall through to the FULL surface (router off / no
    domains / classify error / out-of-enum result). We VALIDATE the label in code
    and never trust HTTP 200 alone (fail-open #19051)."""
    if not _ROUTING_ENABLE or not _ROUTING_DOMAINS or not (user_text or "").strip():
        return None
    names = list(_ROUTING_DOMAINS.keys())
    sys = ("Classify the user request into exactly ONE domain (the kind of "
           "capability it needs). Domains:\n"
           + "\n".join(f"{n}: {_ROUTING_DOMAINS[n]['desc']}" for n in names))
    payload = {
        "model": ROUTER_MODEL,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content": user_text[:2000]}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "route", "strict": True, "schema": {
                "type": "object",
                "properties": {"domain": {"type": "string", "enum": names}},
                "required": ["domain"], "additionalProperties": False}}},
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.0, "max_tokens": 30, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{PLANNER_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return None
        content = ((r.json().get("choices") or [{}])[0].get("message", {})
                   .get("content") or "")
        dom = (_loads_lenient(content) or {}).get("domain")
        if dom in _ROUTING_DOMAINS:
            log.info("router: domain=%s <- %s", dom, user_text[:48].replace(chr(10), " "))
            return dom
        log.info("router: out-of-enum %r -> full surface", dom)
    except Exception as e:
        log.info("router classify failed (-> full surface): %s", e)
    return None
