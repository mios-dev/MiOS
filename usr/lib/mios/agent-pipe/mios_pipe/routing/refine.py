# AI-hint: REFINE intent-classifier extracted verbatim from server.py (refactor R5/mios_refine wave). The PRIMARY pre-router pass -- refine_intent() calls the micro/refine model (own httpx) and parses the strict-json envelope into the intent/refined_text/news/web/local_state/needs_location/browser_action/domain_type/multi_task fields that feed all downstream routing, plus _salvage_refine_dispatch (recover a one-verb dispatch when the model NARRATES instead of emitting JSON) and the load-bearing classifier prompts _REFINE_SYSTEM / _REFINE_SYSTEM_LITE (moved byte-for-byte -- a single altered character changes routing behavior). Sibling imports: loads_lenient (mios_jsonsalvage), _env_grounding (mios_grounding), _deterministic_action_route (mios_routing), mios_tokenize. Every symbol that STAYS in server.py (logger, the config consts REFINE_*, the _VERB_CATALOG/_AGENT_REGISTRY/_FASTPATH_VERBS/routing-phrase globals, _over_global_ceiling/_resolve_verb_key/_route_domain/_routed_domain_var, the _db_* writers) is dependency-INJECTED via configure() under its EXACT original server name (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim + re-applies the @_traced_stage("refine") span at the boundary (surface-parity zero-diff).
# AI-related: server.py (host of the DI deps + re-import site), mios_routing (_deterministic_action_route + the SSOT routing-phrase loaders), mios_grounding (_env_grounding), mios_jsonsalvage (loads_lenient), mios_tokenize (history truncation), mios_config (config SSOT).
# AI-functions: refine_intent, _salvage_refine_dispatch, configure
"""MiOS agent-pipe -- REFINE intent classifier (extracted from server.py).

Verbatim move: the refine pass is the primary classifier feeding routing.
The _REFINE_SYSTEM / _REFINE_SYSTEM_LITE prompts and the refine_intent /
_salvage_refine_dispatch bodies are byte-identical to their server.py origin
(prompt-sensitive -- do not edit). server.py injects every dep that stays
behind via :func:`configure` and re-imports the names verbatim.
"""

import asyncio
import json
import inspect
import os
import re
import time
from typing import Optional, Callable, Any

import httpx

import mios_tokenize
from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_grounding import _env_grounding, _env_grounding_static, _env_grounding_dynamic
from mios_routing import _deterministic_action_route
# Heavy-path critic->refiner consumes the DCI Challenger critic directly (sibling,
# one-way boundary -- mios_dci never imports this module nor server). DCI_ENABLED /
# DCI_FLOW_TRIGGER_CONF are stable import-time constants in mios_dci (configure()
# there only rebinds the _db_* writers), so importing them verbatim mirrors how
# server.py froze the same values -- behaviour-identical.
from mios_dci import dci_critic_pass, DCI_ENABLED, DCI_FLOW_TRIGGER_CONF


# -- Dependency-injection seam ------------------------------------------------
# Everything below stays in server.py (config consts, the live verb/agent
# catalogs + routing-phrase globals, the ceiling/verb-resolve/domain-route
# helpers, the contextvar, the _db_* writers, the logger). server.py calls
# configure(...) with these AFTER they are all defined (one-way boundary: this
# module never imports server). They keep their ORIGINAL server.py names because
# the moved bodies reference them verbatim. The classifier is only invoked at
# request time -- well after configure() has injected everything; the loaders'
# defaults below just keep import + the surface check working before injection.
log = None
_AGENT_REGISTRY: dict = {}
_VERB_CATALOG: dict = {}
_routed_domain_var = None
_over_global_ceiling = None
_resolve_verb_key = None
_route_domain = None
_db_fire = None
_db_post = None
_db_create = None
REFINE_ENABLED = False
REFINE_MODEL = ""
REFINE_ENDPOINT = ""
REFINE_MAX_TOKENS = 700
REFINE_TIMEOUT_S = 30
REFINE_ATTEMPTS = 2
_OS_CONTROL_VERBS_RENDERED = ""
_BROWSER_ACTION_ALT = ""
_WEB_SEARCH_TRIGGERS: list = []
_WEB_SEARCH_CONTEXTS: list = []
_REMEMBER_TRIGGERS: list = []
_FASTPATH_VERBS = frozenset()
_ROUTING_ENABLE = False
_ROUTING_DOMAINS: dict = {}
# Routing length/word cutoffs (SSOT: mios.toml [refine]; injected via
# configure() from server.py). These feed BOTH the runtime promotion guards
# AND the classifier prompt's char cues -- the SAME constant renders the cue and
# gates the decision, so they can never drift apart. The values below are the
# single documented baseline; behaviour is identical at them and an operator
# override in mios.toml shifts cue + gate together.
REFINE_CHAT_CHARS = 40              # prompt cue: chat is for very short conversational input
REFINE_DISPATCH_CHARS = 60         # prompt cue: dispatch is for short verb invocations
REFINE_PROMOTE_CHARS = 100         # >this -> promote a shallow chat/dispatch to agent (also a prompt cue)
REFINE_DISPATCH_ARG_MAX_WORDS = 3  # a dispatch arg with more words is a semantic phrase -> agent
# Heavy-path critic->refiner knobs (SSOT [agent-pipe] env, read in server.py and
# injected via configure()). The session-event emitter stays in server.py (it
# writes the session-scoped event stream) and is injected under its original name.
# Baselines below match the server env defaults so import + the surface check work
# before injection; configure() overwrites them with the SSOT values.
_emit_session_event = None
CRITIC_REFINE_ENABLED = True
CRITIC_REFINE_MAX = 1
CRITIC_REFINE_MIN_CHARS = 500


def configure(*, logger=None, agent_registry=None, verb_catalog=None,
              routed_domain_var=None, over_global_ceiling=None,
              resolve_verb_key=None, route_domain=None,
              db_fire=None, db_post=None, db_create=None,
              refine_enabled=None, refine_model=None, refine_endpoint=None,
              refine_max_tokens=None, refine_timeout_s=None, refine_attempts=None,
              os_control_verbs_rendered=None, browser_action_alt=None,
              web_search_triggers=None, web_search_contexts=None,
              remember_triggers=None, fastpath_verbs=None,
              routing_enable=None, routing_domains=None,
              promote_chars=None, dispatch_arg_max_words=None,
              chat_chars=None, dispatch_chars=None,
              emit_session_event=None, critic_refine_enabled=None,
              critic_refine_max=None, critic_refine_min_chars=None) -> None:
    """Inject the server.py symbols the refine classifier reads. Each arg keeps
    its original server name as a module global; None means 'leave as-is' so a
    partial re-inject (e.g. the live agent-registry refresh) is safe. The routing
    cutoff args (promote_chars / dispatch_arg_max_words / chat_chars /
    dispatch_chars) carry the SSOT [refine] thresholds; injecting any of them
    re-renders _REFINE_SYSTEM so its length cues match the new gates."""
    global log, _AGENT_REGISTRY, _VERB_CATALOG, _routed_domain_var
    global _over_global_ceiling, _resolve_verb_key, _route_domain
    global _db_fire, _db_post, _db_create
    global REFINE_ENABLED, REFINE_MODEL, REFINE_ENDPOINT
    global REFINE_MAX_TOKENS, REFINE_TIMEOUT_S, REFINE_ATTEMPTS
    global _OS_CONTROL_VERBS_RENDERED, _BROWSER_ACTION_ALT
    global _WEB_SEARCH_TRIGGERS, _WEB_SEARCH_CONTEXTS, _REMEMBER_TRIGGERS
    global _FASTPATH_VERBS, _ROUTING_ENABLE, _ROUTING_DOMAINS
    global REFINE_CHAT_CHARS, REFINE_DISPATCH_CHARS, REFINE_PROMOTE_CHARS
    global REFINE_DISPATCH_ARG_MAX_WORDS, _REFINE_SYSTEM
    global _emit_session_event, CRITIC_REFINE_ENABLED
    global CRITIC_REFINE_MAX, CRITIC_REFINE_MIN_CHARS
    if logger is not None:
        log = logger
    if agent_registry is not None:
        _AGENT_REGISTRY = agent_registry
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if routed_domain_var is not None:
        _routed_domain_var = routed_domain_var
    if over_global_ceiling is not None:
        _over_global_ceiling = over_global_ceiling
    if resolve_verb_key is not None:
        _resolve_verb_key = resolve_verb_key
    if route_domain is not None:
        _route_domain = route_domain
    if db_fire is not None:
        _db_fire = db_fire
    if db_post is not None:
        _db_post = db_post
    if db_create is not None:
        _db_create = db_create
    if refine_enabled is not None:
        REFINE_ENABLED = refine_enabled
    if refine_model is not None:
        REFINE_MODEL = refine_model
    if refine_endpoint is not None:
        REFINE_ENDPOINT = refine_endpoint
    if refine_max_tokens is not None:
        REFINE_MAX_TOKENS = refine_max_tokens
    if refine_timeout_s is not None:
        REFINE_TIMEOUT_S = refine_timeout_s
    if refine_attempts is not None:
        REFINE_ATTEMPTS = refine_attempts
    if os_control_verbs_rendered is not None:
        _OS_CONTROL_VERBS_RENDERED = os_control_verbs_rendered
    if browser_action_alt is not None:
        _BROWSER_ACTION_ALT = browser_action_alt
    if web_search_triggers is not None:
        _WEB_SEARCH_TRIGGERS = web_search_triggers
    if web_search_contexts is not None:
        _WEB_SEARCH_CONTEXTS = web_search_contexts
    if remember_triggers is not None:
        _REMEMBER_TRIGGERS = remember_triggers
    if fastpath_verbs is not None:
        _FASTPATH_VERBS = fastpath_verbs
    if routing_enable is not None:
        _ROUTING_ENABLE = routing_enable
    if routing_domains is not None:
        _ROUTING_DOMAINS = routing_domains
    if emit_session_event is not None:
        _emit_session_event = emit_session_event
    if critic_refine_enabled is not None:
        CRITIC_REFINE_ENABLED = critic_refine_enabled
    if critic_refine_max is not None:
        CRITIC_REFINE_MAX = critic_refine_max
    if critic_refine_min_chars is not None:
        CRITIC_REFINE_MIN_CHARS = critic_refine_min_chars
    _cuts_changed = False
    if chat_chars is not None:
        REFINE_CHAT_CHARS = int(chat_chars)
        _cuts_changed = True
    if dispatch_chars is not None:
        REFINE_DISPATCH_CHARS = int(dispatch_chars)
        _cuts_changed = True
    if promote_chars is not None:
        REFINE_PROMOTE_CHARS = int(promote_chars)
        _cuts_changed = True
    if dispatch_arg_max_words is not None:
        REFINE_DISPATCH_ARG_MAX_WORDS = int(dispatch_arg_max_words)
    # Re-render the prompt's length cues whenever a char cutoff is (re)injected so
    # the cue numbers track the runtime gate (one SSOT, no drift).
    if _cuts_changed:
        _REFINE_SYSTEM = _build_refine_system()


