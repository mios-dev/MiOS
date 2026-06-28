# AI-hint: ROUTING layer extracted verbatim from server.py (refactor R2/mios_routing wave). The deterministic SSOT-config routing loaders -- _load_routing_domains (mios.toml [routing.domains.*] -> the 2-stage domain router), _load_routing_phrases (a lowercased/longest-first phrase list from [routing].<key>), _load_launch_fillers -- plus _deterministic_action_route, the catalog-derived pre-router that binds an unambiguous "open/launch <app>" (or a standalone "type '<text>'") to a single concrete verb BEFORE the refine micro can mis-classify it as a research swarm. All phrase/domain vocab is mios.toml data (NO hardcoded English). The loaders are pure config + a logger; _deterministic_action_route reads the fast-path verb sets + launch phrase frozensets, which stay in server.py (they derive from the _VERB_CATALOG server global) and are dependency-INJECTED via configure() under their original server names (one-way boundary -- this module NEVER imports server). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./test_mios_routing.py
# AI-functions: _load_routing_domains, _load_routing_phrases, _load_launch_fillers, _deterministic_action_route, configure
"""ROUTING layer -- deterministic SSOT-config routing loaders + the
catalog-derived deterministic pre-router.

Extracted verbatim from ``server.py``. ``_load_routing_domains`` /
``_load_routing_phrases`` / ``_load_launch_fillers`` read the routing
vocabulary from ``mios.toml`` ``[routing]`` (domains, launch fillers,
trigger phrases) -- all SSOT data, no hardcoded English. ``_deterministic
_action_route`` maps an unambiguous launch / type request to a single
concrete verb override before the refine micro can mis-route it.

The fast-path verb sets and launch phrase frozensets (``_FASTPATH_VERBS``,
``_LAUNCH_TRIGGERS``, ``_LAUNCH_FILLERS``, ``_LAUNCH_LEAD_WORDS``,
``_LAUNCH_TRAIL_WORDS``, ``_COMPOUND_ACTION_ALT``) and the module logger
are injected via :func:`configure` -- they stay in ``server.py`` because
they derive from the ``_VERB_CATALOG`` server global. ``server.py``
re-imports every name under its original alias so the module's public
surface is byte-identical (one-way boundary: this module never imports
``server``).
"""

from __future__ import annotations

import os
import re
from typing import Optional


# ── Dependency-injection seam ─────────────────
# The config loaders log on failure; _deterministic_action_route reads the
# fast-path verb sets + launch phrase frozensets that server.py derives from
# _VERB_CATALOG. server.py calls configure() with these AFTER they are all
# defined (one-way boundary: this module never imports server). They keep their
# ORIGINAL server.py names because the moved bodies reference them verbatim. The
# loaders run at server import time (before configure), so `log` defaults to None
# and is only touched on the error path; the fast-path globals are read only at
# request time, well after configure() has injected them.
log = None
_COMPOUND_ACTION_ALT = ""
_FASTPATH_VERBS = frozenset()
_LAUNCH_TRIGGERS = frozenset()
_LAUNCH_FILLERS = []
_LAUNCH_LEAD_WORDS = frozenset()
_LAUNCH_TRAIL_WORDS = frozenset()


def configure(*, logger=None, compound_action_alt=None, fastpath_verbs=None,
              launch_triggers=None, launch_fillers=None, launch_lead_words=None,
              launch_trail_words=None) -> None:
    """Inject the server.py logger + the _VERB_CATALOG-derived fast-path verb
    sets / launch phrase frozensets the routing layer reads."""
    global log, _COMPOUND_ACTION_ALT, _FASTPATH_VERBS, _LAUNCH_TRIGGERS
    global _LAUNCH_FILLERS, _LAUNCH_LEAD_WORDS, _LAUNCH_TRAIL_WORDS
    if logger is not None:
        log = logger
    if compound_action_alt is not None:
        _COMPOUND_ACTION_ALT = compound_action_alt
    if fastpath_verbs is not None:
        _FASTPATH_VERBS = fastpath_verbs
    if launch_triggers is not None:
        _LAUNCH_TRIGGERS = launch_triggers
    if launch_fillers is not None:
        _LAUNCH_FILLERS = launch_fillers
    if launch_lead_words is not None:
        _LAUNCH_LEAD_WORDS = launch_lead_words
    if launch_trail_words is not None:
        _LAUNCH_TRAIL_WORDS = launch_trail_words


