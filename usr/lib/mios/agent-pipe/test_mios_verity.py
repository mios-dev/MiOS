#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_verity (refactor R6 extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the anti-fabrication invariants of the extracted POLISH/VERITY cluster: _strip_ungrounded_figures drops a $-price sentence whose number is ABSENT from the haystack while KEEPING a grounded one (and honours the >half-the-figures fail-safe by leaving the answer untouched); polish_response short-circuits to None on empty raw_text, and -- with every injected dep stubbed + httpx monkeypatched to a canned 200 + verity gated off (no hint_tools) -- passes a no-figure/no-contradiction draft through unchanged. Guards the extracted cluster + its configure() DI seam so a later move can't silently change fact-check behaviour.
# AI-related: ./mios_verity.py
# AI-functions: check, t_strip_figures, t_strip_failsafe, t_strip_unicode_sentence, t_abbr_from_ssot, t_polish_empty, t_polish_passthrough, t_clarify_empty, t_clarify_extracts_question, main
"""Unit tests for mios_verity (refactor R6)."""

import asyncio
import contextvars
import sys
import types

import mios_verity as v

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    line = f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else "")
    try:
        print(line)
    except UnicodeEncodeError:
        # A narrow console (Windows cp1252) can't encode the non-Latin script
        # tokens these tests assert on; never let stdout encoding fail the run.
        enc = sys.stdout.encoding or "ascii"
        print(line.encode(enc, "replace").decode(enc))


def t_strip_figures():
    # One grounded $-price (184 is in the haystack) + one ungrounded ($999 absent).
    answer = "Deals as low as $184 are available. Prices drop to $999 today."
    haystack = "We found fares around $184 on the route."
    out = v._strip_ungrounded_figures(answer, haystack)
    check("strip: keeps grounded $184", "$184" in out, out)
    check("strip: drops ungrounded $999", "$999" not in out, out)


def t_strip_failsafe():
    # No numeric grounding at all -> haystack has no digits -> leave untouched.
    answer = "It costs $500 and is 12% off."
    check("strip: empty-haystack untouched",
          v._strip_ungrounded_figures(answer, "no numbers here") == answer)
    # Empty answer round-trips.
    check("strip: empty answer untouched", v._strip_ungrounded_figures("", "x $5") == "")


def t_strip_unicode_sentence():
    # Script-neutrality: a CJK answer line with NO ASCII sentence boundary. The
    # ungrounded-figure clause ($999) is terminated by the ideographic full stop
    # (。), not "<period> <space>". The OLD ASCII-only splitter treated the whole
    # line as ONE sentence -> a grounded figure anywhere kept the ungrounded one
    # (its non-Latin neighbour never policed). The unicode-aware splitter gives
    # the CJK line per-sentence granularity: keep the grounded 東京/$184 clause,
    # drop ONLY the ungrounded 大阪/$999 clause -- the non-Latin token survives.
    answer = "東京の価格は $184 です。大阪の価格は $999 です。"
    haystack = "東京 fares around $184 were found."
    out = v._strip_ungrounded_figures(answer, haystack)
    check("strip(cjk): keeps grounded 東京/$184", "$184" in out and "東京" in out, out)
    check("strip(cjk): drops ungrounded 大阪/$999", "$999" not in out and "大阪" not in out, out)


def t_abbr_from_ssot():
    # The abbreviation screen is SSOT-driven (configure(abbreviations=...) <- the
    # mios.toml [verity] read), NOT a literal baked in code: feeding a DIFFERENT
    # list changes which trailing periods are protected -> changes the split ->
    # changes the output. Behaviour must follow the config value.
    answer = "Items etc. $999 listed. Final price $184 today."
    haystack = "Final price was $184."
    # (1) "etc." IS an abbreviation -> its period is protected -> "Items etc. $999
    #     listed." is ONE sentence -> dropped whole (ungrounded $999) -> "etc." gone.
    v.configure(abbreviations=["etc."])
    out_protected = v._strip_ungrounded_figures(answer, haystack)
    check("abbr(ssot): protected 'etc.' -> sentence dropped",
          "Items etc" not in out_protected and "$184" in out_protected, out_protected)
    # (2) "etc." NOT in the list -> its period splits -> "Items etc." is its own
    #     figure-less sentence -> survives, only "$999 listed." is dropped.
    v.configure(abbreviations=["zzz."])
    out_split = v._strip_ungrounded_figures(answer, haystack)
    check("abbr(ssot): unprotected 'etc.' -> sentence kept",
          "Items etc" in out_split and "$999" not in out_split, out_split)
    # Restore the shipped default so later tests see vendor behaviour.
    v.configure(abbreviations=list(v._ABBR_DEFAULT))