def _build_refine_system() -> str:
    """Render the full REFINE classifier prompt, interpolating the SSOT length
    cues (REFINE_CHAT_CHARS / REFINE_DISPATCH_CHARS / REFINE_PROMOTE_CHARS) into
    the 'Length cue' block so the prompt's char hints always match the runtime
    promotion guards (one constant feeds both). Byte-identical to the original
    apart from those three interpolated cue numbers; configure() re-renders it
    after the cutoffs are injected so an mios.toml override flows into the cue."""
    return (
    "You are MiOS-Agent's refine pass. Read the user's message and\n"
    "the recent chat history. Emit a single JSON object describing\n"
    "what the user wants AND how to achieve it. Be terse -- output\n"
    "is consumed by another agent, NOT shown to the user.\n"
    "\n"
    "Schema:\n"
    '  {\n'
    '    "intent": "<one of: chat | dispatch | agent | dag | multi_task>",\n'
    '    "refined_text": "<rewritten user query in clear, actionable form>",\n'
    '    "intended_outcome": "<one short line: what the user expects back>",\n'
    '    "target_agent": "<one of the registered sub-agents -- pick by role>",\n'
    '    "hint_tools":  ["<verb-name-1>", "<verb-name-2>", ...],\n'
    '    "hint_skills": ["<skill-name-1>", ...],\n'
    '    "reply": "<for intent=chat: your reply directly; omit otherwise>",\n'
    '    "tasks": [   // ONLY for intent=multi_task. One entry per\n'
    '                 //   discrete goal the user crammed into one prompt.\n'
    '      {\n'
    '        "title":            "<short imperative -- one line>",\n'
    '        "refined_text":     "<rewritten subtask, agent-ready>",\n'
    '        "intended_outcome": "<what success looks like for THIS task>",\n'
    '        "target_agent":     "<role-matched sub-agent>",\n'
    '        "hint_tools":       ["..."],\n'
    '        "hint_skills":      ["..."],\n'
    '        "priority":         1,  // lower runs first; 1..N\n'
    '        "depends_on":       []  // task indices this one waits for;\n'
    '                                //   empty = runs first / in parallel\n'
    '      }, ...\n'
    '    ],\n'
    '    "tool_cards": [   // OPTIONAL but PREFERRED for intent in\n'
    '                      //   {agent, dag, multi_task}. Per-step\n'
    '                      //   guidance carried INTO the sub-agent\n'
    '                      //   dispatch so it knows WHY each tool is\n'
    '                      //   hinted + what success looks like. Lifts\n'
    '                      //   the planning burden off the worker.\n'
    '      {\n'
    '        "tool":              "<verb-name or skill-name>",\n'
    '        "args_hint":         {"key": "value", ...},\n'
    '        "why":               "<one line: why THIS tool for THIS step>",\n'
    '        "success_predicate": "<short check: how to know it worked>",\n'
    '        "output_used_by":    [<idx-of-step-that-consumes-this>]\n'
    '      }, ...\n'
    '    ]\n'
    '  }\n'
    "\n"
    "REASON -> PLAN -> DELEGATE meta-rule:\n"
    "  An 'open / find / install / launch / use / run / start / show /\n"
    "  reveal X' intent NEVER routes to `chat`. NEITHER does any request\n"
    "  for CURRENT or EXTERNAL information: 'search the web for', 'look\n"
    "  up', 'latest', 'today', 'news', 'recent', \"what's trending\",\n"
    "  prices, weather, scores, or ANY fact not answerable from THIS\n"
    "  conversation alone. Those need the agent's web_search / web_extract\n"
    "  tools -- pick `agent` (or `dag`). Decide local-vs-web by intent: a\n"
    "  file/app on THIS computer -> agent with directory_lookup/\n"
    "  everything_search/fs_search; current world info -> agent with\n"
    "  web_search/web_extract. The downstream agent must fan out across\n"
    "  discovery/search surfaces before deciding -- never refuse or\n"
    "  chat-reply without trying. Refine-time `chat` is RESERVED for\n"
    "  greetings / thanks / single-turn conversational text with NO action\n"
    "  verb AND no external-info need.\n"
    "\n"
    "Intent classification:\n"
    "  chat        -- greeting, thanks, single-turn conversation; no system\n"
    "                 effect needed; emit `reply` and no agent is called.\n"
    "                 NOT for any 'open / find / launch / install / show /\n"
    "                 reveal / run / start <X>' intent -- those need\n"
    "                 tools and must route to `agent` or `dag`.\n"
    "  dispatch    -- maps to ONE MiOS verb; tool + args populated by the\n"
    "                 existing router. Refine just rewrites refined_text.\n"
    "  agent       -- needs a sub-agent for ONE coherent goal. Pick\n"
    "                 target_agent by role:\n"
    "                 * general    (Hermes)        -- broad reasoning + tools\n"
    "                 * coding     (OpenCode)      -- file edits / refactor / git\n"
    "                 * telemetry  (mios-daemon-agent) -- 'what just happened?',\n"
    "                              log/journal tail, recent system activity\n"
    "                              follow-ups. Pinned to 2 cores; always-on.\n"
    "  dag         -- ONE goal broken into multiple dependent steps; the\n"
    "                 planner will decompose. target_agent can be empty.\n"
    "  multi_task  -- the user crammed SEVERAL INDEPENDENT goals into one\n"
    "                 prompt (e.g. 'open chrome AND install vscode AND\n"
    "                 summarize my journal'). Emit a `tasks` array with one\n"
    "                 entry per discrete goal, ordered by priority. The\n"
    "                 dispatcher runs task #1 immediately, queues the rest\n"
    "                 in kanban for sequential execution.\n"
    "\n"
    "RULES:\n"
    "- ALWAYS emit valid JSON. No prose around it.\n"
    "- `hint_tools` lists MiOS verb names you think the agent will need\n"
    "  (open_app, focus_window, text_view, winget_search, ...).\n"
    "- For 'find <X>' / 'where is <X>' / 'show me the <X> file' queries,\n"
    "  ALWAYS hint `directory_lookup` -- sub-100ms DB query against the\n"
    "  mios-daemon cache (~19k indexed entries). Falls back to\n"
    "  `everything_search` (Windows-side live search) or `fs_search`\n"
    "  (Linux-side deep walk) only when the cache misses.\n"
    "- DURABLE MEMORY + KNOWLEDGE actions map to verbs -- do NOT just\n"
    "  acknowledge them in `chat`. When the user asks you to KEEP/REMEMBER/\n"
    "  SAVE/NOTE a durable fact -> intent=dispatch tool=`remember`. To READ\n"
    "  back what was saved -> `recall`. To CONDENSE a doc/text into tiers ->\n"
    "  `summarize`. To pull local files/notes into the knowledge vault ->\n"
    "  `ingest`. To NAVIGATE/SEARCH the stored second brain -> `viking_ls`/\n"
    "  `viking_find`/`viking_cat`. To run a code snippet SAFELY in a sandbox\n"
    "  -> `coderun`. These are real effects; a bare conversational 'noted'\n"
    "  with no verb is WRONG when the user asked you to remember/save it.\n"
    "- `hint_skills` lists C.2 skill names from the catalog\n"
    "  (open-and-focus, install-flatpak-app, window-tile-side-by-side).\n"
    "- For conversational input (greetings, small talk, single-turn\n"
    "  questions like 'how are you', acknowledgements, thanks):\n"
    "  pick intent=chat AND populate `reply` with a brief, natural\n"
    "  response. Do NOT delegate to a sub-agent. Examples that should\n"
    "  ALWAYS be chat: 'hey', 'hi', 'hello', 'thanks', 'thank you',\n"
    "  'how's it going', 'how are you', 'good morning', 'bye'.\n"
    "  When in doubt about conversational vs. agent: if the user is\n"
    "  not asking for a system action / file / data / code, chat.\n"
    "- multi_task vs dag: dag = ONE goal, dependent steps (e.g. 'install\n"
    "  vscode and open it'). multi_task = SEVERAL goals, independent\n"
    "  (e.g. 'install vscode AND THEN ALSO summarize my journal AND\n"
    "  THEN ALSO post a status to discord'). Three+ unrelated\n"
    "  imperatives joined by `and`/`also`/`then` is the multi_task tell.\n"
    "- multi_task MUST emit `tasks` with >= 2 entries. If you only\n"
    "  find one goal, use intent=agent or intent=dag instead.\n"
    "- RESEARCH-AND-REPORT: when the goal is to GATHER information on one\n"
    "  or more topics and report the findings back IN THE ANSWER (rather\n"
    "  than putting something on the operator's screen), it is research,\n"
    "  not launching. Decompose into one INDEPENDENT research task per\n"
    "  topic so they dispatch CONCURRENTLY (depends_on empty), each\n"
    "  delegated to a web_search-capable sub-agent that fetches + reads\n"
    "  page content via Hermes's native Chrome browsing; finish with a\n"
    "  synthesis step that combines the findings into one report. NEVER\n"
    "  map a 'check / look up / find out <topic>' goal to open_url or to\n"
    "  opening a visible browser window per topic -- open_url only SHOWS a\n"
    "  page the operator explicitly asked to see.\n"
    "- EXPLICIT-TARGET LAUNCH (decisive, OVERRIDES research): when the user\n"
    "  names a browser/app to open something IN or WITH it ('open <X> in\n"
    "  epiphany', 'show <url> in GNOME Web', 'pull <page> up in chrome',\n"
    "  'open epiphany to <url>'), the operator wants a WINDOW ON SCREEN, not\n"
    "  a report. This is ALWAYS intent=dispatch, tool=open_url, args=\n"
    "  {\"url\": <resolved real URL>, \"browser\": <the named app>}. NEVER\n"
    "  route a named-browser launch to research / web_search / agent. The\n"
    "  named app target (a browser the operator points at) is the decisive\n"
    "  tell. Resolve a page description to its real URL ('the Wikipedia\n"
    "  main page' -> https://en.wikipedia.org/wiki/Main_Page).\n"
    "- BREADTH = FACETS: a BROAD or COMPREHENSIVE ask about a SINGLE topic\n"
    "  (the user wants 'everything', the 'full picture', 'all the latest', a\n"
    "  wide/deep overview) is multi_task too -- split the ONE topic into 2-4\n"
    "  INDEPENDENT FACETS of it (distinct angles / sub-topics / regions /\n"
    "  sectors) and emit one research task per facet so they dispatch\n"
    "  CONCURRENTLY, then synthesise. A wide ask deserves a real swarm, not\n"
    "  one shallow pass. (A narrow single-fact question stays intent=agent.)\n"
    "- `tool_cards` rationale (ReWOO + MCP-style annotations): the\n"
    "  worker agent (Hermes / OpenCode / daemon-agent) sees ONLY what\n"
    "  you emit. If you list tools in hint_tools but the worker has\n"
    "  no idea WHY each one was hinted, it'll re-derive the plan\n"
    "  itself (slow + error-prone). Per-step `tool_cards` carry the\n"
    "  WHY + the success predicate, so the worker just executes. For\n"
    "  multi-step goals (3+ tool calls), emit tool_cards even when\n"
    "  intent stays `agent` -- they're additive guidance, not a new\n"
    "  intent class. Skip tool_cards for intent=chat or single-step\n"
    "  dispatch (no value vs. cost).\n"
    "- For dag: tool_cards' `output_used_by` lets the worker chain\n"
    "  step outputs (e.g. step 0 lists games -> step 1 web_search\n"
    "  ratings -> step 2 launches winner). Worker substitutes #E0,\n"
    "  #E1 placeholders into args at execute time -- you don't have\n"
    "  to know the runtime values.\n"
    "\n"
    "Length cue (CRITICAL): intent=chat is for SHORT conversational\n"
    "inputs (~ <" + str(REFINE_CHAT_CHARS) + " chars: 'hi', 'how are you', 'thanks'). intent=\n"
    "dispatch is for SHORT verb invocations (~ <" + str(REFINE_DISPATCH_CHARS) + " chars: 'open\n"
    "chrome', 'launch steam', 'screenshot'). If the user_text is\n"
    "LONG (>" + str(REFINE_PROMOTE_CHARS) + " chars) it almost certainly describes a multi-step\n"
    "goal -- pick intent=dag (or multi_task for unrelated parallel\n"
    "goals) and decompose. A long-text intent=dispatch is almost\n"
    "always wrong -- the args would have to carry a semantic\n"
    "descriptor (e.g. 'the highest reviewed game I have installed')\n"
    "which the launcher can't resolve to a real app.\n"
    "\n"
    "Arg-concreteness rule: when emitting intent=dispatch, every\n"
    "args value MUST be a concrete identifier (app name, file\n"
    "path, URL, fully-qualified id). NEVER a semantic phrase\n"
    "('highest', 'best', 'the one with X', 'whichever is fastest').\n"
    "Do NOT invent or guess command-line arguments (e.g. '--big-picture' or\n"
    "'-bigpicture') for open_app/launch_app. If the requested mode or target\n"
    "has a native URI protocol (like steam://open/bigpicture for Steam Big Picture\n"
    "mode), use that native URI directly as the app target name/URL.\n"
    "If the right value can't be known without first running other\n"
    "tools, pick intent=dag with the lookup as step 0 and the\n"
    "dispatch as a downstream node using #E0 substitution.\n"
    "\n"
    "Strict version grounding rule: Do NOT guess, assume, or append specific version numbers,\n"
    "release versions, or hardware specifications (e.g. '4', '5', '6', '2026') unless they\n"
    "are explicitly requested by the user or present in the chat history/context. Keep generic brand\n"
    "or product names (e.g. 'spotify' or 'photoshop') EXACTLY as requested in the refined query\n"
    "so that downstream search/resolver tools can check the actual installed system inventory.\n"
    )