def _load_routing_domains() -> tuple[dict, bool]:
    """Parse mios.toml [routing.domains.*] -> {domain: {"desc","verbs"}} plus the
    router_enable switch. The 2-stage domain router's Stage-1 classifier consumes
    `desc` as each enum label's meaning; Stage-2 filters the planner catalog to the
 chosen domain's `verbs`. SSOT (fix the 82-tool mis-routing
    via schema-routing, NO english prose rules). FAIL-SAFE: router disabled / no
    domains / load error -> ({}, False) -> full-surface behaviour, nothing lost."""
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as f:
            rt = (tomllib.load(f).get("routing") or {})
        enable = str(rt.get("router_enable", "false")).lower() in {"true", "1", "yes", "on"}
        domains: dict = {}
        for dom, cfg in (rt.get("domains") or {}).items():
            if isinstance(cfg, dict):
                domains[str(dom)] = {"desc": str(cfg.get("desc", "")),
                                     "verbs": [str(v) for v in (cfg.get("verbs") or [])]}
        return domains, enable
    except Exception as e:
        log.warning("routing domains load failed: %s", e)
        return {}, False


def _load_routing_phrases(key: str) -> list:
    """Load a deterministic-launch SSOT phrase list from mios.toml [routing].<key>,
    lowercased + de-duplicated, longest-first (so multi-word phrases strip before
    their substrings). NO hardcoded English in code -- the lists are SSOT data.
    FAIL-SAFE: any error -> []."""
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as f:
            rt = (tomllib.load(f).get("routing") or {})
        return sorted(
            {str(p).lower().strip() for p in (rt.get(key) or []) if str(p).strip()},
            key=len, reverse=True)
    except Exception as e:
        log.warning("routing phrases load failed (%s): %s", key, e)
        return []


def _load_launch_fillers() -> list:
    """Trailing courtesy/location phrases (SSOT mios.toml [routing].launch_filler_
    phrases) stripped from a deterministic launch target so 'open notepad for me'
    -> open_app(name='notepad') and 'open spotify on my desktop' -> name='spotify'
 (e2e: filler bled into the app name, and 'on my desktop'
    forced the launch into the LLM path which mis-classified it as discovery)."""
    return _load_routing_phrases("launch_filler_phrases")


