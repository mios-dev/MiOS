# AI-hint: Standalone unit test for mios-delegation-prefilter's MODEL-DRIVEN conversational-bypass classifier (_looks_conversational). Pure stdlib; imports the CLI module by path (no .py extension, libexec convention) behind a stub `aiohttp` so it loads without the real dep, then stubs the micro-LLM call (_micro_chat) to prove: the CHAT/ACT verdict comes from the MODEL not the words (a greeting the model calls ACT does NOT bypass; a long task the model calls CHAT does), degrade-open force-delegates when the micro lane raises, and a non-model mode disables the classifier -- asserting no keyword/length list drives the decision.
# AI-related: mios-delegation-prefilter
# AI-functions: _check, _run, t_model_chat_bypasses, t_model_act_forces, t_verdict_not_word_gated, t_degrade_open_on_error, t_mode_off_disabled, t_empty_text, main
"""Standalone unit test for mios-delegation-prefilter's conversational-bypass
classifier.

The bypass that decides which prompts SKIP the forced delegate_task tool_choice
is MODEL-DRIVEN (a micro-LLM chat-vs-act classifier) -- the old English greeting
regex list + 60-char length cutoff were deleted. This test imports the CLI module
by path (it has no .py extension) behind a stub ``aiohttp`` module so it loads
without the real dependency, then stubs the micro-LLM call (``_micro_chat``) to
prove:

  * the CHAT/ACT decision comes from the MODEL, not the user's words (a greeting
    the model labels ACT does NOT bypass; a long task sentence the model labels
    CHAT DOES) -- i.e. no keyword list or length cutoff drives the decision;
  * degrade-open: when the micro lane raises, the classifier returns False so the
    prefilter force-delegates (the safe majority behaviour);
  * a non-"model" mode disables the classifier entirely.

Run:  python test_mios_delegation_prefilter.py
"""
from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / "mios-delegation-prefilter"

# The CLI imports aiohttp at module top; stub it so the import succeeds on hosts
# without the dependency. Only the three imported names must exist -- the test
# patches _micro_chat, so none of these stubs are actually invoked.
if "aiohttp" not in sys.modules:
    _aiohttp = types.ModuleType("aiohttp")
    _aiohttp.web = types.SimpleNamespace()
    _aiohttp.ClientSession = object
    _aiohttp.ClientTimeout = object
    sys.modules["aiohttp"] = _aiohttp

_spec = importlib.util.spec_from_loader(
    "mios_delegation_prefilter",
    importlib.machinery.SourceFileLoader("mios_delegation_prefilter", str(_SRC)),
)
mdp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mdp)  # type: ignore[union-attr]

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _run(coro):
    return asyncio.run(coro)


def _stub_micro(verdict: str):
    """Replace the micro-LLM call with one that returns a fixed verdict string."""
    async def _fake(system, user, *, max_tokens):  # noqa: ANN001
        return verdict
    mdp._micro_chat = _fake


def _stub_micro_raises():
    async def _fake(system, user, *, max_tokens):  # noqa: ANN001
        raise RuntimeError("micro lane down")
    mdp._micro_chat = _fake


def t_model_chat_bypasses() -> None:
    """Model says CHAT -> bypass (conversational, skip force-delegate)."""
    mdp.BYPASS_MODE = "model"
    _stub_micro("CHAT")
    out = _run(mdp._looks_conversational("hello there"))
    _check("model CHAT verdict -> bypass", out is True, f"got {out!r}")


def t_model_act_forces() -> None:
    """Model says ACT -> do NOT bypass (force-delegate)."""
    mdp.BYPASS_MODE = "model"
    _stub_micro("ACT")
    out = _run(mdp._looks_conversational("audit these three services"))
    _check("model ACT verdict -> force-delegate", out is False, f"got {out!r}")


def t_verdict_not_word_gated() -> None:
    """The decision follows the MODEL, not the words: a bare greeting the model
    calls ACT is NOT bypassed, and a long task sentence the model calls CHAT IS
    bypassed -- the opposite of any greeting-word / length-cutoff gate."""
    mdp.BYPASS_MODE = "model"
    _stub_micro("ACT")
    greeting_forced = _run(mdp._looks_conversational("hi")) is False
    _stub_micro("CHAT")
    long_text = "please tell me everything about the project in great detail " * 3
    long_bypassed = _run(mdp._looks_conversational(long_text)) is True
    _check("verdict driven by model not keywords/length",
           greeting_forced and long_bypassed,
           f"greeting_forced={greeting_forced} long_bypassed={long_bypassed}")


def t_degrade_open_on_error() -> None:
    """Micro lane raises -> degrade-open to False (force-delegate), never a
    keyword fallback."""
    mdp.BYPASS_MODE = "model"
    _stub_micro_raises()
    out = _run(mdp._looks_conversational("hello"))
    _check("degrade-open on micro failure -> force-delegate", out is False, f"got {out!r}")


def t_mode_off_disabled() -> None:
    """Non-'model' mode disables the classifier; no model call, returns False
    even for an obvious greeting."""
    mdp.BYPASS_MODE = "off"

    async def _boom(system, user, *, max_tokens):  # noqa: ANN001
        raise AssertionError("micro_chat must NOT be called when mode != model")
    mdp._micro_chat = _boom
    out = _run(mdp._looks_conversational("hi"))
    _check("mode!=model disables classifier (no model call)", out is False, f"got {out!r}")


def t_empty_text() -> None:
    """Empty / whitespace prompt -> False without a model call."""
    mdp.BYPASS_MODE = "model"

    async def _boom(system, user, *, max_tokens):  # noqa: ANN001
        raise AssertionError("micro_chat must NOT be called for empty text")
    mdp._micro_chat = _boom
    out = _run(mdp._looks_conversational("   "))
    _check("empty text -> False, no model call", out is False, f"got {out!r}")


def t_no_keyword_lists_remain() -> None:
    """Structural proof the deleted gates are gone: the module no longer defines
    the greeting/fanout keyword lists."""
    gone = (not hasattr(mdp, "_CONVERSATIONAL_RES")
            and not hasattr(mdp, "FANOUT_PATTERNS")
            and not hasattr(mdp, "_looks_fanoutable"))
    _check("greeting/fanout keyword gates deleted", gone,
           "found a residual keyword list" if not gone else "")


def main() -> int:
    for t in (t_model_chat_bypasses, t_model_act_forces, t_verdict_not_word_gated,
              t_degrade_open_on_error, t_mode_off_disabled, t_empty_text,
              t_no_keyword_lists_remain):
        t()
    n_fail = sum(1 for _n, ok, _d in _RESULTS if not ok)
    print(f"\n{len(_RESULTS) - n_fail}/{len(_RESULTS)} passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