# Built once at import from the baseline cutoffs (byte-identical to the original
# constant). configure() re-renders it after server.py injects the SSOT cutoffs
# so an mios.toml override of the length cues propagates; server.py re-imports
# the rebuilt value after its configure() call (surface-parity zero-diff).
_REFINE_SYSTEM = _build_refine_system()


# Compact "light refine" prompt (operator architecture the
# micro just classifies + lightly refines/contextualizes; heavy step
# planning belongs to the planner downstream). The full _REFINE_SYSTEM
# above is ~1500 tokens -> 14-26s prefill on the 0.6b CPU micro AND
# confused its classification (called a web query "chat"). This tight
# version is ~450 tokens -> a few seconds, and the 0.6b classifies the
# same web query correctly (operator test).
_REFINE_SYSTEM_LITE = (
    "You are MiOS-Agent's refine pass. Read the user's message + recent\n"
    "history and output ONE compact JSON object (no prose).\n"
    "\n"
    "Fields:\n"
    '  "intent": chat | dispatch | agent | multi_task   (coarse -- the\n'
    "    planner decides single-step vs multi-step downstream)\n"
    '  "refined_text": the request rewritten as a clear, ACTIONABLE query.\n'
    "    For follow-up / contextual requests (e.g. 'research further', 'tell me more',\n"
    "    'explain the second one', 'why?', 'show links'), you MUST resolve all relative\n"
    "    references and details from the chat history into a fully detailed and explicit\n"
    "    rewritten query (e.g. 'detailed background and additional news on Volkswagen cost-cutting\n"
    "    production cuts in China July 2026') rather than repeating the generic query.\n"
    "    For current / recent / live info (news, events, trends, prices,\n"
    "    scores), make it a CONCRETE search query anchored to NOW (use the\n"
    "    current date or 'today' / 'latest') and DISAMBIGUATE any vague word a\n"
    "    search engine would mis-match to a brand / product / unrelated term\n"
    "    (e.g. a bare 'current' or 'trending' that hits an app or a\n"
    "    dictionary). This is the string the web search actually runs.\n"
    "    Do NOT guess, assume, or append specific version numbers, release\n"
    "    versions, or hardware specifications (e.g. '4', '5', '6', '2026') unless\n"
    "    explicitly requested or present in the context. Keep generic brand or\n"
    "    product names (e.g. 'spotify' or 'photoshop') EXACTLY as requested\n"
    "    so downstream resolver/search tools can match local system inventory.\n"
    "    Do NOT invent/guess CLI arguments (like '--big-picture'). If a mode has\n"
    "    a native URI scheme (e.g. steam://open/bigpicture), use it as the app target.\n"
    '  "news": recency-anchored / current-events / "latest" asks (a NEWS index\n'
    "    beats a general web search).\n"
    '  "web": ANY external-knowledge gap -- a fact about the outside world you are\n'
    "    not certain of. When unsure, prefer web; NEVER fabricate facts or citations.\n"
    "  Classify by what the ask NEEDS, never by a keyword.\n"
    '  "needs_location": true when answering REQUIRES the user\'s OWN physical\n'
    "    location -- weather, 'near me' / nearby / local services, directions,\n"
    "    what's on locally, distance-from-here. The pipeline resolves it from the\n"
    "    forwarded client location; if NONE was forwarded it ASKS the user for\n"
    "    their city rather than guessing one. NEVER put a 'my current location' /\n"
    "    '[location]' placeholder in refined_text -- if a real city was forwarded\n"
    "    use it, otherwise leave the place OUT and set this flag. Classify by what\n"
    "    the ask NEEDS. Omit/false otherwise.\n"
    '  "browser_action": true ONLY when the user wants the agent to PERFORM an\n'
    "    INTERACTIVE action ON a website or app -- sign up, log in, set up an\n"
    "    account or price alert, book, fill in + SUBMIT a form, post, or change\n"
    "    settings on a site -- i.e. DO something, not just LOOK UP / find out\n"
    "    information. Keep intent=agent; the browser-capable agent carries the\n"
    "    action out with its live browser. Omit/false for pure research/lookup.\n"
    '  "local_state": true when the answer comes from inspecting THIS computer\'s\n'
    "    OWN live state -- system/hardware (CPU/GPU/memory/disk), running services\n"
    "    or processes, containers, INSTALLED apps/games, recent logs/activity, or\n"
    "    MiOS's own status -- NOT from the web. The pipeline runs LOCAL read tools\n"
    "    (system_status, mios_apps, process_list, ...) and will NOT web-search (a\n"
    "    web search for local machine state returns irrelevant junk -- random\n"
    "    files, dictionaries, brand names). Keep intent=agent.\n"
    "    HYBRID -- local_state and web are NOT mutually exclusive: set BOTH\n"
    "    local_state:true AND web:true when the question names something ON this\n"
    "    machine but ALSO needs knowledge that exists only OFF it -- the\n"
    "    theoretical specs / benchmarks / ratings / latest version / capabilities\n"
    "    of a component you must first IDENTIFY locally (e.g. 'the theoretical AI\n"
    "    performance of MY GPU', 'is my installed X the latest version', 'how does\n"
    "    my CPU compare to ...'). The pipeline then grounds on BOTH the local read\n"
    "    tools AND web_search and combines them -- judge by MEANING, not keywords;\n"
    "    do NOT drop the web half just because the question says 'this/my system'.\n"
    "    Otherwise omit/false for anything that needs EXTERNAL / web information. A\n"
    "    technology or product\n"
    "    COMPARISON or general research question ('compare X vs Y vs Z', 'best\n"
    "    tool for ...', 'which database for ...') is NOT local_state even if it\n"
    "    mentions caches, databases, or systems -- it needs external knowledge.\n"
    '  "inventory_filter": ONLY with local_state -- when the question targets a\n'
    "    SPECIFIC category/kind of installed thing ('what GAMES do I have',\n"
    "    'list my browsers', 'show installed editors'), the short substring to\n"
    "    filter the app inventory by (e.g. 'games', 'browser', 'editor'). Lets\n"
    "    the pipeline pull a SMALL focused list instead of the whole inventory.\n"
    "    OMIT for a general 'what's installed / list all apps'. Your choice of\n"
    "    word, not a fixed list.\n"
    '  "state_scope": ONLY with local_state. "live" = what is OPEN / RUNNING NOW\n'
    "    (open windows, running apps/processes, active containers, current\n"
    '    CPU/GPU/mem/disk use); "inventory" = what is INSTALLED on disk\n'
    '    (apps/games); omit or "both" = a general system overview. Routes which\n'
    "    local read tools fire -- e.g. 'what's open' -> live -> the OPEN WINDOWS,\n"
    "    not the whole installed-app catalogue. Classify the question's MEANING,\n"
    "    not by keywords.\n"
    '  "domain_type": "internal" | "external" | "both" -- the FUNDAMENTAL domain\n'
    "    of the request. internal = answered or done ENTIRELY on THIS machine (a\n"
    "    local_state read OR a local action/dispatch); external = answered ENTIRELY\n"
    "    from the web / outside world (research, news, lookups, comparisons of\n"
    "    EXTERNAL products); both = genuinely needs a LOCAL part AND an EXTERNAL\n"
    "    part together (e.g. 'compare MY installed GPUs to the latest online\n"
    "    benchmarks', 'check my running services then look up each one's newest\n"
    "    version', 'what games do I have and which got the best reviews this\n"
    "    year'). When both: ALSO set intent=multi_task and put the LOCAL facet(s)\n"
    "    and the EXTERNAL facet(s) as SEPARATE tasks -- mark each LOCAL facet with\n"
    '    "local_state": true and each EXTERNAL facet with "web": true -- so they\n'
    "    run CONCURRENTLY and a synthesis combines them. Classify by what the\n"
    "    request NEEDS, never by keywords.\n"
    '  "intended_outcome": one line -- what the user expects back\n'
    '  "target_agent": a registered sub-agent chosen by role\n'
    '  "hint_tools": [verb names the agent will need -- ONLY names that appear\n'
    "    in the action-verb catalog injected below. If no listed verb clearly\n"
    "    fits, OMIT this field. NEVER invent a verb name (no guessing plausible\n"
    "    names like 'flight_search' / 'journalctl_tail') -- an unlisted name\n"
    "    fails downstream; omitting is always safer than inventing.]\n"
    '  "tool": ONLY for intent=dispatch -- the exact verb name (one of the\n'
    '    verbs listed in the action-verb catalog below)\n'
    '  "args": ONLY for intent=dispatch -- that verb\'s arguments as a JSON\n'
    "    object, using the concrete target the user named\n"
    '  "reply": ONLY when intent=chat -- your short direct reply\n'
    '  "tasks": ONLY when intent=multi_task -- one entry per goal\n'
    "\n"
    "Classify by what the request fundamentally NEEDS, never by keywords:\n"
    "  chat = the user only wants conversation; the answer is already\n"
    "    fully contained in ordinary dialogue -- nothing must be looked\n"
    "    up, fetched, computed, or done on the machine. Emit reply.\n"
    "  dispatch = ONE single, concrete machine ACTION that maps to exactly one\n"
    "    of the verbs listed below: an OS-control action on a NAMED target\n"
    "    (launch / open / close / focus / move / resize a SPECIFIC app or window;\n"
    "    open a SPECIFIC URL) -- EXACTLY ONE target. If the request names MORE THAN\n"
    "    ONE distinct app/action to act on, it is NOT dispatch -- use intent=agent\n"
    "    so the agent performs EACH in turn (dispatch fires only one and drops the\n"
    "    rest). OR a STANDING/RECURRING request -- 'do X every N\n"
    "    minutes/hours', 'each day', 'keep me updated on X', 'check X regularly'\n"
    "    -> the `schedule` verb (args: prompt=the task, every=the interval). A\n"
    "    request that says to REPEAT on an interval is `schedule`, NOT one-shot\n"
    "    research, even if X itself is a research topic. Emit `tool` (that verb's\n"
    "    name) and `args` (its\n"
    "    arguments). For the target, use ONLY the bare app / window / URL NAME\n"
    "    the user named -- STRIP conversational filler ('for me', 'on my pc',\n"
    "    'please', 'now', 'real quick'): 'focus Spotify for me on my pc'\n"
    "    -> tool=focus_window args={title:'Spotify'}. Use dispatch ONLY\n"
    "    when the target is a concrete identifier that can be passed straight\n"
    "    to the verb -- if the target is vague ('the best browser', 'highest-\n"
    "    rated game') or the request needs lookup / research / several steps,\n"
    "    use agent instead. For a plain launch/open prefer launch_app or\n"
    "    open_app -- the fast-path itself confirms the action by diffing a\n"
    "    before/after window enumeration, so no separate verify verb is needed.\n"
    "  agent = the user wants something DONE on this computer, or KNOWN\n"
    "    from information not already present in this conversation. The\n"
    "    agent owns the tools (system control, local file search, web\n"
    "    search/extract) and must USE them rather than guess or refuse.\n"
    "  multi_task = the request needs SEVERAL INDEPENDENT pieces of work that\n"
    "    can each run on their own with NO shared result. Use it when EITHER:\n"
    "    (a) the user lists several distinct goals in one message ('open chrome\n"
    "    AND list my games AND remind me at 3pm'), OR (b) a SINGLE topic spans\n"
    "    clearly SEPARABLE facets that benefit from concurrent research AND a\n"
    "    plain 'agent' single loop would have to serialise them (e.g. compare\n"
    "    several named items; cover distinct regions/angles the user named). In\n"
    "    case (b) split into 2-4 facets, one tasks entry each, so they research\n"
    "    CONCURRENTLY and a synthesis combines them. Do NOT split a single\n"
    "    coherent question that one agent loop answers well ('tell me about X',\n"
    "    'what is Y') -- that is intent=agent, not multi_task. A narrow\n"
    "    single-fact ask is NEVER multi_task. Emit a tasks array (>=2 entries).\n"
    "    CRITICAL -- the BOTH case (domain_type=both): when ONE request mixes a\n"
    "    LOCAL / this-machine part AND an EXTERNAL / web part, you MUST emit\n"
    "    intent=multi_task with the two as SEPARATE tasks so they run\n"
    "    concurrently -- one task for the LOCAL facet (set that task's\n"
    "    \"local_state\": true) and one for the EXTERNAL/web facet (set that\n"
    "    task's \"web\": true). NEVER collapse it to a single intent=agent that\n"
    "    only does the local half and INVENTS the web half. Example: 'what GPU is\n"
    "    in this machine and what are the newest GPUs released this year' ->\n"
    "    intent=multi_task, domain_type=both, tasks=[\n"
    "      {\"title\":\"this machine's GPU\",\"local_state\":true,\"refined_text\":\n"
    "       \"report the installed GPU model from local system state\"},\n"
    "      {\"title\":\"newest GPUs 2026\",\"web\":true,\"refined_text\":\n"
    "       \"newest GPUs released in 2026\"}].\n"
    "    multi_task is for INDEPENDENT work only -- goals or facets that could\n"
    "    each run on their own, none needing another's RESULT (run as parallel\n"
    "    tool calls). When a single goal's later step instead CONSUMES an\n"
    "    earlier step's output, that is NOT multi_task: it is one agent running\n"
    "    the standard tool-calling loop, issuing tool calls in order so the\n"
    "    final action uses the RESOLVED value, not a description of it. Classify\n"
    "    that agent and let the loop sequence it.\n"
    "  Default to agent whenever the request is not purely conversation. When\n"
    "  in doubt between chat, dispatch, and agent, choose agent -- over-\n"
    "  delegating is safer than under-delegating. Use dispatch ONLY when the\n"
    "  target is a concrete identifier; if any arg would be vague, use agent.\n"
    "\n"
    "GROUNDING (no fabrication): when answering needs information not already\n"
    "in this conversation -- anything external or current the agent would look\n"
    "up rather than already know -- classify it agent so the agent FETCHES it\n"
    "with the matching tool. Never invent facts, figures, or sources in this\n"
    "JSON. For intent=chat, emit a brief natural reply; if you cannot produce\n"
    "one, still emit intent=chat and the pipeline will generate the reply.\n"
    "The agent chooses the tool by purpose, not by keyword. Never address the\n"
    "operator by a personal name they did not give; use no name rather than a\n"
    "guessed one.\n"
    "\n"
    "LANGUAGE: write refined_text, intended_outcome, and reply in ENGLISH\n"
    "by default. Use another language ONLY when the operator's own message\n"
    "is clearly written in that language -- then keep every human-readable\n"
    "value in that ONE language. Never drift to a language the operator did\n"
    "not use. JSON keys + verb/tool names stay as-is (identifiers).\n"
)


