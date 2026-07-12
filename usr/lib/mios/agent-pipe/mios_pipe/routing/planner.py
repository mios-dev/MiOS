# AI-hint: Planner / DAG-decomposition layer extracted verbatim from server.py. Holds the Phase-A.1 _PLANNER_SYSTEM prompt (renders the SSOT verb/recipe/agent catalogs into the function-calling-shaped DAG planner prompt), the Stage-2 domain-prompt narrowers _planner_system_for / _action_domain_verbs (swap the full verb-catalog block for the routed domain's slice), decompose_intent (calls the planner LLM -> validated DAG of dispatch-verb / sub-agent nodes), and the executor orderers _topological_order (dependency order, cycle-safe) + _dag_levels (Kahn concurrent-level layering). Config (PLANNER_*) re-read from os.environ with _STACK_MODEL/_LIGHT_BASE bases imported from mios_config; _render_verb_catalog imported from mios_verbcatalog; the rendered catalogs + the routed-domain contextvar + the raw verb-catalog/routing-domains SSOT + _is_action_domain/_build_dispatch_cmd helpers + the live _AGENT_REGISTRY are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server; _AGENT_REGISTRY is re-injected on membership reload). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_verbcatalog.py, ./test_mios_planner.py
# AI-functions: decompose_intent, _topological_order, _dag_levels, _planner_system_for, _action_domain_verbs, configure
"""Planner / DAG-decomposition layer (Phase A.1).

Extracted verbatim from ``server.py``. ``_PLANNER_SYSTEM`` is the
function-calling-shaped planner system prompt -- it embeds the SSOT verb /
recipe / agent catalogs (rendered server-side and injected via
:func:`configure`) so the planner only emits real verbs / agents.
``decompose_intent`` calls the planner LLM and returns a validated DAG of
dispatch-verb / sub-agent nodes (or ``None`` to fall through to the backend).
``_topological_order`` / ``_dag_levels`` order that DAG for the executor.

``_planner_system_for`` / ``_action_domain_verbs`` narrow that prompt to a
single routed domain's verb slice (Stage-2 of the domain router); they live
here beside their only caller (``decompose_intent``).

Config constants (``PLANNER_*``) are re-read from ``os.environ`` (bases
``_STACK_MODEL`` / ``_LIGHT_BASE`` from ``mios_config``); ``_render_verb_catalog``
is imported from ``mios_verbcatalog``; the rendered catalogs, the routed-domain
contextvar, the raw verb-catalog / routing-domains SSOT, the
``_is_action_domain`` / ``_build_dispatch_cmd`` helpers and the live
``_AGENT_REGISTRY`` are injected via :func:`configure` (one-way boundary --
this module never imports ``server``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Optional

import httpx

from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_config import _STACK_MODEL, _LIGHT_BASE
# Catalog renderer for the now-native _planner_system_for Stage-2 surface-narrowing
# (moved here from server.py). mios_verbcatalog never imports mios_planner, so this
# direct import keeps the one-way boundary intact (no cycle).
from mios_verbcatalog import _render_verb_catalog

log = logging.getLogger("mios-agent-pipe")


# -- Planner config (verbatim from server.py; re-read from env, same as the
# sibling-module precedent in mios_dci). _STACK_MODEL / _LIGHT_BASE come from
# mios_config so the defaults track the SSOT model/endpoint. ----------------
PLANNER_ENABLED = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_ENABLED", "true",
).lower() not in {"false", "0", "no"}
PLANNER_MODEL = os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MODEL", _STACK_MODEL,   # gemma4:12b entire-stack
)
PLANNER_ENDPOINT = os.environ.get(
    # mios-llm-light /v1 (the old :11434 legacy lane default is dead -- G5/G17). Env (SSOT
    # agent-pipe.env) overrides; this is only the fresh-install fallback.
    "MIOS_AGENT_PIPE_PLANNER_ENDPOINT", _LIGHT_BASE,
).rstrip("/")
PLANNER_TIMEOUT_S = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_TIMEOUT_S", "30"))
PLANNER_MAX_TOKENS = int(os.environ.get(
    # 1536 (was 800): gemma4:12b is the REASONING model -- it spends tokens on
    # reasoning_content before emitting the JSON content, so a tight budget
    # truncates the decompose to empty -> -> council dups..
    "MIOS_AGENT_PIPE_PLANNER_MAX_TOKENS", "1536"))
PLANNER_MAX_NODES = int(os.environ.get(
    "MIOS_AGENT_PIPE_PLANNER_MAX_NODES", "8"))
# Short-prompt-skip cutoffs (SSOT: mios.toml [planner]; injected via configure()
# from server.py). A prompt under BOTH limits is treated as a single-dispatch
# input and skips the DAG planner. The values below are the single documented
# baseline; behaviour is identical at them.
PLANNER_SHORT_PROMPT_CHARS = 60   # below this char count, a non-action prompt skips the planner
PLANNER_SHORT_PROMPT_WORDS = 10   # ...AND at or below this whitespace-token count

# -- Dependency-injection seam -------------------------------------
# decompose_intent + _PLANNER_SYSTEM + the native Stage-2 narrowers depend on
# symbols server.py owns: the rendered SSOT catalogs (_VERB_CATALOG_RENDERED /
# _RECIPE_CATALOG_RENDERED / _AGENT_CATALOG_RENDERED), the routed-domain
# contextvar, the raw verb-catalog + routing-domains SSOT (_VERB_CATALOG /
# _ROUTING_DOMAINS, read at call time by _planner_system_for / _action_domain_verbs),
# the multi-consumer _is_action_domain split, the dispatch-verb resolver
# _build_dispatch_cmd, and the live _AGENT_REGISTRY. server.py injects them via
# configure() AFTER they are defined (one-way boundary: this module never
# imports server). _PLANNER_SYSTEM is built INSIDE configure() once the three
# rendered catalogs are present -- it cannot be built at import time because the
# catalogs are rendered server-side. server.py re-imports _PLANNER_SYSTEM AFTER
# the configure() call so its binding sees the built value. _AGENT_REGISTRY is
# re-injected on every membership reload (live agent add/drop).
_VERB_CATALOG_RENDERED: Optional[str] = None
_RECIPE_CATALOG_RENDERED: Optional[str] = None
_AGENT_CATALOG_RENDERED: Optional[str] = None
_routed_domain_var = None
_is_action_domain = None
_build_dispatch_cmd = None
_AGENT_REGISTRY: dict = {}
_PLANNER_SYSTEM: Optional[str] = None
# Raw SSOT for the now-native domain-prompt helpers (_planner_system_for /
# _action_domain_verbs, moved here from server.py): the HOT verb catalog (shared by
# reference, mirroring its other consumers) + the routed [routing.domains] table.
# Both default empty so the helpers fail-safe to the full prompt until configure()
# injects them. _is_action_domain stays INJECTED (it is multi-consumer in server).
_VERB_CATALOG: dict = {}
_ROUTING_DOMAINS: dict = {}


def configure(*, verb_catalog_rendered=None, recipe_catalog_rendered=None,
              agent_catalog_rendered=None, routed_domain_var=None,
              is_action_domain=None, verb_catalog=None, routing_domains=None,
              build_dispatch_cmd=None, agent_registry=None,
              short_prompt_chars=None, short_prompt_words=None) -> None:
    """Inject the server.py runtime deps the planner calls back into, then
    (re)build _PLANNER_SYSTEM once the rendered catalogs are available. The
    verb_catalog / routing_domains args feed the now-native _planner_system_for /
    _action_domain_verbs helpers (raw SSOT they read at call time). The
    short_prompt_chars / short_prompt_words args carry the SSOT [planner]
    short-prompt-skip cutoffs (None = keep the baseline)."""
    global _VERB_CATALOG_RENDERED, _RECIPE_CATALOG_RENDERED, _AGENT_CATALOG_RENDERED
    global _routed_domain_var, _is_action_domain, _VERB_CATALOG, _ROUTING_DOMAINS
    global _build_dispatch_cmd, _AGENT_REGISTRY
    global PLANNER_SHORT_PROMPT_CHARS, PLANNER_SHORT_PROMPT_WORDS
    if verb_catalog_rendered is not None:
        _VERB_CATALOG_RENDERED = verb_catalog_rendered
    if recipe_catalog_rendered is not None:
        _RECIPE_CATALOG_RENDERED = recipe_catalog_rendered
    if agent_catalog_rendered is not None:
        _AGENT_CATALOG_RENDERED = agent_catalog_rendered
    if routed_domain_var is not None:
        _routed_domain_var = routed_domain_var
    if is_action_domain is not None:
        _is_action_domain = is_action_domain
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if routing_domains is not None:
        _ROUTING_DOMAINS = routing_domains
    if build_dispatch_cmd is not None:
        _build_dispatch_cmd = build_dispatch_cmd
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if short_prompt_chars is not None:
        PLANNER_SHORT_PROMPT_CHARS = int(short_prompt_chars)
    if short_prompt_words is not None:
        PLANNER_SHORT_PROMPT_WORDS = int(short_prompt_words)
    if (_VERB_CATALOG_RENDERED is not None
            and _RECIPE_CATALOG_RENDERED is not None
            and _AGENT_CATALOG_RENDERED is not None):
        _build_planner_system()


# ── Planner system prompt (Phase A.1 DAG decomposition) ───────────
# Function-calling-shaped prompt for qwen2.5-coder:7b. Emits a DAG
# of dispatch verbs WHEN the user's intent is multi-step. Returns
# {"action": "decompose", "nodes": [...]}. Each node has a unique
# id, a tool, args, and a list of node-id deps (parents). Empty
# nodes list = "I can't decompose this; fall through to backend".
#
# IMPORTANT: this prompt MUST stay in lockstep with the dispatch
# verb table in _build_dispatch_cmd. A planner emitting a verb the
# dispatcher doesn't know causes silent failures.
def _build_planner_system() -> None:
    """Build _PLANNER_SYSTEM from the injected rendered catalogs (verbatim
    server.py prompt). Continuation lines below are byte-identical to the
    original; only the wrapping assignment is re-homed here."""
    global _PLANNER_SYSTEM
    _PLANNER_SYSTEM = (
    "You are the MiOS planner (Agentic-OS DAG decomposition layer).\n"
    "The user's prompt has been classified as multi-step. Your job is\n"
    "to emit a DAG of MiOS dispatch verbs that, executed in topological\n"
    "order, fulfills the user's intent. Emit JSON ONLY.\n"
    "\n"
    "REASON -> PLAN -> DELEGATE meta-rule:\n"
    "  For any 'open / find / install / use / launch X' intent, the\n"
    "  FIRST DAG layer is ALWAYS a PARALLEL FAN-OUT of every relevant\n"
    "  inventory / search verb from the verb catalog below (deps=[]).\n"
    "  The action verb depends on ALL of them (deps=[n1,n2,...]) so it\n"
    "  runs only after probes complete. Never emit a single-node DAG\n"
    "  that goes straight to the action without the fan-out first --\n"
    "  the downstream agent has to be able to choose the right target,\n"
    "  and choosing requires evidence from MULTIPLE surfaces (Windows-\n"
    "  side index, Linux-side inventory, package managers, cached FS\n"
    "  map). A single refusal turn that declares something absent\n"
    "  without running any probe first is a defect.\n"
    "\n"
    "Output shape (EXACT):\n"
    '{"action":"decompose",\n'
    ' "summary": "<one-line plan in user\'s language>",\n'
    ' "nodes": [\n'
    '   {"id":"n1","tool":"<verb>","args":{...},"deps":[]},\n'
    '   {"id":"n2","tool":"<verb>","args":{...},"deps":["n1"]},\n'
    '   {"id":"n3","agent":"<sub-agent>","prompt":"<sub-task>","deps":[]},\n'
    '   ...\n'
    ' ]}\n'
    "\n"
    "TWO node kinds -- pick per sub-task:\n"
    "  * a `tool` node runs ONE MiOS dispatch verb (direct OS action /\n"
    "    probe; from the verb catalog below).\n"
    "  * an `agent` node DELEGATES a self-contained sub-task to a named\n"
    "    sub-agent (from the sub-agent roster below) -- use it when the\n"
    "    sub-task needs an agent's own reasoning + tool-loop (code work ->\n"
    "    the coding agent; open-ended research/synthesis -> a general\n"
    "    agent; a quick second opinion / summary -> the cpu reasoner).\n"
    "    `prompt` is the sub-task in the user's language; it MAY contain\n"
    "    #E<id> refs to upstream outputs (substituted at run time).\n"
    "ROUTE DIFFERENT sub-tasks to DIFFERENT agents and give independent\n"
    "ones deps=[] so they run CONCURRENTLY (the executor runs every node\n"
    "whose deps are satisfied in parallel). Weigh the whole roster -- do\n"
    "not funnel everything to one agent. Reserve agent nodes for sub-tasks\n"
    "a single verb cannot cover; do not wrap a plain verb in an agent node.\n"
    "\n"
    "If you cannot decompose into AT LEAST 2 dispatchable nodes, emit\n"
    '{"action":"decompose","summary":"","nodes":[]} so the chain falls\n'
    "through to the backend sub-agent (Hermes / OpenCode / etc.) which\n"
    "has tool-calling + web access itself.\n"
    "\n"
    "ReWOO-style forward refs: an arg can reference an upstream node's\n"
    "stdout via `#E<node-id>` or `#E<node-id>.<field>`. The dispatcher\n"
    "substitutes the actual output at execute time, so you don't have\n"
    "to know the runtime value when planning. Two ref forms:\n"
    "\n"
    "  #E<id>          smart-extract a single useful field from the\n"
    "                  upstream output (handles JSON / NDJSON / plain\n"
    "                  text; picks `name` / `launch` / `title` / `id`\n"
    "                  / `path` in that order). Use when you don't\n"
    "                  care which field, just want THE useful value.\n"
    "\n"
    "  #E<id>.<field>  extract a NAMED field from the upstream's JSON\n"
    "                  output. PREFERRED when you know which field you\n"
    "                  need -- avoids ambiguity if the model picks the\n"
    "                  wrong default field.\n"
    "\n"
    "Example A -- list games, research, LAUNCH THE BEST. An AGENT node researches\n"
    "the real inventory + names the winner; the launch refs THAT node's output\n"
    "(#En2), NOT the first item -- and it is a REAL launch_verified VERB node so\n"
    "it ACTUALLY FIRES (never just narrate 'launching X'):\n"
    '  {"id":"n1","tool":"mios_apps","args":{"filter":"games"},"deps":[]},\n'
    '  {"id":"n2","agent":"hermes","prompt":"From these installed GAMES -> #En1 '
    "-- do ONE web search comparing their aggregate review scores (one "
    "comparative query, not per-title); pick the single highest-rated ACTUAL "
    "GAME (ignore non-game library items like wallpaper/utility/benchmark/"
    "redistributable entries). Output STRUCTURED JSON ONLY, no prose: "
    '{\\"winner\\":\\"<exact launch name from the list>\\"}.",'
    '"format":"json","deps":["n1"]},\n'
    '  {"id":"n3","tool":"launch_verified","args":{"name":"#En2.winner"},"deps":["n2"]}\n'
    "\n"
    "Example B -- find a file then open it (PREFER this over mios-find\n"
    "for `find X` / `where is X` -- directory_lookup is ~100x faster):\n"
    '  {"id":"n1","tool":"directory_lookup","args":{"query":"<X>","kind":"file","limit":1},"deps":[]},\n'
    '  {"id":"n2","tool":"text_view","args":{"path":"#En1.path"},"deps":["n1"]}\n'
    "\n"
    "NEVER paste the raw `#E<id>` value into a launcher arg without\n"
    "thought -- mios_apps + directory_lookup return NDJSON-like results\n"
    "(one record per hit), so a bare #En1 in open_app(name=#En1) would\n"
    "substitute only the FIRST hit's smart-extracted field. If you want\n"
    "a specific record's specific field, use #En1.<field> to pull it\n"
    "explicitly (.name / .app_id / .path / .launch / .description).\n"
    "\n"
    "CRITICAL: the action verb's target NAME comes from the PROBE'S\n"
    "OUTPUT (#En1.app_id / #En1.short_name / #En1.name), NEVER from\n"
    "the probe verb's OWN name:\n"
    "  WRONG -- launch_app(name='mios_apps')   <-- emits the probe verb name\n"
    "  WRONG -- launch_app(name='mios-apps')   <-- same defect with hyphen\n"
    "  RIGHT -- launch_app(name='#En1.app_id') <-- ref the discovered app\n"
    "If you cannot decompose 'find X then launch X' into ref-substitution,\n"
    "emit empty nodes and let the backend sub-agent handle it -- never\n"
    "fall back to launching the discovery tool itself.\n"
    "\n"
    "Available verbs (SSOT: mios.toml [verbs.*]; renderer reads it at\n"
    "boot, no English baked in this file). Use EXACT name + args shape\n"
    "-- the dispatcher rejects unknown verbs:\n"
    "\n"
    + _VERB_CATALOG_RENDERED + "\n\n"
    + _RECIPE_CATALOG_RENDERED + "\n\n"
    "Sub-agent roster for `agent` nodes (SSOT: mios.toml [agents.*]; use\n"
    "the EXACT name -- the executor rejects unknown agents):\n"
    "\n"
    + _AGENT_CATALOG_RENDERED + "\n\n"
    "Common patterns (study these before emitting):\n"
    "\n"
    "  open + position:\n"
    "    n1 open_app(name=X) -> n2 focus_window(title=X) -> n3 position_window(title=X, x=A, y=B)\n"
    "\n"
    "  open + write file (NO more pc_type+pc_key; use text_create):\n"
    "    n1 text_create(path=P, content=C) -> n2 text_view(path=P)\n"
    "\n"
    "  flatpak launch with health check:\n"
    "    n1 flatpak_preflight(id=X) -> n2 open_app(name=X)\n"
    "    (preflight halts on broken sandbox; agent surfaces real error)\n"
    "\n"
    "  inventory + filter (e.g. 'show me my browsers'):\n"
    "    n1 mios_apps(filter='browser') -> n2 (chain only when narrowing further)\n"
    "\n"
    "  install + launch:\n"
    "    n1 winget_search(query=X) -> n2 winget_install(id=X) -> n3 open_app(name=X)\n"
    "    n1 flatpak_search(query=X) -> n2 flatpak_install(id=X) -> n3 open_app(name=X)\n"
    "\n"
    "  tile two windows:\n"
    "    n1 position_window(title=L, x=0, y=0) -> n2 resize_window(title=L, ...)\n"
    "    n3 position_window(title=R, x=HW, y=0) -> n4 resize_window(title=R, ...)\n"
    "\n"
    "When NOT to decompose (return empty nodes):\n"
    "- Web research / 'find reviews of X' / 'what's the best Y' -- the backend\n"
    "  sub-agent owns web_search/web_extract; no broker verb covers it.\n"
    "- Pure conversational / explanation requests -- those are chat, not DAG.\n"
    "- Multi-source synthesis where the planner can't fix the source list\n"
    "  upfront -- delegate to the backend sub-agent.\n"
    "- For inventory + research + ACTION like 'find my games, look up reviews,\n"
    "  launch the best': emit the FULL DAG per Example A -- the inventory verb,\n"
    "  then an AGENT node that researches + names the winner, then the action\n"
    "  verb (launch_verified) ref-ing that winner (#E). Do NOT defer the action\n"
    "  to a later turn and do NOT emit the inventory step alone: the user asked\n"
    "  for the launch to HAPPEN this turn.\n"
    "\n"
    "Rules:\n"
    "- Linearize when possible: each node depends only on its predecessor.\n"
    "- Cap your DAG at " + str(PLANNER_MAX_NODES) + " nodes.\n"
    "- Output JSON ONLY -- no preamble, no markdown, no commentary."
    )


# ── Stage-2 domain-prompt narrowing (moved verbatim from server.py) ──
# _action_domain_verbs + _planner_system_for were the planner's sole consumers in
# server; they now live beside decompose_intent (their only caller). _is_action_domain
# stays injected (server-side multi-consumer); _VERB_CATALOG / _ROUTING_DOMAINS are the
# raw SSOT injected via configure(); _render_verb_catalog is imported from
# mios_verbcatalog. Behaviour is byte-for-byte the same as in server.py.
def _action_domain_verbs() -> set:
    """Union of verbs across ALL action domains. A native GUI action spans several
    write-domains (apps_windows focus_window + computer_use cu_type/cu_key), so the
    action planner needs the cross-domain write surface, not one domain's slice."""
    out: set = set()
    for _dn, _dc in (_ROUTING_DOMAINS or {}).items():
        if _is_action_domain(_dn):
            for _v in (_dc.get("verbs") or []):
                out.add(str(_v))
    return out