# ── polish_response behavioural (stubbed deps + monkeypatched httpx) ──
_SENT = "The capital of France is Paris."


class _FakeResp:
    status_code = 200
    text = ""

    def json(self):
        return {"choices": [{"message": {"content": _SENT}}]}


class _FakeClient:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        return _FakeResp()


async def _ath(*a, **k):
    return []


async def _averd(*a, **k):
    return []


def _wire_stubs():
    pv = contextvars.ContextVar("proposal", default=None)
    v.configure(
        polish_enabled=True,
        polish_system="SYS",
        polish_endpoint="http://127.0.0.1:0",
        polish_model="m",
        polish_max_tokens=100,
        polish_timeout_s=5,
        ask_clarify_judge_enable=False,
        polish_post=lambda ep, m, msgs, mt, temperature=0.0: ("http://127.0.0.1:0/v1/chat/completions", {}),
        recent_tool_history=_ath,
        format_tool_history=lambda rows: "",
        recent_satisfaction_verdicts=_averd,
        format_satisfaction_block=lambda rows: "",
        store_knowledge=lambda **k: None,
        write_skill_md_fire=lambda **k: None,
        proposal_var=pv,
    )
    # Canned 200 so no real network is touched; keep HTTPError type for the except.
    v.httpx = types.SimpleNamespace(AsyncClient=_FakeClient, HTTPError=Exception)
    # _env_grounding is imported from mios_grounding, which needs server-side DI
    # we don't run here; stub it to a constant for the offline behavioural test.
    v._env_grounding = lambda: "ENV"


def t_polish_empty():
    # Empty raw_text short-circuits to None before any dep is touched.
    out = asyncio.run(v.polish_response("", {"intended_outcome": "x"}))
    check("polish: empty raw -> None", out is None)


def t_polish_passthrough():
    _wire_stubs()
    # intended_outcome set so the short-raw skip-gate is bypassed; no hint_tools
    # so the verity fact-check stays gated (no network); no figures -> no strip.
    out = asyncio.run(v.polish_response(
        "Paris is the capital.",
        {"intended_outcome": "answer the question"},
        session_id=None,
        original_user_text="What is the capital of France?"))
    check("polish: passes canned model output through", out == _SENT, repr(out))


# ── _clarify_question (generative clarification judge, moved home) ──
# Synthetic non-dictionary token as the model's returned question -- the judge is
# model-driven (no baked keyword screen), so the test pins ONLY that the function
# (a) short-circuits an empty answer and (b) extracts the model's `question` field.
_CLARIFY_TOKEN = "Zyxqq-wuvil-3?"


class _FakeClarifyClient:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **k):
        import json as _j
        return types.SimpleNamespace(
            status_code=200,
            json=lambda: {"choices": [{"message": {
                "content": _j.dumps({"question": _CLARIFY_TOKEN})}}]},
        )


def t_clarify_empty():
    # Empty answer short-circuits to '' before any network is touched.
    check("clarify: empty answer -> ''", asyncio.run(v._clarify_question("zzv-qmx", "")) == "")


def t_clarify_extracts_question():
    saved = v.httpx
    v.httpx = types.SimpleNamespace(AsyncClient=_FakeClarifyClient, HTTPError=Exception)
    try:
        out = asyncio.run(v._clarify_question("wqx-plok", "vmz-trun?"))
    finally:
        v.httpx = saved
    check("clarify: extracts model 'question' field", out == _CLARIFY_TOKEN, repr(out))


def main():
    t_strip_figures()
    t_strip_failsafe()
    t_strip_unicode_sentence()
    t_abbr_from_ssot()
    t_polish_empty()
    t_polish_passthrough()
    t_clarify_empty()
    t_clarify_extracts_question()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