def _salvage_refine_dispatch(content: str) -> dict | None:
    """Recover a deterministic one-verb dispatch when refine emits PROSE.

    A small refine model (qwen3.5:4b) occasionally NARRATES instead of emitting
    the JSON envelope -- even with format=json -- when the request invites
 reasoning ("Open discord on my desktop" -> the model
    replied 'To open Discord on your desktop, I will launch_app(Discord PTB)'
    as prose, json.loads failed at char 0, the turn DROPPED to the research
    swarm -> 477s, 8 agents, fabrication, NO launch). Rather than discard the
    obvious action, salvage it. Fully generative: it only matches verb NAMES
    from the live fast-path catalog (no hardcoded app/English list).

    Returns a {"intent":"dispatch","tool":...,"args":...} dict or None.
    """
    if not content:
        return None
    # 1) An embedded JSON object inside the prose ("...narration... {json}").
    m = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if m:
        try:
            obj = _loads_lenient(m.group(0))
            if isinstance(obj, dict) and obj.get("intent"):
                return obj
        except Exception:
            pass
    # 2) A verb CALL in the prose: VERB(args) where VERB is a real fast-path
    #    verb. Longest-name-first so e.g. launch_verified beats launch_app.
    verbs = sorted(_FASTPATH_VERBS, key=len, reverse=True)
    if not verbs:
        return None
    alt = "|".join(re.escape(v) for v in verbs)
    call = re.search(r"(?<![A-Za-z0-9_])(" + alt + r")\s*\(\s*([^)]*)\)", content)
    if not call:
        return None
    tool = call.group(1)
    inner = (call.group(2) or "").strip()
    args: dict = {}
    # key=value pairs first (name="X", url='Y', every=5m, prompt=...).
    for km in re.finditer(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^,]+)", inner):
        k = km.group(1).strip()
        v = km.group(2).strip().strip("\"'").strip()
        if k and v:
            args[k] = v
    if not args and inner:
        # A bare positional value -> the verb's primary arg (url for open_url,
        # else name -- the launch/window verbs all key on the target name).
        val = inner.strip().strip("\"'").strip()
        if val:
            args["url" if tool == "open_url" else "name"] = val
    if not args:
        return None
    return {"intent": "dispatch", "tool": tool, "args": args, "_salvaged": True}