def _planner_system_for(domain: Optional[str]) -> str:
    """Stage-2 of the domain router: return the planner system prompt with the
    FULL verb-catalog block swapped for ONLY the chosen domain's verbs (<20), so
    the model selects within a tight, domain-correct surface (OpenAI tool-routing
    research). FAIL-SAFE: unknown/empty domain, or any drift, -> the full prompt
    (current behaviour, nothing lost)."""
    if not domain:
        return _PLANNER_SYSTEM
    dom = _ROUTING_DOMAINS.get(domain)
    if not dom or not dom.get("verbs"):
        return _PLANNER_SYSTEM
    # Action domains: a native GUI action spans MULTIPLE write-domains (focus_window
    # + cu_type/cu_key), so widen the planner surface to the UNION of all
    # action-domain verbs (data-driven); research domains keep their tight slice.
    allowed = _action_domain_verbs() if _is_action_domain(domain) else set(dom["verbs"])
    sub = {k: v for k, v in _VERB_CATALOG.items() if k in allowed}
    if not sub:
        return _PLANNER_SYSTEM
    block = _render_verb_catalog(sub)
    if _VERB_CATALOG_RENDERED and _VERB_CATALOG_RENDERED in _PLANNER_SYSTEM:
        return _PLANNER_SYSTEM.replace(_VERB_CATALOG_RENDERED, block, 1)
    return _PLANNER_SYSTEM


