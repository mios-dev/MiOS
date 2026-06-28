# AI-hint: Deliberative Collective Intelligence (DCI) subsystem extracted verbatim from server.py (refactor R6 wave). 14 typed epistemic acts (Habermas-rooted, arxiv 2603.11781) grouped into 6 families -> _DCI_ACTS/_DCI_ACT_NAMES/_DCI_ACT_SCHEMA; the Phase B.1 single-persona Challenger critic (dci_critic_pass, _DCI_CRITIC_SYSTEM); the Phase B.2 4-persona convergent flow (run_dci_flow + _dci_call_persona over Framer/Explorer/Challenger/Integrator personas built by _persona_prompt with _PERSONA_ALLOWED_ACTS); and the Phase B.3 conditional escalation (critic_then_maybe_flow: cheap critic -> heavy flow -> taint-on-dissent). Config (_STACK_MODEL/_LIGHT_BASE) imported from mios_config; the DB-event helpers (_db_post/_db_create/_db_fire) + outbound-auth stamper (_apply_outbound_auth) are dependency-INJECTED via configure() (one-way boundary -- mios_dci NEVER imports server, enforced by 38-drift-checks check 6). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff). The CRITIC_REFINE_* heavy-path executor-critic-refiner stays in server.py (uses _emit_session_event) and consumes dci_critic_pass re-imported from here.
# AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./test_mios_dci.py
# AI-functions: _persona_prompt, _dci_call_persona, run_dci_flow, critic_then_maybe_flow, dci_critic_pass, configure
"""Deliberative Collective Intelligence (DCI) vocab + critic + convergent flow.

Extracted verbatim from ``server.py``. Holds the DCI epistemic-act vocabulary +
JSON schema, the four persona system prompts, the single-persona B.1 critic
(``dci_critic_pass``), the 4-persona B.2 convergent flow (``run_dci_flow`` /
``_dci_call_persona``) and the B.3 conditional-escalation chain
(``critic_then_maybe_flow``). ``server.py`` re-imports every name under its
original alias so the module's public surface is byte-identical.

Config constants come from ``mios_config``; the server-side DB-event helpers and
the outbound-auth header stamper are injected via :func:`configure` (one-way
module boundary -- this module never imports ``server``).
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
from mios_config import _STACK_MODEL, _LIGHT_BASE, _toml_section

log = logging.getLogger("mios-agent-pipe")


# ── Dependency-injection seam ─────────────────────────────────────
# The DCI flow + critic write SurrealDB/pg event rows via server.py's
# _db_create/_db_post/_db_fire helpers and stamp outbound credentials
# via _apply_outbound_auth. server.py calls configure() with those
# functions AFTER they are defined (one-way boundary: this module never
# imports server). They stay None until then; every consumer is
# async/runtime so a standalone ``import mios_dci`` still succeeds.
_db_post = None
_db_create = None
_db_fire = None
_apply_outbound_auth = None


def configure(*, db_post=None, db_create=None, db_fire=None,
              apply_outbound_auth=None) -> None:
    """Inject the server.py runtime helpers the DCI flow/critic call back into."""
    global _db_post, _db_create, _db_fire, _apply_outbound_auth
    if db_post is not None:
        _db_post = db_post
    if db_create is not None:
        _db_create = db_create
    if db_fire is not None:
        _db_fire = db_fire
    if apply_outbound_auth is not None:
        _apply_outbound_auth = apply_outbound_auth


# ── Phase B.1 -- Deliberative Collective Intelligence (DCI) vocab ─
# 14 typed epistemic acts (Habermas-rooted, DCI paper arxiv
# 2603.11781). Replaces unstructured agent debate -- which the
# paper showed degrades vs isolated reasoning -- with grammatical
# typed acts grouped into 6 functional families. Each act is a
# first-class object the agent emits as structured JSON; the
# orchestrator (Phase B.2) deliberates by passing acts between
# personas, preserving tensions, and converging via DCI-CF.
#
# Phase B.1 scope (this commit): vocabulary + schema + a single-
# persona post-dispatch critic helper that writes an event row
# tagged kind=dci_act. NOT yet the 4-persona convergent flow --
# that's B.2. This gives Phase B.1 immediate operator-visible
# value (post-dispatch critic verdicts in the audit log) without
# the latency of running the full deliberation loop on every
# chat turn.

DCI_ENABLED = os.environ.get("MIOS_AGENT_PIPE_DCI_ENABLED",
                              "true").lower() not in {"false", "0", "no"}
DCI_MODEL = os.environ.get("MIOS_AGENT_PIPE_DCI_MODEL", _STACK_MODEL)  # = _STACK_MODEL (granite4.1:8b on :11450; gemma4:12b retired -> 404)
DCI_ENDPOINT = os.environ.get(
    "MIOS_AGENT_PIPE_DCI_ENDPOINT", _LIGHT_BASE,  # mios-llm-light (WS-0B: one owned port key)
).rstrip("/")
DCI_TIMEOUT_S = int(os.environ.get("MIOS_AGENT_PIPE_DCI_TIMEOUT_S", "20"))
DCI_MAX_TOKENS = int(os.environ.get("MIOS_AGENT_PIPE_DCI_MAX_TOKENS", "400"))

# The 14 acts organized by family. Each family corresponds to a
# distinct cognitive function in collective deliberation; missing
# a family in a multi-round flow is what the DCI paper identifies
# as the failure mode for unstructured debate ("sycophantic
# convergence", "groupthink", "fragmentation"). Kept identical to
# the paper so future B.2 / B.3 references stay grounded.
_DCI_ACTS: dict[str, dict] = {
    # Orienting: problem framing + scope.
    "frame":         {"family": "orienting",   "intent": "establish the problem definition"},
    "clarify":       {"family": "orienting",   "intent": "request or supply clarification"},
    "reframe":       {"family": "orienting",   "intent": "restate the problem with a shifted lens"},
    # Generative: expanding the option space.
    "propose":       {"family": "generative",  "intent": "offer a candidate solution / hypothesis"},
    "extend":        {"family": "generative",  "intent": "build on an existing proposal"},
    "spawn":         {"family": "generative",  "intent": "open a new line of inquiry"},
    # Critical: assumption testing + risk.
    "ask":           {"family": "critical",    "intent": "request evidence / probe an assumption"},
    "challenge":     {"family": "critical",    "intent": "contest a claim with a counter-argument"},
    # Integrative: synthesis + memory.
    "bridge":        {"family": "integrative", "intent": "connect two distinct ideas"},
    "synthesize":    {"family": "integrative", "intent": "merge disparate views into a coherent whole"},
    "recall":        {"family": "integrative", "intent": "surface prior context / decisions"},
    # Epistemic: belief state + confidence.
    "ground":        {"family": "epistemic",   "intent": "anchor a claim to verifiable evidence"},
    "update":        {"family": "epistemic",   "intent": "revise a prior belief in light of new info"},
    # Decisional: closure.
    "recommend":     {"family": "decisional",  "intent": "advance a specific action / decision"},
}

_DCI_ACT_NAMES = sorted(_DCI_ACTS.keys())

# JSON Schema for OpenAI structured-output constraint. The model
# MUST emit exactly this shape; anything else is a parse error.
# `confidence` is a 0.0-1.0 scalar so downstream can sort by it
# (e.g. Phase B.2's tension tracker promotes high-confidence
# CHALLENGE acts over low-confidence ones).
_DCI_ACT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "act":        {"type": "string", "enum": _DCI_ACT_NAMES,
                       "description": "Which of the 14 DCI epistemic acts you are emitting."},
        "content":    {"type": "string",
                       "description": "Free-form payload, 1-3 sentences. Mirror the chat language."},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0,
                       "description": "0.0 = highly uncertain; 1.0 = certain."},
        "targets":    {"type": "array", "items": {"type": "string"},
                       "description": "Optional list of prior act-ids this act addresses (Phase B.2 tension tracking)."},
    },
    "required": ["act", "content", "confidence"],
}


# Single-persona critic prompt for Phase B.1. The "Challenger"
# archetype focuses on the critical family (ask / challenge) +
# epistemic family (ground / update). Phase B.2 swaps in the
# full Framer / Explorer / Challenger / Integrator quartet.
_DCI_CRITIC_SYSTEM = (
    "You are a DCI Challenger agent (Deliberative Collective\n"
    "Intelligence, arxiv 2603.11781). Examine the operator's prompt\n"
    "and the agent's tool_result envelope. Emit ONE typed epistemic\n"
    "act as structured JSON. No free-form prose.\n"
    "\n"
    "Available acts (pick ONE):\n"
    + "\n".join(f"  - {a}: {info['intent']} (family: {info['family']})"
                for a, info in sorted(_DCI_ACTS.items())) +
    "\n\n"
    "Output schema (JSON ONLY):\n"
    '  {"act":"<one of the 14>",\n'
    '   "content":"<1-3 sentences in the chat language>",\n'
    '   "confidence":<0.0-1.0>,\n'
    '   "targets":[<optional act-ids you address>]}\n'
    "\n"
    "Heuristic for picking an act (Challenger persona):\n"
    "- If the agent's result looks WRONG / unjustified -> challenge\n"
    "  with a specific counter-argument.\n"
    "- If a step seems UNJUSTIFIED -> ask for evidence.\n"
    "- If the result is well-grounded -> ground (acknowledge +\n"
    "  cite the evidence).\n"
    "- If the result OBSOLETES a prior decision -> update.\n"
    "- If unsure -> ask (low confidence is fine; emit it as a\n"
    "  number).\n"
    "\n"
    "Write any text in ENGLISH by default (another language only if the\n"
    "user's own message is clearly in it). Output JSON ONLY -- no preamble,\n"
    "no markdown."
)


# ── Phase B.2 -- DCI-CF convergent flow (4 personas) ──────────────
# Replaces the single-persona B.1 Challenger with the full
# Deliberative Collective Intelligence convergent-flow algorithm:
# 4 archetypal delegates (Framer / Explorer / Challenger /
# Integrator) iterate a bounded loop against a shared workspace,
# always emitting a structured decision packet on exit (per
# arxiv 2603.11781 §3.4: the algorithm is guaranteed-bounded; even
# if convergence fails after R_max rounds, the Integrator emits a
# fallback packet with minority report + reopen triggers).
#
# All 4 personas role-play on the SAME local qwen2.5-coder:7b
# instance -- DCI paper §5.2 ablation showed single-model
# role-playing matches true multi-model diversity on most tasks,
# and the latency budget on a workstation rules out 4 distinct
# model instances anyway.
#
# B.2 scope (this commit): opt-in via env knob + on-demand
# /dci/deliberate endpoint. The flow does NOT fire automatically
# on every dispatch (the cheap B.1 Challenger covers that audit
# trail). Operator enables this when they want the heavy 4-persona
# deliberation -- e.g. for ambiguous, high-stakes, or
# operator-flagged turns.

# Opt-in gate for the heavy B.2 convergent flow, resolved from the [dci] SSOT
# (env override wins). DEFAULT-OFF for brick-safety: the 4-persona deliberation
# changes council behaviour -- it can TAINT a session on unresolved dissent -- so
# the operator flips [dci].flow_enabled on and live-validates. Same env-or-toml-or-
# default shape as the audit-chain gate; off keeps every dispatch on the cheap B.1
# critic audit trail only (which still records typed acts with their act_type).
DCI_FLOW_ENABLED = str(
    os.environ.get("MIOS_AGENT_PIPE_DCI_FLOW_ENABLED")
    or _toml_section("dci").get("flow_enabled", "false")
).strip().lower() not in {"false", "0", "no"}
DCI_FLOW_R_MAX = int(os.environ.get("MIOS_AGENT_PIPE_DCI_FLOW_R_MAX", "3"))
DCI_FLOW_TIMEOUT_S = int(os.environ.get(
    "MIOS_AGENT_PIPE_DCI_FLOW_TIMEOUT_S", "20"))

# Per-persona allowed-act sets. Hard constraint at validation
# time so single-model role-play doesn't collapse all four personas
# onto the same act (operator-observed first-run regression
# every persona emitted `ground` on an unambiguous
# success envelope -- correct individually but no deliberative
# value as a 4-persona flow). The Integrator retains the broadest
# set since its job is synthesis + decision.
_PERSONA_ALLOWED_ACTS: dict[str, set] = {
    "framer":     {"frame", "clarify", "reframe"},
    "explorer":   {"propose", "extend", "spawn"},
    "challenger": {"ask", "challenge"},
    "integrator": {"bridge", "synthesize", "recall",
                   "ground", "update", "recommend"},
}

# The dissent/objection acts -- exactly what the Challenger persona is allowed to
# emit. Derived from the persona-allowed SSOT so it tracks the vocabulary instead
# of restating a ("challenge","ask") literal at every site that decides "is this an
# objection?" -- the B.1 critic's B.2-escalation trigger, run_dci_flow's dissent
# extraction, and the warn-severity tag all read this ONE set.
_DCI_DISSENT_ACTS = frozenset(_PERSONA_ALLOWED_ACTS["challenger"])

# Per-persona system prompts. Each is a SPECIALIZATION of the
# generic critic prompt -- focuses the model on a specific act
# family while preserving access to the full 14-act vocabulary
# (the persona "constrains tendency, not capability" per DCI
# §4.1). The shared structural-output schema (_DCI_ACT_SCHEMA from
# B.1) is reused -- one schema, four prompts.

def _persona_prompt(role: str, role_desc: str, allowed_acts: set) -> str:
    """Build a hard-constraint persona prompt: MUST emit one of the
    listed acts, with each act's intent inline so the model picks
    the right one for its cognitive role."""
    allowed_lines = "\n".join(
        f"  - {a}: {_DCI_ACTS[a]['intent']}"
        for a in sorted(allowed_acts)
    )
    return (
        f"You are the DCI {role} persona (arxiv 2603.11781).\n"
        f"Your job: {role_desc}\n"
        "\n"
        "You MUST emit EXACTLY ONE act from this list. Any other\n"
        "act will be REJECTED and your contribution to this round\n"
        "will be lost:\n"
        f"{allowed_lines}\n"
        "\n"
        "Write the content in ENGLISH by default (another language only if\n"
        "the operator's own message is clearly in it). Output JSON ONLY shaped:\n"
        '  {"act":"<name>","content":"<1-3 sentences>",'
        '"confidence":<0-1>,"targets":[]}\n'
        "No preamble, no markdown, no commentary."
    )


_DCI_FRAMER_SYSTEM = _persona_prompt(
    "Framer",
    "establish the problem scope + clarify ambiguity. Read the "
    "operator's prompt + the envelope and decide what we're really "
    "deciding about.",
    _PERSONA_ALLOWED_ACTS["framer"],
)

_DCI_EXPLORER_SYSTEM = _persona_prompt(
    "Explorer",
    "expand the option space. What alternative paths or framings has "
    "the Framer missed? What is the second-best option here?",
    _PERSONA_ALLOWED_ACTS["explorer"],
)

_DCI_CHALLENGER_SYSTEM = _persona_prompt(
    "Challenger",
    "interrogate the proposals + the envelope. What evidence is "
    "thin? What assumption looks shaky? Pick the most consequential "
    "weak point and contest it -- or ask for evidence if it's "
    "ambiguous.",
    _PERSONA_ALLOWED_ACTS["challenger"],
)

_DCI_INTEGRATOR_SYSTEM = _persona_prompt(
    "Integrator",
    "synthesize the Framer / Explorer / Challenger contributions "
    "into a coherent next step. When their views diverge, EXPLICITLY "
    "name the tension in your `content` -- do NOT paper over "
    "disagreement. On the final round emit `recommend` to close.",
    _PERSONA_ALLOWED_ACTS["integrator"],
)

_DCI_PERSONAS = [
    ("framer",     _DCI_FRAMER_SYSTEM),
    ("explorer",   _DCI_EXPLORER_SYSTEM),
    ("challenger", _DCI_CHALLENGER_SYSTEM),
    ("integrator", _DCI_INTEGRATOR_SYSTEM),
]


async def _dci_call_persona(
    persona_name: str,
    system_prompt: str,
    user_text: str,
    workspace: dict,
) -> Optional[dict]:
    """One persona round: gives the persona the workspace state +
    asks for ONE typed act. Returns the parsed act dict (with
    persona name appended) or None on any error."""
    workspace_summary = json.dumps(workspace, indent=2, default=str)[:3000]
    user_msg = (
        f"OPERATOR PROMPT:\n{user_text[:1500]}\n\n"
        f"CURRENT WORKSPACE STATE:\n{workspace_summary}\n\n"
        f"You are the {persona_name}. Emit ONE typed epistemic act now:"
    )
    payload = {
        "model": DCI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": DCI_MAX_TOKENS,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=DCI_FLOW_TIMEOUT_S) as s:
            r = await s.post(
                f"{DCI_ENDPOINT}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("dci flow %s error: %s", persona_name, e)
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
    if not isinstance(parsed, dict):
        return None
    act = parsed.get("act")
    if act not in _DCI_ACTS:
        return None
    # Per-persona constraint: reject acts outside the persona's
    # allowed set. Forces deliberative diversity vs single-model
    # mode-collapse.
    allowed = _PERSONA_ALLOWED_ACTS.get(persona_name, set(_DCI_ACTS.keys()))
    if act not in allowed:
        log.info("dci %s emitted %s (not in family); rejecting",
                 persona_name, act)
        return None
    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.5
    parsed["persona"] = persona_name
    parsed["family"] = _DCI_ACTS[act]["family"]
    return parsed


async def run_dci_flow(
    user_text: str,
    envelope: dict,
    *,
    session_id: Optional[str] = None,
    r_max: Optional[int] = None,
) -> dict:
    """Run the DCI-CF convergent flow on (user_text, envelope).
    Returns a structured deliberation result:
      {decision: <Integrator's final recommend act>,
       rounds: [[act_per_persona, ...], ...],
       dissents: [<tension acts>],
       converged: bool}
    Always returns -- the bounded loop guarantees termination."""
    if r_max is None:
        r_max = DCI_FLOW_R_MAX
    # Initialize the shared workspace. DCI paper §3.2 prescribes 6
    # sections; we collapse to 5 for the v1 implementation.
    workspace: dict = {
        "user_prompt":  user_text[:600],
        "envelope":     {
            "tool":    (envelope.get("tool_call") or {}).get("function", {}).get("name"),
            "args":    (envelope.get("tool_call") or {}).get("function", {}).get("arguments"),
            "success": (envelope.get("tool_result") or {}).get("success"),
            "output":  ((envelope.get("tool_result") or {}).get("output") or "")[:500],
        },
        "frames":       [],    # Framer acts
        "proposals":    [],    # Explorer acts
        "challenges":   [],    # Challenger acts
        "syntheses":    [],    # Integrator non-final acts
    }
    rounds: list = []
    decision: Optional[dict] = None
    for r_idx in range(1, r_max + 1):
        round_acts = []
        for persona_name, system_prompt in _DCI_PERSONAS:
            act = await _dci_call_persona(
                persona_name, system_prompt, user_text, workspace,
            )
            if not act:
                continue
            round_acts.append(act)
            # Route the act into the workspace section based on family.
            family = act.get("family", "")
            if family == "orienting":
                workspace["frames"].append(act)
            elif family == "generative":
                workspace["proposals"].append(act)
            elif family == "critical":
                workspace["challenges"].append(act)
            elif family in ("integrative", "epistemic"):
                workspace["syntheses"].append(act)
            elif family == "decisional":
                # Final-form recommend -- capture as the decision.
                decision = act
            # Per-act event (reuse B.1's tagging).
            severity = "warn" if act["act"] in _DCI_DISSENT_ACTS and act["confidence"] >= DCI_FLOW_TRIGGER_CONF else "info"
            # act_type is a first-class event column (T-028) so dissent/act queries
            # are an indexed scan, not a JSONB extract; the act stays in the payload
            # too. Degrade-open: a pre-migration DB without the column drops it (the
            # pg mirror filters to live columns) and the event still logs.
            _db_fire(_db_post(_db_create("event", {
                "source": "mios-agent-pipe",
                "kind": "dci_act",
                "severity": severity,
                "summary": f"r{r_idx}/{persona_name}/{act['act']} ({act['confidence']:.2f})",
                "act_type": act["act"],
                "payload": {
                    "round": r_idx,
                    "persona": persona_name,
                    "act": act["act"],
                    "family": act["family"],
                    "confidence": act["confidence"],
                    "content": (act.get("content") or "")[:500],
                    "targets": act.get("targets") or [],
                    "session": session_id,
                },
            }, now_fields=("ts",))))
        rounds.append(round_acts)
        # Early-exit if the Integrator emitted a recommend.
        if decision is not None:
            break
    # If no recommend was emitted, force one last Integrator round.
    if decision is None:
        forced = await _dci_call_persona(
            "integrator",
            _DCI_INTEGRATOR_SYSTEM + (
                "\n\nIMPORTANT: This is the FINAL round. You MUST "
                "emit `recommend` as your act -- not `synthesize`, "
                "not `bridge`. The workspace has reached R_max; "
                "the deliberation MUST close with a decision."
            ),
            user_text, workspace,
        )
        if forced and forced.get("act") == "recommend":
            decision = forced
    converged = decision is not None
    # Dissent extraction: high-confidence challenges/asks that
    # were never resolved by a subsequent recommend/synthesize.
    # Cutoff is the single SSOT dissent-confidence knob
    # (DCI_FLOW_TRIGGER_CONF) -- the same threshold that auto-fires
    # the heavy flow, so "what counts as dissent" and "what
    # escalates" stay one tunable.
    dissents = [
        a for a in workspace["challenges"]
        if a.get("confidence", 0.0) >= DCI_FLOW_TRIGGER_CONF
    ]
    for d in dissents:
        # Awaited (not fire-and-forget) so downstream consumers
        # querying right after run_dci_flow returns see the rows.
        await _db_post(_db_create("event", {
            "source": "mios-agent-pipe",
            "kind": "dissent",
            "severity": "warn",
            "summary": f"unresolved {d['act']} ({d['confidence']:.2f})",
            "act_type": d["act"],
            "payload": {
                "persona": d.get("persona"),
                "content": (d.get("content") or "")[:500],
                "session": session_id,
            },
        }, now_fields=("ts",)))
    # Final decision packet -- always returned, even on
    # convergence failure (fallback uses the most-recent synthesis
    # if Integrator couldn't be coerced into a recommend).
    if decision is None and workspace["syntheses"]:
        decision = dict(workspace["syntheses"][-1])
        decision["fallback"] = True
    return {
        "decision": decision,
        "rounds": rounds,
        "dissents": dissents,
        "converged": converged,
        "rounds_used": len(rounds),
        "workspace": {
            "frames":     len(workspace["frames"]),
            "proposals":  len(workspace["proposals"]),
            "challenges": len(workspace["challenges"]),
            "syntheses":  len(workspace["syntheses"]),
        },
    }


# Phase B.3 -- conditional B.2 trigger.
# When the cheap B.1 Challenger emits a HIGH-CONFIDENCE
# `challenge` or `ask` (>= DCI_FLOW_TRIGGER_CONF), automatically
# fire the heavy B.2 4-persona convergent flow. If the flow then
# surfaces unresolved dissent, write a tainted tool_call row so
# the operator's NEXT dispatch in the same session gets refused by
# the Semantic Firewall. The whole chain runs fire-and-forget so
# the operator's reply isn't delayed.
#
# Single SSOT dissent-confidence knob. Used for BOTH the
# auto-escalation trigger here AND the dissent-extraction /
# event-severity cutoffs in run_dci_flow + dci_critic_pass, so the
# "high-confidence challenge/ask" line is one tunable -- not three
# baked literals that could silently drift apart.
DCI_FLOW_TRIGGER_CONF = float(os.environ.get(
    "MIOS_AGENT_PIPE_DCI_FLOW_TRIGGER_CONF", "0.7"))


async def critic_then_maybe_flow(
    user_text: str,
    envelope: dict,
    *,
    session_id: Optional[str] = None,
) -> None:
    """Chain B.1 critic -> conditional B.2 flow. Fire-and-forget
    via _db_fire so the dispatch reply isn't delayed.

    Phase B.3 flow:
      1. Run dci_critic_pass (single-persona Challenger).
      2. If the act is in (challenge, ask) AND confidence is high,
         escalate to run_dci_flow (4 personas, bounded loop).
      3. If the flow surfaces unresolved dissent, write a tainted
         tool_call row keyed to the session so any subsequent
         high-privilege verb in this session gets firewalled.
    """
    if not (DCI_ENABLED or DCI_FLOW_ENABLED):
        return
    # Stage 1: B.1 critic.
    act = await dci_critic_pass(user_text, envelope, session_id=session_id)
    if not act:
        return
    # Conditional escalation to B.2 -- GATED on DCI_FLOW_ENABLED so the heavy
    # 4-persona deliberation (and its taint-on-dissent side effect) is operator
    # opt-in. Default-off runs only the cheap B.1 critic above; flipping
    # [dci].flow_enabled on makes a high-confidence Challenger objection escalate
    # to the full convergent flow. The objection set is the persona-allowed SSOT
    # (_DCI_DISSENT_ACTS), not a restated ("challenge","ask") literal.
    if (DCI_FLOW_ENABLED
            and act.get("act") in _DCI_DISSENT_ACTS
            and act.get("confidence", 0.0) >= DCI_FLOW_TRIGGER_CONF):
        # Sentinel raised; fire the B.2 jury. Cap rounds at 2 for
        # the auto-trigger path (operator can still hit /dci/
        # deliberate manually for the full R_max=3 budget).
        result = await run_dci_flow(
            user_text, envelope,
            session_id=session_id, r_max=2,
        )
        # If the flow surfaced unresolved dissent, write a tainted
        # tool_call row so the Semantic Firewall blocks subsequent
        # high-privilege verbs in this session.
        #
        # NB: this write is AWAITED (not fire-and-forget). The
        # firewall pre-check on the operator's NEXT dispatch needs
        # to see this row -- if we fire-and-forget it, a sub-second
        # follow-up dispatch from the operator could land BEFORE
        # the write completes and slip past the firewall (operator-
        # observed race the dissent row didn't show up
        # in the SurrealDB readback because the loop returned before
        # the pending writes settled).
        if result.get("dissents") and session_id:
            taint_row = {
                "tool": "dci_dissent",
                "args": {
                    "dissent_count": len(result["dissents"]),
                    "trigger_act": act["act"],
                    "trigger_conf": act["confidence"],
                },
                "result_preview": (
                    f"DCI flow surfaced {len(result['dissents'])} "
                    f"unresolved dissent(s) -- session tainted"
                ),
                "success": False,
                "latency_ms": 0,
                "tainted": True,
                "taint_reason": (
                    f"dci_dissent:{len(result['dissents'])}_"
                    f"unresolved_after_r{result.get('rounds_used',0)}"
                ),
            }
            await _db_post(
                _db_create("tool_call", taint_row, now_fields=("ts",)).rstrip(";")
                + f", session = {session_id};"
            )


# Pydantic-free request shape for /dci/deliberate -- accept raw
# JSON so the operator can curl-test on the fly without writing a
# client.

async def dci_critic_pass(
    user_text: str,
    envelope: dict,
    *,
    session_id: Optional[str] = None,
) -> Optional[dict]:
    """Post-dispatch critic: invokes the DCI Challenger persona on
    the (user_text, envelope) pair and emits ONE typed epistemic
    act. Returns the parsed act dict, or None on any error.

    Fire-and-forget at the caller's discretion -- the chat reply is
    already rendered by the time this runs. Event row
    written automatically (kind=dci_act, source=mios-agent-pipe).
    """
    if not DCI_ENABLED or not user_text:
        return None
    # Compact envelope for the critic prompt -- keep latency low
    # by passing just the structured tool_call + tool_result, not
    # the full rendered <details> block.
    compact = {
        "tool":       (envelope.get("tool_call") or {}).get("function", {}).get("name"),
        "args":       (envelope.get("tool_call") or {}).get("function", {}).get("arguments"),
        "success":    (envelope.get("tool_result") or {}).get("success"),
        "output":    ((envelope.get("tool_result") or {}).get("output") or "")[:600],
        "stderr":    ((envelope.get("tool_result") or {}).get("stderr") or "")[:200],
        "exit_code":  (envelope.get("tool_result") or {}).get("exit_code"),
    }
    user_msg = (
        f"OPERATOR PROMPT:\n{user_text[:1500]}\n\n"
        f"AGENT ENVELOPE:\n{json.dumps(compact, indent=2, default=str)}\n\n"
        "Emit ONE typed epistemic act now:"
    )
    payload = {
        "model": DCI_MODEL,
        "messages": [
            {"role": "system", "content": _DCI_CRITIC_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": DCI_MAX_TOKENS,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=DCI_TIMEOUT_S) as s:
            # FED-G2 follow-up: attach the outbound credential for the critic endpoint
            # (shared key for a local lane / per-agent header for a remote one).
            _dci_hdrs = {"Content-Type": "application/json"}
            _apply_outbound_auth(_dci_hdrs, DCI_ENDPOINT)
            r = await s.post(
                f"{DCI_ENDPOINT}/v1/chat/completions",
                json=payload,
                headers=_dci_hdrs,
            )
            if r.status_code != 200:
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.warning("dci_critic unexpected error: %s", e)
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
    if not isinstance(parsed, dict):
        return None
    act = parsed.get("act")
    if act not in _DCI_ACTS:
        return None
    # Normalize + cap confidence.
    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.5
    family = _DCI_ACTS[act]["family"]
    # Event row -- act_type is the first-class column (T-028) so analytics is a
    # plain indexed scan (SELECT * FROM event WHERE act_type='challenge') instead
    # of a JSONB extract; the act + family stay in the payload for the full record.
    # Degrade-open: a DB without the column drops it (pg mirror filters to live
    # columns) and the event still logs.
    severity = "warn" if act in _DCI_DISSENT_ACTS and parsed["confidence"] >= DCI_FLOW_TRIGGER_CONF else "info"
    row = {
        "source":  "mios-agent-pipe",
        "kind":    "dci_act",
        "severity": severity,
        "summary": f"{family}/{act} ({parsed['confidence']:.2f})",
        "act_type": act,
        "payload": {
            "act":         act,
            "family":      family,
            "confidence":  parsed.get("confidence"),
            "content":     (parsed.get("content") or "")[:600],
            "targets":     parsed.get("targets") or [],
            "session":     session_id,
        },
    }
    _db_fire(_db_post(_db_create("event", row, now_fields=("ts",))))
    return parsed