async def refine_intent(user_text: str,
                        history: list = None,
                        on_token: Optional[Callable[[str, bool], Any]] = None) -> Optional[dict]:
    """Quick-refine pass. Returns the parsed plan dict or None on
    bypass / error (caller falls through to the legacy router path).

    Bypass: trivial inputs (greetings, single-word commands) skip
    refine entirely. The existing classify_intent router handles
    them with its own chat-reply path in one LLM call -- adding a
    refine pass on top would be wasted latency. Local-compute-aware
 per operator directive 'fast and efficient for pure
    local compute'."""
    if not REFINE_ENABLED or not user_text or not user_text.strip():
        return None
    # No length-based trivial bypass: it mis-classed short ACTION
    # commands ("Check system status", "Take screenshot", "Open chrome")
    # as chat -> the chat short-circuit then faked a reply without
    # running the tool. The capable refine model
    # below classifies every non-empty query instead -- greetings still
    # land as intent=chat, real actions as intent=agent.
    # Pull the registered agents into the prompt so the model picks
    # one that actually exists.
    agents_summary = "\n".join(
        f"  - {n}: role={c.get('role','?')} "
        f"strengths={','.join(c.get('strengths') or [])[:80]}"
        for n, c in _AGENT_REGISTRY.items()
    )
    # Thinking is disabled at the API level (enable_thinking=False on the
    # /v1 call below) rather than via the `/no_think` token -- operator test
    # proved the qwen3 micros ignore /no_think (modelfile
    # thinking-mode override) and dump the answer into message.reasoning,
    # leaving message.content EMPTY.
    static_parts = [
        _REFINE_SYSTEM_LITE,
        _env_grounding_static(),
        f"Registered sub-agents:\n{agents_summary}"
    ]
    if _OS_CONTROL_VERBS_RENDERED:
        static_parts.append(
            "Action-verb catalog (for intent=dispatch -- map a single\n"
            "concrete app / window / URL action, OR a recurring 'every N' /\n"
            "'each day' standing request, to exactly ONE of these):\n"
            + _OS_CONTROL_VERBS_RENDERED
        )
    if _VERB_CATALOG:
        static_parts.append(
            "VALID verb names -- for `hint_tools` (and `tool`) use ONLY "
            "these EXACT names; NEVER invent a plausible-sounding name (no "
            "'journalctl_tail', 'flight_search', 'system_service_status'). "
            "If none fits, leave hint_tools empty:\n"
            + ", ".join(sorted(_VERB_CATALOG.keys()))
        )
    system = "\n\n".join(static_parts) + "\n\n" + _env_grounding_dynamic()
    msgs = [{"role": "system", "content": system}]
    # Last 2 turns of history, tightly capped -- the OWUI pipe already
    # enhances the prompt before it reaches us, so re-feeding long
    # history here just slows the CPU refine (
    # refine hit 13-45s on a ~1646-char input). Keep it lean.
    if history:
        for h in history[-2:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                msgs.append({"role": h["role"],
                             "content": mios_tokenize.truncate_to_tokens(
                                 str(h.get("content", "")), 250)})  # WS-A5 seam (was [:200])
    # Cap the refine input to the TAIL. OWUI's RAG ("Searching Knowledge")
    # rewrites the user turn as "<context...>\n\nQuery: <actual question>"
    # - the real question is at the END (operator test showed a
    # 6207-char user_text for a one-line question; CPU refine scales with
    # length). Keep the last 1500 chars so the question + nearby context
    # survive while latency stays bounded.
    # NATIVE structured outputs (WS-H1): constrain refine to a strict
    # json_schema so the envelope is schema-VALID by construction -- the decoder
    # cannot emit a missing/mistyped/out-of-enum field, killing the recurring
    # parse_fail/_loads_lenient/_salvage tiers and letting the prompt shed its
    # JSON-shape prose. Copies the PROVEN _route_domain pattern on the SAME :11450
    # llama.cpp lane: json_schema + chat_template_kwargs.enable_thinking=False
    # (llama.cpp #20345 silently DROPS the grammar when thinking is on -- the old
    # "NO response_format forces reasoning" note was the qwen3:1.7b era WITHOUT the
    # thinking-off fix). Schema validated live on :11450/granite4.1:8b
    # (200 + 17-key JSON; args additionalProperties:true accepted by the GBNF
    # compiler). Gated MIOS_REFINE_STRUCTURED (default on); ANY backend/refusal/
    # parse failure still degrades to the lenient path below (fail-open).
    _refine_structured = os.environ.get(
        "MIOS_REFINE_STRUCTURED", "true").strip().lower() not in {"0", "false", "no", "off"}
    _refine_stream_structured = os.environ.get(
        "MIOS_REFINE_STREAM_STRUCTURED", "true").strip().lower() not in {"0", "false", "no", "off"}
    if on_token and not _refine_stream_structured:
        _refine_structured = False

    
    _u_content = user_text[-1500:]
    if not _refine_structured and not on_token:
        _u_content += " /no_think"
    msgs.append({"role": "user", "content": _u_content})
    
    payload = {
        "model": REFINE_MODEL,
        "messages": msgs,
        "temperature": 0.0,
        "max_tokens": REFINE_MAX_TOKENS,
        "stream": bool(on_token),
    }
    if _refine_structured:
        _rv = sorted(_VERB_CATALOG.keys())
        payload["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "mios_refine", "strict": True, "schema": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "intent": {"type": "string",
                               "enum": ["chat", "dispatch", "agent", "multi_task"]},
                    "refined_text": {"type": "string"},
                    "news": {"type": "boolean"},
                    "web": {"type": "boolean"},
                    "local_state": {"type": "boolean"},
                    "needs_location": {"type": "boolean"},
                    "browser_action": {"type": "boolean"},
                    "domain_type": {"type": ["string", "null"]},
                    "state_scope": {"type": ["string", "null"]},
                    "inventory_filter": {"type": ["string", "null"]},
                    "intended_outcome": {"type": ["string", "null"]},
                    "target_agent": {"type": ["string", "null"]},
                    "hint_tools": {"type": "array",
                                   "items": {"type": "string", "enum": _rv}},
                    "tool": {"type": ["string", "null"], "enum": _rv + [None]},
                    "args": {"type": ["object", "null"], "additionalProperties": True},
                    "reply": {"type": ["string", "null"]},
                    "tasks": {"type": ["array", "null"], "items": {
                        "type": "object", "additionalProperties": False,
                        "properties": {
                            "title": {"type": "string"},
                            "refined_text": {"type": "string"},
                            "web": {"type": "boolean"},
                            "local_state": {"type": "boolean"}},
                        "required": ["title", "refined_text", "web", "local_state"]}}},
                "required": ["intent", "refined_text", "news", "web", "local_state",
                             "needs_location", "browser_action", "domain_type",
                             "state_scope", "inventory_filter", "intended_outcome",
                             "target_agent", "hint_tools", "tool", "args", "reply",
                             "tasks"]}}}
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    url = f"{REFINE_ENDPOINT}/v1/chat/completions"
    t0 = time.time()
    # RETRY once on timeout/transport error : the first
    # call after a VRAM eviction is a COLD model load and a loaded dGPU can push
    # a single attempt past the deadline -> returning None drops the WHOLE turn
    # to the council. That's what made "Focus Forza" hit the fast-path while
    # "Focus discord" 6 min later fell to the council narrating "couldn't locate
    # Discord" -- NOT a per-app difference (warm, refine maps discord/steam/
    # slack/chrome to focus_window identically to forza), just a transient
    # refine miss. The retry runs warm (the failed attempt left the model
    # resident) so a clear OS-action routes to dispatch consistently for EVERY
    # app. Model-decides, no hardcoded verb/app list. Tunable MIOS_REFINE_ATTEMPTS.
    async def _call_on_token(token_val: str, is_re: bool):
        if on_token:
            try:
                if inspect.iscoroutinefunction(on_token):
                    await on_token(token_val, is_re)
                else:
                    on_token(token_val, is_re)
            except Exception as _cb_err:
                log.warning("Error in on_token: %s", _cb_err)

    body = None
    for _attempt in range(REFINE_ATTEMPTS):
        try:
            if on_token:
                async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
                    async with s.stream("POST", url, json=payload, headers={"Content-Type": "application/json"}) as r:
                        if r.status_code != 200:
                            err_txt = await r.aread()
                            log.warning("refine stream: backend %s in %.1fs: %s", r.status_code, time.time() - t0, err_txt[:200])
                            return None
                        content_chunks = []
                        in_think = False
                        buffer = ""
                        async for chunk in r.aiter_text():
                            buffer += chunk
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if not line:
                                    continue
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str == "[DONE]":
                                        continue
                                    try:
                                        data = json.loads(data_str)
                                        choices = data.get("choices") or []
                                        if not choices:
                                            continue
                                        delta = choices[0].get("delta") or {}
                                        
                                        r_val = delta.get("reasoning_content") or delta.get("reasoning")
                                        if r_val:
                                            await _call_on_token(r_val, True)
                                            continue
                                            
                                        c_val = delta.get("content") or ""
                                        if c_val:
                                            temp = c_val
                                            if "<think>" in temp:
                                                in_think = True
                                                parts = temp.split("<think>", 1)
                                                if parts[0]:
                                                    await _call_on_token(parts[0], False)
                                                if parts[1]:
                                                    await _call_on_token(parts[1], True)
                                                continue
                                            if "</think>" in temp:
                                                in_think = False
                                                parts = temp.split("</think>", 1)
                                                if parts[0]:
                                                    await _call_on_token(parts[0], True)
                                                if parts[1]:
                                                    content_chunks.append(parts[1])
                                                    await _call_on_token(parts[1], False)
                                                continue
                                                
                                            if in_think:
                                                await _call_on_token(c_val, True)
                                            else:
                                                content_chunks.append(c_val)
                                                await _call_on_token(c_val, False)
                                    except Exception as e:
                                        pass
                        full_content = "".join(content_chunks)
                        body = {
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": full_content
                                }
                            }]
                        }
                        break
            else:
                async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
                    r = await s.post(url, json=payload,
                                     headers={"Content-Type": "application/json"})
                    if r.status_code != 200:
                        log.warning("refine: backend %s in %.1fs: %s", r.status_code, time.time() - t0, r.text[:200])
                        return None
                    body = r.json()
                    break
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            log.warning("refine: timeout/http error after %.1fs (attempt %d/%d): %s",
                        time.time() - t0, _attempt + 1, REFINE_ATTEMPTS, e)
            if _attempt + 1 >= REFINE_ATTEMPTS:
                return None
            # (load-361 incident): under host pressure a retry
            # just stalls the turn AGAIN (the 2x-long refine that idled the dGPU
            # while the CPU thrashed) -> degrade-open NOW (proceed without refine)
            # instead of retrying when the box is already over the admission
            # ceiling. Warm/healthy hosts keep the cold-load retry benefit.
            if _over_global_ceiling():
                log.warning("refine: host over ceiling -> skip retry, degrade-open")
                return None
            continue
        except Exception as e:
            log.warning("refine unexpected error: %s", e)
            return None
    if body is None:
        return None
    elapsed = time.time() - t0
    # OpenAI /v1 choices[] shape (MiOS is /v1-only). The streaming path above
    # already synthesises this same {choices:[{message:{content}}]} envelope.
    choices = body.get("choices") or []
    msg = (choices[0].get("message") if choices else {}) or {}
    content = (msg.get("content") or "").strip()
    if not content:
        log.warning("refine: %.1fs empty_content", elapsed)
        return None
    # qwen3-style reasoning models sometimes wrap output in
    # <think>...</think> blocks before the JSON. Strip them so
    # the JSON parser sees just the structured plan.
    content = re.sub(r"<think>.*?</think>\s*", "", content,
                     flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"^\s*```(?:json)?\s*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    try:
        parsed = _loads_lenient(content)
    except json.JSONDecodeError as e:
        # 1) STRUCTURAL repair FIRST : the common failure is
        # near-JSON with ONE bad token (empty value / trailing comma / comment /
        # truncated tail), NOT prose. _loads_lenient recovers the whole plan so a
        # flawless intent/refined_text/news classification is not thrown away over
        # one malformed field (which then degraded into the "worldwide trends
        # today" junk query + punt). Only accept a real plan (has an intent).
        parsed = _loads_lenient(content)
        if isinstance(parsed, dict) and parsed.get("intent"):
            log.warning("refine: %.1fs parse_fail REPAIRED (%s) -> intent=%s",
                        elapsed, e.msg, parsed.get("intent"))
        else:
            # 2) The model NARRATED instead of emitting JSON. Salvage an obvious
            # one-verb dispatch from the prose rather than dropping the turn to the
            # research swarm ("Open discord" -> 477s fan-out).
            parsed = _salvage_refine_dispatch(content)
            if parsed is not None:
                log.warning(
                    "refine: %.1fs parse_fail SALVAGED prose -> dispatch %s args=%s",
                    elapsed, parsed.get("tool"), parsed.get("args"))
            else:
                log.warning("refine: %.1fs parse_fail: %s; preview=%r",
                            elapsed, e, content[:200])
                return None
    if not isinstance(parsed, dict):
        log.warning("refine: %.1fs not_dict type=%s",
                    elapsed, type(parsed).__name__)
        return None
    log.info("refine: %.1fs [%s] intent=%s domain=%s target=%s",
             elapsed, REFINE_MODEL, parsed.get("intent"),
             parsed.get("domain_type"), parsed.get("target_agent"))
    # Stash routing-metadata onto the envelope so downstream SSE
    # emit sites can surface "refine: 17.7s qwen3:1.7b intent=agent"
    # instead of the bare "refine" label.
    parsed["_elapsed_s"] = round(elapsed, 1)
    parsed["_model"] = REFINE_MODEL
    parsed["_endpoint"] = REFINE_ENDPOINT
    # Normalise the model-driven `news` flag to a strict bool (format=json
    # usually yields a real boolean; coerce common string truthy forms too).
    # Drives _web_research_enrich -> SearXNG news category. MODEL-classified,
    # NOT a Python keyword check (operator binding: no hardcoded keyword lists).
    _news = parsed.get("news")
    parsed["news"] = (_news is True) or (
        isinstance(_news, str) and _news.strip().lower() in {"true", "1", "yes"})
    # Strict-bool coercion for needs_location (drives the location-required guard:
    # ask for the city instead of fabricating one when none was forwarded).
    _nl = parsed.get("needs_location")
    parsed["needs_location"] = (_nl is True) or (
        isinstance(_nl, str) and _nl.strip().lower() in {"true", "1", "yes"})
    # Same strict-bool coercion for browser_action (drives the fire-both browser
    # hand-off: the swarm researches AND a pinned Hermes node drives the browser).
    _ba = parsed.get("browser_action")
    parsed["browser_action"] = (_ba is True) or (
        isinstance(_ba, str) and _ba.strip().lower() in {"true", "1", "yes"})
    # Validate hint_tools against the verb catalog (refine sometimes
    # HALLUCINATES a tool name -- "news_search", earlier "journalctl_tail"/"flight_search" --
    # which the native loop then injects RAW as a STRONG preference, nudging the model toward
    # a non-existent tool. Drop any hint that does not resolve to a real verb (alias-aware +
    # hyphen/underscore/plural fold, the same fold _build_dispatch_cmd uses). Generic closed-
    # vocabulary check -- NO hardcoded name, NO topic list; degrade-open (an empty hint_tools
    # just lets the model self-route, which is the design).
    _ht = parsed.get("hint_tools")
    if isinstance(_ht, list) and _ht and _VERB_CATALOG:
        _folded_keys = {v.replace("-", "_").rstrip("s") for v in _VERB_CATALOG}
        _kept, _dropped = [], []
        for _h in _ht:
            if not isinstance(_h, str) or not _h.strip():
                continue
            _hs = _h.strip()
            _fold = _hs.lower().replace("-", "_").rstrip("s")
            if (_resolve_verb_key(_hs) in _VERB_CATALOG
                    or _fold in _VERB_CATALOG or _fold in _folded_keys):
                _kept.append(_hs)
            else:
                _dropped.append(_hs)
        parsed["hint_tools"] = _kept
        if _dropped:
            log.info("refine: dropped %d hallucinated hint_tool(s): %s",
                     len(_dropped), _dropped)
    # Force browser_action for a URL + READ/browse intent :
    # "open <url> and quote/read/summarize" must hit the CDP browse path (real DOM
    # via mios-cdp-fetch), not the open_url fast-path that only launches. Also flip
    # intent->agent so the dispatch fast-path doesn't fire open_url first.
    if not parsed["browser_action"] and _BROWSER_ACTION_ALT:
        try:
            import re as _re_brd
            _utb = user_text or ""
            if _re_brd.search(r'https?://', _utb) and _re_brd.search(
                    r'\b(?:' + _BROWSER_ACTION_ALT + r')\b', _utb, _re_brd.I):
                parsed["browser_action"] = True
                if parsed.get("intent") in ("dispatch", "chat"):
                    parsed["intent"] = "agent"
        except Exception:
            pass
    # Explicit browser-LAUNCH overrides the model's browse/research mis-route
    # ("open the Wikipedia main page in epiphany" got
    # routed to web-research and the agent FABRICATED "successfully opened in
    # Epiphany" -- the narrate-instead-of-call lie). Deterministic guard: a
    # launch verb + a named browser/app as the trailing "in/with <X>" target +
    # a resolvable URL (explicit in the text, or the one the model already
    # resolved into `parsed`) -> force intent=dispatch open_url. open_url then
    # really launches (real success OR an honest failure), never a fabricated
    # confirmation. The <X> token is resolved to a flatpak downstream by
    # mios-open-url, so there is NO hardcoded browser list here; the trailing

    # local_state: the query is about THIS machine -> fire local READ tools +
    # SUPPRESS web research ("summarize recent activity" /
    # "check service status" got web-searched into garbage -- random .xlsx files
    # containing "mios", dictionary defs of "list", the "Next" fashion brand).
    _ls = parsed.get("local_state")
    parsed["local_state"] = (_ls is True) or (
        isinstance(_ls, str) and _ls.strip().lower() in {"true", "1", "yes"})
    # domain_type: internal | external | both (agentic
    # internal/external/both routing). Coerce + derive a default from existing
    # signals when omitted: local_state -> internal; else external (safe default --
    # a missing classification must not silently become a local-only answer).
    # "both" is honored only when the model ALSO emitted a multi_task split (the
    # concurrent-mixed-execution branch verifies the tasks before splitting).
    _dt = parsed.get("domain_type")
    _dt = _dt.strip().lower() if isinstance(_dt, str) else ""
    if _dt not in ("internal", "external", "both"):
        _dt = "internal" if parsed.get("local_state") else "external"
    # ADDITIVE HYBRID : a local_state turn that ALSO flags a
    # web/news knowledge gap is genuinely BOTH -- even without a multi_task split,
    # which the model routinely omits for "the specs of MY hardware". Promote to
    # 'both' off refine's OWN web flag (model-judged, no keyword list) so the
    # dispatcher skips the local-only fast-path and the native loop fires BOTH the
    # local read tools AND web_search. Pure-local (web=false) is unchanged.
    if parsed.get("local_state") and (parsed.get("web") or parsed.get("news")):
        _dt = "both"
    parsed["domain_type"] = _dt
    # Deterministic routing for two verbs gemma4 mis-selects (
    # tool battery: web_search punted to LOCAL data; "remember X" ran mios_apps and
    # didn't save). Keyword-triggered like the launch/browse pre-router; the model
    # still owns everything else.
    try:
        import re as _re_vr
        _utl = user_text or ""
        # web_search pre-route: a TRIGGER verb co-occurring with a WEB context, both
        # from SSOT [routing] lists. Empty lists -> skip (model self-routes). The
        # `then|and then` split below is a STRUCTURAL conjunction boundary, not a
        # topic keyword. NO hardcoded English routing keywords.
        if _WEB_SEARCH_TRIGGERS and _WEB_SEARCH_CONTEXTS:
            _wt = "|".join(_re_vr.escape(p) for p in _WEB_SEARCH_TRIGGERS)
            _wc = "|".join(_re_vr.escape(p) for p in _WEB_SEARCH_CONTEXTS)
            if _re_vr.search(rf'\b(?:{_wt})\b.{{0,40}}\b(?:{_wc})\b', _utl, _re_vr.I):
                parsed["web"] = True
                parsed["local_state"] = False
                if parsed.get("intent") == "chat":
                    parsed["intent"] = "agent"
        # remember pre-route: SSOT trigger phrases + live-catalog guard. Empty list
        # -> skip (model self-routes).
        if _REMEMBER_TRIGGERS and "remember" in (_VERB_CATALOG or {}):
            _rt = "|".join(_re_vr.escape(p) for p in _REMEMBER_TRIGGERS)
            _rm = _re_vr.match(rf'\s*(?:please\s+)?(?:{_rt})(?:\s+that)?\s+(.+)',
                               _utl, _re_vr.I)
            if _rm:
                _fact = _re_vr.split(r',?\s*\b(?:then|and then)\b', _rm.group(1),
                                     maxsplit=1)[0].strip().rstrip('.')
                if _fact:
                    parsed["intent"] = "dispatch"
                    parsed["tool"] = "remember"
                    parsed["args"] = {"fact": _fact}
    except Exception:
        pass
    # Chat-classify guard: a small refine model occasionally picks
    # intent=chat for an input that's CLEARLY actionable (literal
    # CLI verb, fully-qualified URL, `mios-*` shim invocation) and
    # fabricates a confirmation `reply` text. Force-promote to
    # dispatch when the user text is shaped like a command or URL.
    # Language-agnostic: keyed off path / scheme prefixes, NOT on
    # any natural-language tokens (operator binding).
    if parsed.get("intent") == "chat":
        _ut = (user_text or "").strip()
        _looks_actionable = (
            _ut.startswith(("mios-", "/", "./", "sudo ", "systemctl ",
                            "podman ", "docker ", "git ", "curl ",
                            "wsl.exe", "powershell.exe", "cmd.exe"))
            or "://" in _ut
        )
        if _looks_actionable:
            log.info(
                "refine: chat promoted to dispatch "
                "(text starts with verb/URL token)")
            parsed["intent"] = "dispatch"
            parsed.pop("reply", None)
    # multi_task sanity: collapse to `agent` if the model produced
    # the multi_task intent with <2 tasks. Avoids surfacing an empty
    # kanban queue when the model was over-eager.
    if parsed.get("intent") == "multi_task":
        tasks = parsed.get("tasks") or []
        if not isinstance(tasks, list) or len(tasks) < 2:
            log.info(
                "refine: multi_task degraded to agent (tasks=%s)",
                len(tasks) if isinstance(tasks, list) else "non-list",
            )
            parsed["intent"] = "agent"
            # Keep the MULTI-STEP signal: refine SAW multiple steps but did
            # not itemise them. The handler hands this to the planner to
            # decompose into a concurrent per-agent DAG.
            parsed["_multi_step"] = True
            parsed.pop("tasks", None)
    # Long-prompt guard (language-agnostic): a real intent=chat /
    # intent=dispatch input is short (greeting, single verb).
    # When the user_text is >100 chars but the refine model still
    # picked one of those shallow intents, it almost always missed
    # multi-step structure. Promote to `agent` so the worker (or
    # the planner DAG) decomposes properly. Operator-flagged trace:
    # 134-char "find all games; research ratings; launch highest"
    # was classified intent=dispatch with args="highest reviewed
    # game" and the launcher picked Ubisoft as nearest substring.
    _ut = (user_text or "").strip()
    # OS-control dispatch is EXEMPT from the length guard (operator
    # trace: "Open notepad"->council, "Focus Spotify"
    # ->web). A concrete window/app action is legitimately ONE step even
    # when OWUI's RAG/memory enhancement pads the surrounding turn past
    # 100 chars (it rewrites the turn as "<context...>\n\nQuery: <cmd>",
    # documented above) -- refine still reads the tail and correctly
    # emits dispatch+<os verb>, but this guard was then demoting it to
    # agent purely on the padded length, sending every OS command to the
    # council/swarm. The OS-control set is SSOT from mios.toml's
    # "Window / app launch" section (no hardcoded verb/app/keyword list);
    # a genuinely multi-step ask still lands as multi_task at the model,
    # and a vague non-OS dispatch is still caught below.
    _os_dispatch = (parsed.get("intent") == "dispatch"
                    and str(parsed.get("tool") or "").strip()
                    in _FASTPATH_VERBS)
    if (parsed.get("intent") in ("chat", "dispatch")
            and len(_ut) > REFINE_PROMOTE_CHARS
            and not _os_dispatch):
        log.info(
            "refine: %s promoted to agent (user_text=%d chars > %d)",
            parsed["intent"], len(_ut), REFINE_PROMOTE_CHARS)
        parsed["intent"] = "agent"
        parsed.pop("reply", None)
    # Arg-shape guard: a dispatch arg value of >3 words is almost
    # certainly a semantic descriptor (e.g. "highest reviewed
    # game", "any browser will do"), not a concrete identifier the
    # launcher can resolve. Promote to agent so the worker
    # disambiguates with tool calls. Language-agnostic: counts
    # whitespace-separated tokens.
    if parsed.get("intent") == "dispatch":
        # Fast-path verbs (OS-control + schedule) resolve multi-word args by
        # design (a window title; a research prompt), so they're exempt from
        # the wordy-arg demotion below.
        _is_os = str(parsed.get("tool") or "").strip() in _FASTPATH_VERBS
        _args = parsed.get("args") if isinstance(parsed.get("args"), dict) else {}
        _wordy = False
        for v in _args.values():
            if isinstance(v, str) and len(v.strip().split()) > REFINE_DISPATCH_ARG_MAX_WORDS:
                _wordy = True
                break
        # OS-control verbs (focus/close/move/launch) resolve a multi-word target
        # by substring/fuzzy match, so a wordy title ("FakeGame 6 for me on
        # my pc") is FINE -- do NOT demote them to the research council (operator
        # "focus FakeGame 6" went to the council + failed). Only
        # a wordy NON-OS dispatch is the vague descriptor the launcher can't take.
        if _wordy and not _is_os:
            log.info(
                "refine: dispatch promoted to agent "
                "(arg value contained a multi-word semantic phrase)")
            parsed["intent"] = "agent"
    # Deterministic OS-action pre-router (research-backed): override a misrouted
    # 'launch/open <app>' to dispatch+open_app so the weak refine micro can't
    # flip a concrete action to a research swarm (the bug where "launch epiphany"
    # fired mios_find/list_windows + fabricated success instead of launching).
    _det = _deterministic_action_route(user_text)
    if _det is not None and parsed.get("intent") != "dispatch":
        log.info("refine: deterministic OS-action override %s args=%s (was intent=%s)",
                 _det["tool"], _det["args"], parsed.get("intent"))
        parsed = _det
    # Cross-domain mis-dispatch guard ("open discord and send a
    # message to @someone" -> refine emitted open_url with a FABRICATED discord channel
    # URL + fake token instead of the agent orchestrating launch+send). If refine
    # picked a single dispatch verb that is NOT in the routed domain's SSOT verb-set,
    # the classification and the chosen tool disagree -> the dispatch + its args are
    # unreliable (commonly fabricated). Defer to the agent tool-loop (full surface).
    # Data-driven on [routing.domains]; no keyword/app/URL literals. Skips the
    # deterministic route (a clean "open X").
    if (parsed.get("intent") == "dispatch" and not parsed.get("_deterministic")
            and _ROUTING_ENABLE and _ROUTING_DOMAINS):
        _gdom = _routed_domain_var.get(None)
        if _gdom is None:
            try:
                _gdom = await _route_domain(user_text)
            except Exception:  # noqa: BLE001
                _gdom = None
        _gtool = str(parsed.get("tool") or "").strip()
        _gverbs = (set((_ROUTING_DOMAINS.get(_gdom) or {}).get("verbs") or [])
                   if _gdom else set())
        if _gdom and _gverbs and _gtool and _gtool not in _gverbs:
            log.info("refine: cross-domain mis-dispatch (tool=%s NOT in routed domain "
                     "%s) -> agent (anti-fabrication)", _gtool, _gdom)
            parsed["intent"] = "agent"
            parsed.pop("tool", None)
            parsed.pop("args", None)
            parsed.pop("reply", None)
            # Reset to the CLEAN user text + drop fabricated web hints so the
            # invented URL/args never leak into the agent prompt or web-enrich.
            parsed["refined_text"] = user_text
            parsed.pop("hint_tools", None)
            parsed["web"] = False
            parsed["news"] = False
    # Best-effort event row.
    _db_fire(_db_post(_db_create("event", {
        "source": "mios-agent-pipe",
        "kind": "refine",
        "severity": "info",
        "summary": str(parsed.get("intent", "?"))[:120],
        "payload": parsed,
    }, now_fields=("ts",))))
    return parsed


async def _critic_refine_agent(
    raw: str,
    user_text: str,
    refined: Optional[dict],
    session_id: Optional[str],
    *,
    client,
    target_endpoint: str,
    headers: dict,
    base_body: dict,
) -> str:
    """Critic->refiner for the HEAVY agent path (ref AIOS B.1 / OS-Copilot
    executor-critic-refiner). Run the DCI critic on the buffered agent
    answer; if it raises a high-confidence challenge/ask (a genuinely
    contested/complex resolution), re-invoke the backend ONCE with the
    critic's concern so the answer is revised, then return the revision.

    Fires AS NEEDED: short/simple answers (< CRITIC_REFINE_MIN_CHARS) and
    the mios-os-control dispatch fast path never reach here, so CPU
    usecases stay fast; GPU/heavy answers earn the loop. Bounded by
    CRITIC_REFINE_MAX; returns the ORIGINAL answer on any error or when
    the critic is satisfied (the common case)."""
    if not (CRITIC_REFINE_ENABLED and DCI_ENABLED):
        return raw
    if not raw or len(raw) < CRITIC_REFINE_MIN_CHARS:
        return raw
    envelope = {
        "intent": (refined or {}).get("intent", "agent"),
        "answer": raw[:4000],
        "user_text": (user_text or "")[:1000],
    }
    try:
        act = await dci_critic_pass(user_text, envelope, session_id=session_id)
    except Exception as e:
        log.warning("critic-refine: critic pass failed: %s", e)
        return raw
    if not act or not (
            act.get("act") in ("challenge", "ask")
            and float(act.get("confidence", 0.0)) >= DCI_FLOW_TRIGGER_CONF):
        return raw  # critic satisfied -> answer stands (common case)
    concern = str(act.get("content") or "").strip()[:600]
    if not concern:
        return raw
    refine_body = dict(base_body)
    refine_body["stream"] = False
    refine_body["messages"] = list(refine_body.get("messages") or []) + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content":
            f"A reviewer raised this concern about your answer: {concern}\n"
            f"Revise your answer to fully address it. Be correct and "
            f"concise; do not mention this review."},
    ]
    out = raw
    for _ in range(max(1, CRITIC_REFINE_MAX)):
        try:
            r = await client.post(
                f"{target_endpoint}/chat/completions",
                content=json.dumps(refine_body).encode("utf-8"),
                headers=headers,
            )
            if r.status_code != 200:
                break
            j = r.json()
            ch = j.get("choices") or []
            new = (str((ch[0].get("message") or {}).get("content") or "")
                   if ch else "")
            if new.strip():
                out = new
                _emit_session_event({
                    "source": "mios-agent-pipe",
                    "kind": "critic_refine",
                    "severity": "info",
                    "summary": (f"refined on {act.get('act')} "
                                f"conf={act.get('confidence')}"),
                    "payload": {"concern": concern[:200]},
                }, session_id)
                break
        except Exception as e:
            log.warning("critic-refine: re-invoke failed: %s", e)
            break
    return out