async def decompose_intent(user_text: str) -> Optional[dict]:
    """Call the planner LLM to emit a DAG of dispatch verbs for a
    multi-step user intent. Returns the parsed dict, or None on
    error / unparseable response.

    Short-prompt skip: short inputs (heuristic: under the SSOT
    [planner] char/word cutoffs) almost always map to a SINGLE
    dispatch verb, not a multi-step plan. Return None so the chain
    falls through to the backend single-dispatch path -- mios-launch
    resolves the verb directly. The planner used to over-decompose
    these into 2-step DAGs whose ReWOO substitution then misfired
    on NDJSON-emitting tools."""
    if not PLANNER_ENABLED or not user_text or not user_text.strip():
        return None
    _ut = user_text.strip()
    # Stage-1 domain router : classify the intent -> show the
    # planner ONLY that domain's verbs (Stage-2 via _planner_system_for). Fail-safe:
    # _route_domain returns None -> full catalog (current behaviour, nothing lost).
    _domain = _routed_domain_var.get(None)  # routed once at the chat entry
    # Short-prompt skip: a short input usually maps to ONE dispatch, not a DAG --
    # EXCEPT an ACTION-domain command, where a short string is the normal shape
    # ("send a discord message to @someone saying hello") that still needs a
    # multi-verb GUI/tool DAG (focus_window -> cu_type -> cu_key). Bypass the skip
    # for action domains (data-driven) so the action is decomposed + executed.
    if (len(_ut) < PLANNER_SHORT_PROMPT_CHARS
            and len(_ut.split()) <= PLANNER_SHORT_PROMPT_WORDS
            and not _is_action_domain(_domain)):
        log.info("planner: short-prompt skip (%d chars, %d words)",
                 len(_ut), len(_ut.split()))
        return None
    payload = {
        "model": PLANNER_MODEL,
        "messages": [
            {"role": "system", "content": _planner_system_for(_domain)},
            {"role": "user",   "content": user_text[:4000]},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": PLANNER_MAX_TOKENS,
        "stream": False,
    }
    url = f"{PLANNER_ENDPOINT}/v1/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("planner unexpected error: %s", e)
        return None
    choices = body.get("choices") or []
    if not choices:
        return None
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        return None
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = _loads_lenient(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "nodes" not in parsed:
        return None
    nodes = parsed.get("nodes") or []
    if not isinstance(nodes, list) or len(nodes) < 2:
        return None
    if len(nodes) > PLANNER_MAX_NODES:
        nodes = nodes[:PLANNER_MAX_NODES]
        parsed["nodes"] = nodes
    # Validate each node: an `agent` node must name a registered sub-agent
    # + carry a prompt; a `tool` node must resolve to a known verb. A mixed
    # DAG (some agents, some verbs) is fine.
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            return None
        if n.get("agent"):
            if str(n["agent"]) not in _AGENT_REGISTRY:
                log.info("planner emitted unknown agent %r; discarding DAG",
                         n.get("agent"))
                return None
            if not str(n.get("prompt") or "").strip():
                log.info("planner agent node %r missing prompt; discarding",
                         n.get("id"))
                return None
            continue
        if "tool" not in n:
            return None
        if _build_dispatch_cmd(str(n["tool"]), n.get("args") or {}) is None:
            log.info("planner emitted unknown verb %r; discarding DAG",
                     n.get("tool"))
            return None
    return parsed


def _topological_order(nodes: list[dict]) -> list[dict]:
    """Return nodes in dependency order. Unknown / cyclic deps fall
    back to declaration order so we never hang."""
    by_id = {n.get("id"): n for n in nodes if isinstance(n, dict)}
    visited: set = set()
    out: list = []
    def visit(nid):
        if nid in visited or nid not in by_id:
            return
        visited.add(nid)
        for d in (by_id[nid].get("deps") or []):
            visit(d)
        out.append(by_id[nid])
    for n in nodes:
        visit(n.get("id"))
    return out


def _dag_levels(nodes: list[dict]) -> list[list[dict]]:
    """Group nodes into concurrent execution LEVELS (Kahn layering): each
    level is the set of not-yet-run nodes whose deps are ALL already
    satisfied, so every node in a level can run CONCURRENTLY. A level only
    starts after all earlier levels finish, preserving topological order
    (so ReWOO #E<id> refs resolve). Cyclic / dangling deps degrade to one
    forced node per round (declaration order) so the DAG never hangs --
    same safety stance as _topological_order."""
    by_id = {n.get("id"): n for n in nodes
             if isinstance(n, dict) and "id" in n}
    remaining = [n for n in nodes if isinstance(n, dict) and "id" in n]
    done: set = set()
    levels: list[list[dict]] = []
    while remaining:
        ready = [n for n in remaining
                 if all((d in done) or (d not in by_id)
                        for d in (n.get("deps") or []))]
        if not ready:  # cycle / dangling dep -- force progress, no hang
            ready = [remaining[0]]
        levels.append(ready)
        ready_ids = {n.get("id") for n in ready}
        done |= ready_ids
        remaining = [n for n in remaining if n.get("id") not in ready_ids]
    return levels