def _deterministic_action_route(user_text: str) -> Optional[dict]:
    """Research-backed (OpenAI function-calling + AIOS routing) deterministic
    pre-router. An unambiguous 'launch/open <app>' is a single concrete action;
    bind it to open_app(name=<app>) HERE so the qwen-class refine micro never
    gets to misclassify it as a research swarm -- the failure where 'launch
    epiphany' fired mios_find/list_windows and FABRICATED 'it's open' instead of
    launching. Returns the override dict, or None to fall through to the LLM
    router for compound/ambiguous phrasing (URLs, 'in <app>', conjunctions,
    questions) which the stronger refine model resolves. Triggers are
    catalog-derived (verb names), not hardcoded words (operator no-hardcode rule)."""
    t = (user_text or "").strip()
    if not t or "?" in t:
        return None
    # Standalone "type/write '<text>' [into it]" -> pc_type (Windows desktop
    # input). Operator's EXACT domain (typing). Without this a bare type request
    # that carries NO launch verb misrouted (multi-turn
    # trace): refine hinted cu_type (the LINUX vm verb), the model fired
    # windows_file_search/list_windows and ECHOED the text instead of typing it
    # (notepad stayed "Untitled"). The action vocab is SSOT
    # (_COMPOUND_ACTION_ALT <- mios.toml [routing].compound_actions) -- NO
    # hardcoded keyword list. Fires ONLY when pc_type is a real fast-path verb.
    # A QUOTED literal (within the first 2 words of an action verb) is the
    # unambiguous text-to-type; an unquoted form needs the action verb at the
    # HEAD plus an explicit "in/into <target>" so ordinary prose ("put it on the
    # table", "write to me") can never hijack the route. Degrades open: no clear
    # match -> falls through to the LLM router (no regression). The type-chain's
    # read-back verification (mios-pc-control) still catches a wrong/lost focus.
    if _COMPOUND_ACTION_ALT and "pc_type" in _FASTPATH_VERBS:
        _Q = "\"'‘’“”"
        _av = r"(?:" + _COMPOUND_ACTION_ALT + r")"
        _typ = None
        _mq = re.match(
            r"^\s*(?:\w+\s+){0,2}?" + _av + r"\b[\s:.\-]*["
            + _Q + r"](.+?)[" + _Q + r"]", t, re.IGNORECASE)
        if _mq:
            _typ = _mq.group(1).strip()
        else:
            _mh = re.match(
                r"^\s*" + _av + r"\b[\s:.\-]+(.+?)\s+\b(?:into|in)\b\s+\S",
                t, re.IGNORECASE)
            if _mh:
                _typ = _mh.group(1).strip().strip(_Q).strip()
        if _typ:
            return {"intent": "dispatch", "tool": "pc_type",
                    "args": {"text": _typ}, "_deterministic": True}
    # Native AIOS implementation: Do NOT strip compound tails in the deterministic
    # fast-path. We WANT "open notepad and type hello" to fall through to the LLM
    # router so it is natively decomposed into two separate tool calls (open_app + pc_type).
    if not t or len(t) > 80:
        return None
    words = t.split()
    if len(words) < 2:
        return None
    head = words[0].lower().strip(".,:;!\"'")
    if head not in _LAUNCH_TRIGGERS or "open_app" not in _FASTPATH_VERBS:
        return None
    rest = " ".join(words[1:]).strip()
    # Strip a trailing sentence terminator FIRST so the filler / word-boundary
    # matching below isn't defeated by punctuation: 'open X on my desktop.' kept
    # the period, so 'on my desktop' never stripped, the leftover 'on' tripped the
    # compound guard, and the launch fell to the LLM router -- which then picked
    # hermes's built-in `terminal` tool (exit 126) instead of open_app
    # (e2e).
    rest = rest.rstrip(" .,!;:")
    # Strip trailing courtesy/location filler (SSOT list) so the app name is clean
    # and the launch stays on the DETERMINISTIC path -- 'open notepad for me' ->
    # name='notepad'; 'open spotify on my desktop' -> name='spotify'. Stripping
    # before the compound check is what keeps 'on my desktop' from forcing the
    # launch into the LLM router (which mis-routed it to discovery in the e2e).
    _low = rest.lower()
    _changed = True
    while _changed and rest:
        _changed = False
        for _f in _LAUNCH_FILLERS:
            if _f and _low.endswith(_f):
                rest = rest[:len(rest) - len(_f)].rstrip(" ,.")
                _low = rest.lower()
                _changed = True
                break
    # Drop leading determiners/possessives + trailing generic nouns (SSOT) so
    # natural phrasings resolve: 'the windows calculator app' -> 'windows
    # calculator', 'my photos application' -> 'photos'. Word-by-word (so a real
    # one-word app name is never partially truncated).
    _rw = rest.split()
    while _rw and _rw[0].lower() in _LAUNCH_LEAD_WORDS:
        _rw.pop(0)
    while _rw and _rw[-1].lower() in _LAUNCH_TRAIL_WORDS:
        _rw.pop()
    rest = " ".join(_rw).strip()
    _low = rest.lower()
    # (Removed compound interception -- compounds natively fall to the LLM router)
    if not rest or len(rest.split()) > 3:
        return None
    # True compound forms (url / 'in <app>' / conjunctions = two targets) -> let
    # the LLM router split content from target; the deterministic path only takes
    # the unambiguous bare 'launch <app>' (after filler + determiners stripped).
    if "://" in rest or re.search(r"\b(in|and|then|with|on|to)\b", _low):
        return None
    return {"intent": "dispatch", "tool": "open_app",
            "args": {"name": rest}, "_deterministic": True}
