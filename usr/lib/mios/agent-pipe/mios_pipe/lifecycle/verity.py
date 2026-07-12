# AI-hint: Anti-fabrication POLISH/VERITY cluster extracted verbatim from server.py (refactor R6 wave). Three functions: _verity_factcheck (generate up to N SearXNG queries for a draft's UNCERTAIN specifics, run quick fresh searches, return a CONFIRM/DROP fact-check block -- gated to web turns), _strip_ungrounded_figures (deterministic output-side guard dropping sentences whose $-price/N%-percent figures are absent from the haystack polish saw, with a >half-the-figures fail-safe and abbreviation-protected sentence split), and polish_response (final sub-agent->user answer re-shaper grounded in tool-history + satisfaction verdicts + web sources + the verity fact-check; language-anchored to the operator's ORIGINAL words; appends the figure-guard, the ASK-TO-RUN proposal block, and the GLOBAL clarification block; fire-and-forget knowledge-store + SKILL.md mirror). Config-style constants (REFINE_*/POLISH_*/WEB_RESEARCH_SEARCH_TIMEOUT/_WEB_ENRICH_VERBS/ASK_CLARIFY_JUDGE_ENABLE/_POLISH_SYSTEM) and the server-side runtime helpers (_polish_post, _recent_tool_history, _format_tool_history, _recent_satisfaction_verdicts, _format_satisfaction_block, _store_knowledge, _write_skill_md_fire, _proposal_var) are dependency-INJECTED via configure() (one-way boundary -- mios_verity NEVER imports server). The generative clarification judge _clarify_question (the GLOBAL clarification block's gate) lives here too -- it reads only mios_config model-call scalars (ROUTER_MODEL/PLANNER_ENDPOINT/PLANNER_TIMEOUT_S) + _loads_lenient, so it moved home (no longer injected). _loads_lenient (mios_jsonsalvage) and _env_grounding (mios_grounding) are imported directly. server.py re-imports every name under its EXACT original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_grounding.py, ./test_mios_verity.py
# AI-functions: _verity_factcheck, _strip_ungrounded_figures, polish_response, _clarify_question, configure
"""Anti-fabrication POLISH/VERITY cluster (final-answer fact-check + figure guard).

Extracted verbatim from ``server.py``. Holds the final-pass VERITY fact-check
(``_verity_factcheck``), the deterministic ungrounded-figure output guard
(``_strip_ungrounded_figures``) and the sub-agent answer re-shaper
(``polish_response``). ``server.py`` re-imports every name under its original
alias so the module's public surface is byte-identical.

The model-call constants (REFINE_*/POLISH_*) and the server-side DB/format/store
helpers are injected via :func:`configure` (one-way module boundary -- this
module never imports ``server``); ``_loads_lenient`` and ``_env_grounding`` come
from sibling modules directly.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Optional

import httpx

from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_grounding import _env_grounding
from mios_config import (  # SSOT mios.toml reader + model-call scalars (sibling, pure)
    _toml_section, ROUTER_MODEL, PLANNER_ENDPOINT, PLANNER_TIMEOUT_S)

log = logging.getLogger("mios-agent-pipe")


# ── Dependency-injection seam ─────────────────────────────────────
# The verity/polish cluster reads several server.py module constants and calls
# back into server.py runtime helpers (DB reads, tool-history formatting,
# knowledge store, clarify judge, the proposal contextvar). server.py calls
# configure() with those AFTER every one is defined (one-way boundary: this
# module never imports server). They stay at their import-time defaults until
# then; every consumer is async/runtime so a standalone ``import mios_verity``
# still succeeds.
REFINE_TIMEOUT_S = int(os.environ.get("MIOS_REFINE_TIMEOUT_S", "30"))
REFINE_ENDPOINT = ""
REFINE_MODEL = ""
_WEB_ENRICH_VERBS: set = set()
WEB_RESEARCH_SEARCH_TIMEOUT = float(
    os.environ.get("MIOS_WEB_RESEARCH_SEARCH_TIMEOUT_S", "30"))
POLISH_ENABLED = False
_POLISH_SYSTEM = ""
POLISH_ENDPOINT = ""
POLISH_MODEL = ""
POLISH_MAX_TOKENS = 800
POLISH_TIMEOUT_S = 15
ASK_CLARIFY_JUDGE_ENABLE = False

# Sentence-split abbreviation exceptions for the figure-guard's script-neutral
# splitter (mios_verity._strip_ungrounded_figures -> _sents). SSOT-sourced from
# mios.toml [verity].sentence_abbreviations; the Latin set below is the documented
# vendor default (matches the shipped mios.toml value) so a standalone import still
# works when the file/section is absent (degrade-open). configure() can override.
_ABBR_DEFAULT = ("approx.", "Approx.", "e.g.", "i.e.", "vs.", "etc.", "U.S.",
                 "U.K.", "a.m.", "p.m.", "No.", "Inc.", "Co.", "Ltd.", "St.", "Mt.")


def _ssot_abbreviations() -> tuple:
    """Sentence-split abbreviation exceptions from mios.toml [verity], or the
    Latin default when the key/file is absent. Script-neutral splitter + this
    SSOT exception list = no baked word screen frozen in code."""
    try:
        _v = _toml_section("verity").get("sentence_abbreviations")
        if isinstance(_v, (list, tuple)) and _v:
            return tuple(str(x) for x in _v if str(x).strip())
    except Exception:  # noqa: BLE001 -- best-effort; fall to the Latin default
        pass
    return _ABBR_DEFAULT


_ABBR = _ssot_abbreviations()

_polish_post = None
_recent_tool_history = None
_format_tool_history = None
_recent_satisfaction_verdicts = None
_format_satisfaction_block = None
_store_knowledge = None
_write_skill_md_fire = None
_proposal_var = None


def configure(*, refine_timeout_s=None, refine_endpoint=None, refine_model=None,
              web_enrich_verbs=None, web_research_search_timeout=None,
              polish_enabled=None, polish_system=None, polish_endpoint=None,
              polish_model=None, polish_max_tokens=None, polish_timeout_s=None,
              ask_clarify_judge_enable=None, polish_post=None,
              recent_tool_history=None, format_tool_history=None,
              recent_satisfaction_verdicts=None, format_satisfaction_block=None,
              store_knowledge=None, write_skill_md_fire=None,
              proposal_var=None,
              abbreviations=None) -> None:
    """Inject the server.py constants + runtime helpers the verity/polish
    cluster reads and calls back into. Called once at import time, after every
    injected symbol is defined."""
    global REFINE_TIMEOUT_S, REFINE_ENDPOINT, REFINE_MODEL, _WEB_ENRICH_VERBS
    global WEB_RESEARCH_SEARCH_TIMEOUT, POLISH_ENABLED, _POLISH_SYSTEM
    global POLISH_ENDPOINT, POLISH_MODEL, POLISH_MAX_TOKENS, POLISH_TIMEOUT_S
    global ASK_CLARIFY_JUDGE_ENABLE
    global _polish_post, _recent_tool_history, _format_tool_history
    global _recent_satisfaction_verdicts, _format_satisfaction_block
    global _store_knowledge, _write_skill_md_fire
    global _proposal_var, _ABBR
    if refine_timeout_s is not None:
        REFINE_TIMEOUT_S = refine_timeout_s
    if refine_endpoint is not None:
        REFINE_ENDPOINT = refine_endpoint
    if refine_model is not None:
        REFINE_MODEL = refine_model
    if web_enrich_verbs is not None:
        _WEB_ENRICH_VERBS = web_enrich_verbs
    if web_research_search_timeout is not None:
        WEB_RESEARCH_SEARCH_TIMEOUT = web_research_search_timeout
    if polish_enabled is not None:
        POLISH_ENABLED = polish_enabled
    if polish_system is not None:
        _POLISH_SYSTEM = polish_system
    if polish_endpoint is not None:
        POLISH_ENDPOINT = polish_endpoint
    if polish_model is not None:
        POLISH_MODEL = polish_model
    if polish_max_tokens is not None:
        POLISH_MAX_TOKENS = polish_max_tokens
    if polish_timeout_s is not None:
        POLISH_TIMEOUT_S = polish_timeout_s
    if ask_clarify_judge_enable is not None:
        ASK_CLARIFY_JUDGE_ENABLE = ask_clarify_judge_enable
    if polish_post is not None:
        _polish_post = polish_post
    if recent_tool_history is not None:
        _recent_tool_history = recent_tool_history
    if format_tool_history is not None:
        _format_tool_history = format_tool_history
    if recent_satisfaction_verdicts is not None:
        _recent_satisfaction_verdicts = recent_satisfaction_verdicts
    if format_satisfaction_block is not None:
        _format_satisfaction_block = format_satisfaction_block
    if store_knowledge is not None:
        _store_knowledge = store_knowledge
    if write_skill_md_fire is not None:
        _write_skill_md_fire = write_skill_md_fire
    if proposal_var is not None:
        _proposal_var = proposal_var
    if abbreviations is not None:
        _ABBR = tuple(str(x) for x in abbreviations if str(x).strip())


async def _clarify_question(user_text: str, answer: str) -> str:
    """Generative judge (NO keywords -- operator "NOTHING HARDCODED"): is `answer`
    PRIMARILY asking the USER for information it NEEDS to proceed (a clarification /
    missing detail / a choice between options), vs a complete answer or an incidental/
    rhetorical question? If yes, return the SINGLE clearest question to put to the user;
    else ''. The caller gates on a '?' present (cheap structural pre-filter) so this runs
    rarely. Degrade -> '' (no prompt)."""
    if not (answer or "").strip():
        return ""
    sys = ("Given the USER's request and the ASSISTANT's reply, decide BY MEANING (never "
           "by keywords): does the reply FULLY address what the user asked, or is it "
           "BLOCKED -- unable to complete the request until the USER supplies a specific "
           "missing detail? Return the single question to put to the user ONLY if it is "
           "genuinely blocked and gave no usable result. If the reply addresses the "
           "request -- INCLUDING greetings, small talk, or a complete answer that merely "
           "ends with a polite or optional question -- return an empty string. Be "
           "CONSERVATIVE: when uncertain, return an empty string.")
    payload = {
        "model": ROUTER_MODEL,
        "messages": [{"role": "system", "content": sys},
                     {"role": "user", "content":
                      f"USER REQUEST: {(user_text or '')[:600]}\n\nASSISTANT REPLY: {answer[:1200]}"}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "clarify", "strict": True, "schema": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"], "additionalProperties": False}}},
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.0, "max_tokens": 80, "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=PLANNER_TIMEOUT_S) as s:
            r = await s.post(f"{PLANNER_ENDPOINT}/v1/chat/completions", json=payload,
                             headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            return ""
        content = ((r.json().get("choices") or [{}])[0].get("message", {})
                   .get("content") or "")
        return str((_loads_lenient(content) or {}).get("question") or "").strip()
    except Exception as e:  # noqa: BLE001 -- degrade-open (no clarification prompt)
        log.debug("clarify judge failed (-> none): %s", e)
        return ""


# Final-pass VERITY fact-check ("checks passes for final
# output can use web tools globally quickly fact check things for uncertainties --
# should be able to generate queries to investigate the results for verity").
VERITY_FACTCHECK = os.environ.get(
    "MIOS_VERITY_FACTCHECK", "true").lower() not in {"false", "0", "no"}
VERITY_FACTCHECK_MAX_Q = int(os.environ.get("MIOS_VERITY_FACTCHECK_MAX_Q", "2"))


async def _verity_factcheck(draft: str, user_q: str,
                            refined: Optional[dict]) -> str:
    """Generate up to N search queries for the UNCERTAIN specifics in a draft
    answer, run a QUICK SearXNG search on each, and return the fresh results so
    the final pass CONFIRMS or DROPS each claim -- turning the old "distrust
    embellishment -> punt" into "verify -> answer with what holds up". Gated to
    web turns (uncertainty = current/external facts); bounded + best-effort."""
    if not VERITY_FACTCHECK or not draft or not draft.strip():
        return ""
    hints = [str(t).lower().strip() for t in ((refined or {}).get("hint_tools") or [])]
    if not any(h in (_WEB_ENRICH_VERBS | {"open_url"}) for h in hints):
        return ""
    sys_p = ("You verify a draft answer. From the draft, pick up to "
             f"{VERITY_FACTCHECK_MAX_Q} SPECIFIC factual claims (named events / "
             "dates / numbers / releases) that are UNCERTAIN and worth a quick web "
             'check. Output JSON {"queries":["concrete search query", ...]} -- each '
             "a concrete keyword search query, NOT a question. Empty list if "
             "nothing needs checking.")
    queries: list = []
    try:
        async with httpx.AsyncClient(timeout=REFINE_TIMEOUT_S) as s:
            r = await s.post(f"{REFINE_ENDPOINT}/v1/chat/completions", json={
                "model": REFINE_MODEL, "stream": False,
                "temperature": 0.0, "max_tokens": 400,
                "messages": [
                    {"role": "system", "content": sys_p},
                    {"role": "user",
                     "content": f"Question: {user_q[:300]}\n\nDraft:\n{draft[:1500]} /no_think"}]},
                headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                _vm = ((r.json().get("choices") or [{}])[0]).get("message") or {}
                c = _vm.get("content") or _vm.get("reasoning_content") or ""
                c = re.sub(r"<think>.*?</think>\s*", "", c, flags=re.DOTALL | re.I)
                queries = [str(q).strip() for q in
                           (_loads_lenient(c or "{}").get("queries") or [])
                           if str(q).strip()][:VERITY_FACTCHECK_MAX_Q]
    except Exception as e:  # noqa: BLE001 -- best-effort
        log.debug("verity query-gen skipped: %s", e)
        return ""
    if not queries:
        return ""
    if isinstance(refined, dict):  # record steps for the emit log
        for q in queries:
            refined.setdefault("_verity_steps", []).append(
                {"emoji": "🔬", "label": "fact-check", "detail": q[:60]})

    async def _fc(q: str) -> tuple:
        try:
            p = await asyncio.create_subprocess_exec(
                "mios-web-search", "-n", "3", "--fanout", "1", q[:200],
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            o, _ = await asyncio.wait_for(
                p.communicate(), timeout=WEB_RESEARCH_SEARCH_TIMEOUT)
            d = _loads_lenient((o or b"{}").decode("utf-8", "replace") or "{}")
            hits = [f"  - {(x.get('title','') or '')[:70]} ({x.get('url','')}) "
                    f"{(x.get('content','') or '')[:160]}"
                    for x in (d.get("results") or [])[:3]]
            return q, hits
        except Exception:  # noqa: BLE001
            try: p.kill()
            except: pass
            return q, []

    results = await asyncio.gather(*[_fc(q) for q in queries])
    blocks = [f"CHECK: {q}\n" + "\n".join(hits) for q, hits in results if hits]
    if not blocks:
        return ""
    log.info("verity fact-check: %d quer(ies) for %.50r", len(blocks), user_q)
    return ("LIVE FACT-CHECK (fresh searches run THIS pass to verify the draft's "
            "specifics; CONFIRM claims these results support, DROP or soften "
            "claims they contradict or don't mention):\n\n" + "\n\n".join(blocks))


def _strip_ungrounded_figures(answer: str, haystack: str) -> str:
    """Drop sentences whose PRICE ($/C$/US$ + digits) or PERCENT (N%) figures are
    absent from the source material polish was given.

 The recurring 4b-polish failure ('FAILURE'): the final
    pass APPENDS invented specifics -- 'deals as low as $184 ... Skyscanner [3]'
    and 'morning departures ~2% cheaper [1]' -- with SCRAMBLED citations, even
    though _POLISH_SYSTEM forbids it. The prompt rule alone doesn't hold on the
    small model, and verity only checks the INPUT draft, never polish's OUTPUT.
    This is the deterministic output-side guard.

    The `haystack` is the FULL material polish saw -- the raw research AND the
    agents' own findings (+ web sources). So a figure is 'grounded' if ANY
    agent or source produced it; only figures polish INVENTED get stripped.
    This is why a general-knowledge numeric answer (agent says '~120 million
    rods') is safe: the number is in the agents' findings = in the haystack.

    Conservative by design: only $-prices and N%-percentages are policed (NOT
    durations / counts / dates / years); prices match by distinctive >=3-digit
    number presence; percentages must have a matching '<n>%' in the source;
    drops at the SENTENCE level within a line (markdown structure preserved);
    and a fail-safe leaves the answer untouched if it would strip more than half
    the figure-bearing sentences (a sign the grounding capture, not the model,
    is at fault)."""
    if not answer or not answer.strip():
        return answer
    hay = haystack or ""
    hay_nums = set(re.findall(r"\d+", hay.replace(",", "")))
    hay_low = hay.lower()
    if not hay_nums:
        return answer  # no numeric grounding to check against -> leave as-is
    # Digits are unicode-aware by default (\d matches any script's decimal digit);
    # the percent sign is accepted in ASCII '%' and fullwidth '％' (CJK) so the
    # numeric guard is script-neutral.
    fig_re = re.compile(
        r"(?:US|C|A|NZ|HK)?\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?\s?[%％]")

    def _ok(tok: str) -> bool:
        nums = re.findall(r"\d+", tok.replace(",", ""))
        if "%" in tok or "％" in tok:
            # percent: require a matching '<n>%' / '<n> percent' in the source,
            # not just the bare digit (which collides with years, versions, etc.)
            return any(re.search(rf"(?<!\d){n}\s?(?:%|％|percent)", hay_low)
                       for n in nums)
        # price: the exact number must be one the source actually produced
        return any(n in hay_nums for n in nums)

    # Abbreviation-protected, SCRIPT-NEUTRAL sentence split. Two boundary classes:
    #   (1) ASCII terminator [.!?] FOLLOWED BY whitespace -- the period is protected
    #       inside the SSOT abbreviation list (_ABBR, sourced from mios.toml [verity])
    #       so "approx." / "U.S." don't split off the grounded "$X USD)" fragment
    #       after them (observed live "C$586 (approx." dangling), then restored.
    #   (2) a unicode sentence terminator (。！？．؟।) -- CJK / Arabic / Devanagari
    #       scripts write WITHOUT a trailing space, so an ASCII-only `[.!?]\s+`
    #       splitter treated a whole multi-sentence CJK line as ONE sentence and
    #       dropped its grounded text wholesale when ANY clause carried an
    #       ungrounded figure. Splitting on these gives non-Latin answers the same
    #       per-sentence granularity Latin ones already had.
    def _sents(line: str) -> list:
        tmp = line
        for ab in _ABBR:
            tmp = tmp.replace(ab, ab[:-1] + "\x00")
        return [seg.replace("\x00", ".")
                for seg in re.split(r"(?<=[.!?])\s+|(?<=[。！？．؟।])", tmp)
                if seg]

    out_lines: list = []
    total = dropped = 0
    for line in answer.split("\n"):
        if not fig_re.search(line):
            out_lines.append(line)
            continue
        keep: list = []
        for s in _sents(line):
            figs = fig_re.findall(s)
            if figs:
                total += 1
                if all(not _ok(f) for f in figs):
                    dropped += 1
                    continue
            keep.append(s)
        out_lines.append(" ".join(keep).rstrip() if keep else None)
    if dropped == 0:
        return answer
    if total and dropped > total / 2:
        log.info("figure-guard: %d/%d ungrounded figure-sentences -> too many, "
                 "leaving answer (grounding capture suspect)", dropped, total)
        return answer
    rebuilt = re.sub(r"\n{3,}", "\n\n",
                     "\n".join(l for l in out_lines if l is not None)).strip()
    log.info("figure-guard: dropped %d ungrounded $/%% sentence(s)", dropped)
    # Never return an empty/whitespace-only rebuild (an all-whitespace string is truthy
    # and would slip past `rebuilt or answer`): fall back to the original answer.
    return rebuilt if rebuilt and rebuilt.strip() else answer


async def polish_response(raw_text: str,
                          refined: Optional[dict],
                          session_id: Optional[str] = None,
                          original_user_text: str = "",
                          persona_system: str = "",
                          agent_tools: Optional[list] = None,
                          max_tokens: Optional[int] = None) -> Optional[str]:
    """Polish a sub-agent's raw response into the final user-facing
    answer. Returns the polished string or None on error (caller
    keeps the raw answer).

    When session_id is supplied, the polish prompt receives the
    recent tool_call history as ground truth. The CRITICAL rule in
    _POLISH_SYSTEM tells the model to REWRITE the response when it
 contradicts the tool history (Operator-flagged
    'open nautilus' -> assistant claimed 'The move command failed
    because the destination directory wasn't writable' -- a
    completely fabricated unrelated error).

    `original_user_text` is the operator's ACTUAL last message and is
    the authoritative LANGUAGE anchor. refined_text is a rewrite the
    (all-English) refine prompt can translate to English -- keying
    polish's reply language off it made a Polish question come back in
 English / mixed. Polish answers in the
    language of the original message; refined_text feeds CONTENT only."""
    if not POLISH_ENABLED or not raw_text or not raw_text.strip():
        return None
    intended = (refined or {}).get("intended_outcome", "") or ""
    refined_q = (refined or {}).get("refined_text", "") or ""
    orig_q = (original_user_text or "").strip()
    # Language anchor = operator's own words; fall back to the rewrite.
    user_q = orig_q or refined_q
    tool_history = await _recent_tool_history(session_id)
    has_failed_tool = any(
        r.get("success") is False for r in tool_history
    )
    # Skip when intended is empty + raw is short + no failed tools.
    # If a tool FAILED, we ALWAYS polish so the response gets
    # ground-truth-checked even on short answers.
    if not intended and len(raw_text) < 200 and not has_failed_tool:
        log.info("polish: skipped (no intended_outcome + raw<200 chars + no failed tools)")
        return None
    system = _POLISH_SYSTEM + "\n" + _env_grounding() + (
        f"\nIntended outcome: {intended}\n" if intended else ""
    )
    # Persona application ("polish the stack's final
    # response WITH PERSONA APPLIED"). The OWUI pipe injects the operator's
    # persona + the SSOT environment/language/locale guidance as system
    # messages; pass them here so the FINAL answer carries the operator's
    # voice/tone/verbosity/units + the right language. Framed as STYLE only
    # so the tight re-shaper never treats it as new tasks/tools.
    if persona_system and persona_system.strip():
        system += (
            "\n\nFINAL-ANSWER STYLE & PERSONA (apply to voice, tone, length, "
            "units, and language ONLY; never as new tasks, tools, or content "
            "to add):\n" + persona_system.strip()[:2000]
        )
    hist_block = _format_tool_history(tool_history)
    # Phase E.1d: also fold in mios-daemon's satisfaction verdicts so
    # polish has the daemon's AND-folded ground truth available
    # alongside the raw tool_call rows. The daemon verdict is the
    # MOST AUTHORITATIVE signal (it cross-checks multiple sources);
    # raw tool_calls are still useful for the per-step detail.
    sat_verdicts = await _recent_satisfaction_verdicts(limit=3)
    sat_block = _format_satisfaction_block(sat_verdicts)
    # Thinking is disabled via enable_thinking=False on the /v1 call below -- qwen3
    # ignores /no_think and would otherwise emit empty content after a
    # long think pass (same fix + failure mode as refine; was the source
    # of the 45s polish timeout, operator test).
    user_msg_parts = [
        f"User's ORIGINAL message (reply in THIS exact language, "
        f"one language only):\n{user_q}"
    ]
    if refined_q and refined_q.strip() and refined_q.strip() != user_q:
        user_msg_parts.append(
            f"Refined intent (use for CONTENT only, never for language):\n"
            f"{refined_q}")
    if sat_block:
        user_msg_parts.append(sat_block)
    if hist_block:
        user_msg_parts.append(hist_block)
    # Evidence for the INVOKED-TOOL CHECK in _POLISH_SYSTEM: the verbs the
    # sub-agent ACTUALLY invoked this turn (captured from its tool-call
    # stream). Lets polish refuse a "done"/"sent"/"posted" claim the agent
    # made WITHOUT a matching tool invocation (the
    # agent fabricated "I've sent it to Discord" / a fake OpenUI render with
    # no tool actually run). Empty list => the agent invoked NO tools, so any
    # completed-action claim is unbacked.
    if agent_tools is not None:
        _inv = ", ".join(str(t) for t in agent_tools) if agent_tools else "(none)"
        user_msg_parts.append(
            f"Tools the agent ACTUALLY invoked this turn: {_inv}")
    # SOURCES survive the handoff : the live web-research
    # grounding (with [n] URLs + fetched text) reaches the FINAL pass so it can
    # cite [n] inline and verify the draft against the REAL sources, not just the
    # agents' paraphrase.
    _src = (refined or {}).get("_web_sources") or ""
    if _src:
        user_msg_parts.append(
            "WEB SOURCES used this turn (cite [n] inline; verify the draft's "
            "specifics against these -- assert only what they support):\n"
            + _src[:6000])
    # VERITY fact-check: fresh searches verifying the draft's uncertain specifics
    # (the checks pass can use web tools to fact-check).
    _fc_block = await _verity_factcheck(raw_text, user_q, refined)
    if _fc_block:
        user_msg_parts.append(_fc_block)
    # Feed the FULL sub-agent draft (capped generously) so polish
    # synthesises the complete answer instead of a truncated/mis-focused
    # slice -- the 3500 cap made polish produce partial answers + "no
    # data" contradictions of a summary it couldn't fully see (operator
    #). The polish now runs on the fast 4b dGPU lane, so 8000
    # chars is cheap.
    user_msg_parts.append(f"Raw answer from sub-agent:\n{raw_text[:8000]}")
    user_msg = "\n\n".join(user_msg_parts)
    url, payload = _polish_post(
        POLISH_ENDPOINT, POLISH_MODEL,
        [{"role": "system", "content": system},
         {"role": "user", "content": user_msg}],
        int(max_tokens) if max_tokens else POLISH_MAX_TOKENS)
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=POLISH_TIMEOUT_S) as s:
            r = await s.post(url, json=payload,
                             headers={"Content-Type": "application/json"})
            if r.status_code != 200:
                log.warning("polish: backend %s in %.1fs: %s", r.status_code, time.time() - t0, r.text[:200])
                return None
            body = r.json()
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        log.warning("polish: timeout/http error after %.1fs: %s",
                    time.time() - t0, e)
        return None
    except Exception as e:
        log.warning("polish unexpected error: %s", e)
        return None
    log.info("polish: %.1fs", time.time() - t0)
    # OpenAI /v1 choices[] shape (MiOS is /v1-only).
    choices = body.get("choices") or []
    msg = (choices[0].get("message") if choices else {}) or {}
    polished = (msg.get("content") or "").strip()
    if not polished:
        return None
    # OUTPUT-SIDE anti-fabrication guard: drop any $-price / N%-percent the
    # polish model INVENTED (absent from the draft+research+agents'-findings+
    # web sources it was given). Catches the recurring "as low as $184 [3]" /
    # "~2% cheaper [1]" tip-fabrication that the prompt rules alone don't hold
    # on the 4b lane. Haystack = everything polish saw.
    polished = _strip_ungrounded_figures(
        polished, "\n".join([raw_text or "", _src or "", _fc_block or ""]))
    # Non-empty guarantee : the figure-guard must NEVER leave a
    # grounded answer empty/blank -- if it did, keep the model's own raw draft instead
    # (which then feeds the answer, never a hardcoded dead-end downstream).
    if not (polished and polished.strip()):
        log.info("polish: figure-guard emptied a grounded answer -> raw draft")
        polished = (raw_text or "").strip()
    # ASK-TO-RUN proposal + anti-fabrication ("mios daemon should
    # ask user to run things"): if a HITL-tier action was intercepted this turn, the pipe
    # PROPOSES it (a pending_action was recorded) and asks the user to approve -- instead
    # of silently no-op'ing or (worse) the small model FABRICATING the un-run result
    # (live-seen: a blocked `coderun` -> a WRONG in-head product as exact). Render a
    # clear, portable proposal (NL + a fenced mios_proposed_action JSON block; works in
    # OWUI + CLI, which do NOT execute upstream tool_calls -- research §4). The user's
    # next "yes" (model-classified) re-runs it. The HITL gate itself is UNCHANGED.
    try:
        _prop = _proposal_var.get()
        if isinstance(_prop, dict) and _prop.get("tool") and "mios_proposed_action" not in (polished or ""):
            import json as _pj
            _ptool = str(_prop.get("tool"))
            _pargs = _prop.get("args") if isinstance(_prop.get("args"), dict) else {}
            _block = _pj.dumps({"mios_proposed_action": {
                "tool": _ptool, "args": _pargs,
                "action_hash": _prop.get("action_hash"),
                "reply_yes_to_run": True}}, ensure_ascii=False)
            polished = (polished or "").rstrip() + (
                f"\n\n> 🛠️ **Proposed action — needs your OK.** I can run `{_ptool}` for "
                f"you, but it's a high-impact action gated for approval, so it did **not** "
                f"run yet. Reply **yes** to run it now, or **no** to skip. (Anything above "
                f"that depended on it is an unverified estimate until then.)"
                f"\n\n```json\n{_block}\n```")
    except Exception:  # noqa: BLE001 -- never break the answer on the proposal note
        pass
    # GLOBAL ASK-USER: clarification ("ask user... for questions and
    # clarifications too, not just coderunning"). If the answer is PRIMARILY a clarifying
    # QUESTION (model-classified; gated on a '?' so the judge runs rarely) and we did NOT
    # already propose an action, mark it mios_clarification so OWUI/Hermes render a native
    # INPUT prompt (the typed answer becomes the next turn). Degrade-open.
    try:
        if (ASK_CLARIFY_JUDGE_ENABLE and "?" in (polished or "")
                and not isinstance(_proposal_var.get(), dict)
                and "mios_clarification" not in (polished or "")):
            _cq = await _clarify_question(user_q, polished)
            if _cq:
                import json as _cj
                _cb = _cj.dumps({"mios_clarification": {"question": _cq}}, ensure_ascii=False)
                polished = (polished or "").rstrip() + f"\n\n```json\n{_cb}\n```"
    except Exception:  # noqa: BLE001 -- never break the answer on the clarify note
        pass
    # Store the finished Q+A (with sources) to the global knowledge table.
    # Fire-and-forget -- the answer is already returned regardless.
    # P2: satisfied is left None here -- polish_response has no DoD verdict in
    # scope (the inline satisfaction check runs in this function's CALLERS,
    # async, not threaded down). Degrade-open: the outcome field is simply
    # omitted (recall rank treats it neutral). Wiring the live verdict down to
    # this store call is a follow-up; we deliberately do NOT add a new
    # synchronous satisfaction call in the hot path.
    _store_knowledge(query=user_q, answer=polished,
                     session_id=session_id, tool_history=tool_history,
                     satisfied=None)
    # P5.7 (Hermes v2026.5.28 brief L6 "closed-loop self-learning"): render
    # the run as a SKILL.md episodic-memory file alongside the knowledge row.
    # Same fire-and-forget posture; failure logs at debug + never affects the
    # already-returned answer. Knowledge table is the RAG-recall surface; the
    # SKILL.md is the human-readable + Obsidian-vault-compatible mirror that
    # the upcoming OpenViking-style L0/L1/L2 indexer (#62) can ingest.
    _write_skill_md_fire(query=user_q, answer=polished,
                         tool_history=tool_history, session_id=session_id)
    return polished
