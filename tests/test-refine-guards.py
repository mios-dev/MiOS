#!/usr/bin/env python3
# AI-hint: Canonical consolidated refine post-parse guard suite (absorbed tests/test-refine-guard.py, which is now a delegating shim). Deterministic ...
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Refine post-parse guard suite (canonical, consolidated).

Covers the REAL production guard -- ``refine_intent`` imported from its real
module path (``usr/lib/mios/agent-pipe/mios_refine.py`` re-exporting
``mios_pipe/routing/refine.py``) -- NOT any inline copy of its logic.

Two layers, honestly separated:

* Deterministic offline tests drive the real ``refine_intent`` through a
  canned OpenAI-compatible transport (the stub recipe the upstream unit suite
  ``test_mios_refine.py`` uses), so they need NO live model endpoint. They
  prove positive and negative controls for every guard: chat-promotion for
  actionable text, long-prompt promotion, short-dispatch passthrough,
  wordy-arg (arg-shape) demotion, multi_task shape repair, and
  malformed/failure behavior (backend error, unparseable prose, empty
  content -> None, never a fabricated result).

* Live integration tests (3, named ``test_live_*``) exercise the deployed
  stack through ``server.refine_intent`` (the traced production entrypoint).
  They are OPT-IN via ``MIOS_REFINE_LIVE_ENDPOINT``. When that env var is
  absent they SKIP explicitly -- under pytest as a reported skip, standalone
  as a printed ``[SKIP]`` line that is never counted as a passed check.

Standalone entrypoint (run-suites.sh unit tier)::

    python3 tests/test-refine-guards.py      # pass=N skip=M fail=K summary

History: this file consolidated (losslessly) the former
tests/test-refine-guards.py (3 cases) and tests/test-refine-guard.py
(3 chat-promotion smoke cases). The old case 3 validated an INLINE COPY of
the wordy-arg guard instead of the production function -- that defect is
fixed here by driving the real ``refine_intent`` with the forged envelope.
"""
from __future__ import annotations
import asyncio
import contextvars
import functools
import importlib
import json
import os
import sys

import _agentpipe_path  # noqa: F401
import mios_refine as mr  # noqa: E402  (re-export shim -> mios_pipe.routing.refine)

try:
    import pytest
except ImportError:  # pragma: no cover -- standalone hosts without pytest
    pytest = None


# ---------------------------------------------------------------- transport
# Canned OpenAI-compatible transport, swapped in for ``mr.httpx`` -- the same
# recipe as usr/lib/mios/agent-pipe/test_mios_refine.py, so the real
# refine_intent() runs end-to-end (build payload -> POST -> parse -> guards)
# against deterministic canned bodies with no network.

class _Log:
    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    warn = warning


class _FakeResp:
    def __init__(self, body, status=200):
        self.status_code = status
        self._body = body
        self.text = ""

    def json(self):
        return self._body


class _FakeClient:
    def __init__(self, owner):
        self._owner = owner

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        return _FakeResp(self._owner.body, self._owner.status)


class _FakeHTTPX:
    HTTPError = Exception  # refine_intent catches httpx.HTTPError on retries

    def __init__(self):
        self.body = None
        self.status = 200

    def AsyncClient(self, timeout=None):
        return _FakeClient(self)


_REAL_HTTPX = mr.httpx
_FAKE = _FakeHTTPX()


def _isolated(fn):
    """Restore production injectables after every call, including assertion failures."""
    @functools.wraps(fn)
    def run():
        if fn.__name__.startswith("test_live_"):
            _require_live()
            # Capture the real server's boot configuration before changing its endpoint.
            importlib.import_module("server")
        target = importlib.import_module("mios_pipe.routing.refine")
        saved = vars(target).copy()
        saved_fake = (_FAKE.body, _FAKE.status)
        try:
            return fn()
        finally:
            vars(target).clear()
            vars(target).update(saved)
            _FAKE.body, _FAKE.status = saved_fake
    return run

# Mirrors the production fastpath composition in server.py (_FASTPATH_VERBS =
# OS-control | schedule | memory | PC-input sections); same sample the
# upstream unit suite injects.
_FASTPATH = frozenset(
    {"open_url", "launch_app", "launch_verified", "focus_window", "pc_type"})
_VERB_CATALOG = {"open_url": {}, "launch_app": {}, "open_app": {},
                 "focus_window": {}, "remember": {}, "web_search": {}}

# Original operator-flagged corpus -------------------------------------
LONG_PROMPT = (
    "find all of my installed games; research all their ratings, "
    "review and launch the highest reviewed game I have installed "
    "for me on my PC"
)                                   # 144 chars > REFINE_PROMOTE_CHARS (100)
SHORT_DISPATCH = "open chrome"      # 11 chars: legitimate single dispatch
ACTIONABLE_CASES = [                # historically misclassified as chat
    "mios-open-url https://www.wikipedia.org",
    "https://example.com",
    "git status",
]


class _Skipped(Exception):
    """Standalone-mode skip signal (pytest uses pytest.skip instead)."""


def _install() -> None:
    """Point the REAL module at the canned transport + stub injectables.

    ``configure`` is the module's public injection seam (the same one
    server.py calls at boot); nothing here re-implements guard logic.
    """
    mr.httpx = _FAKE
    # Isolate the post-parse guards: the deterministic OS-action router is a
    # different guard with its own suite (upstream recipe).
    mr._deterministic_action_route = lambda _t: None

    async def _route_domain(_txt):
        return None

    mr.configure(
        logger=_Log(),
        agent_registry={},
        verb_catalog=_VERB_CATALOG,
        routed_domain_var=contextvars.ContextVar("routed_domain", default=None),
        over_global_ceiling=lambda: False,
        resolve_verb_key=lambda name: name,
        route_domain=_route_domain,
        db_fire=lambda *a, **k: None,
        db_post=lambda *a, **k: None,
        db_create=lambda *a, **k: {},
        refine_enabled=True,
        refine_model="test-refine",
        refine_endpoint="http://stub.local",
        refine_max_tokens=700,
        refine_timeout_s=5,
        refine_attempts=1,
        os_control_verbs_rendered="",
        browser_action_alt="",
        web_search_triggers=[],
        web_search_contexts=[],
        remember_triggers=[],
        fastpath_verbs=_FASTPATH,
        routing_enable=False,
        routing_domains={},
        promote_chars=100,
        chat_chars=40,
        dispatch_chars=60,
        dispatch_arg_max_words=3,
    )


def _run(user_text, envelope, status=200):
    """One real refine_intent() call against a canned model body."""
    _FAKE.body = {"choices": [{"message": {"content": json.dumps(envelope)}}]}
    _FAKE.status = status
    return asyncio.run(mr.refine_intent(user_text, None))


# ============================================================================
# Deterministic offline guard coverage (no live endpoint required)
# ============================================================================

def test_chat_promotion_overrides_chat_for_actionable_text():
    """Former test-refine-guard.py corpus: actionable prefixes / URLs must
    never survive as intent=chat; the guard rewrites chat -> dispatch."""
    _install()
    for text in ACTIONABLE_CASES:
        r = _run(text, {"intent": "chat", "refined_text": text,
                        "reply": "Sure, Wikipedia has been opened."})
        assert r is not None, f"refine returned None for {text!r}"
        assert r.get("intent") != "chat", (
            f"{text!r} still classified chat (guard did not promote): {r!r}")
        assert "reply" not in r, (
            f"canned chat reply survived promotion for {text!r}: {r!r}")


def test_chat_promotion_negative_genuine_chat_stays_chat():
    """Negative control: short conversational input is NOT over-promoted."""
    _install()
    r = _run("hey there", {"intent": "chat", "refined_text": "hey there",
                           "reply": "Hi! How can I help?"})
    assert r is not None, "genuine chat returned None"
    assert r.get("intent") == "chat", f"genuine chat demoted: {r!r}"
    assert r.get("reply") == "Hi! How can I help?", f"reply lost: {r!r}"


def test_long_multistep_dispatch_promoted_to_agent():
    """Case 1 (failure-trace faithful): model emits intent=dispatch for the
    144-char multi-step prompt; the length guard must promote to agent."""
    _install()
    r = _run(LONG_PROMPT, {
        "intent": "dispatch", "refined_text": LONG_PROMPT,
        "tool": "open_app",
        "args": {"name": "the highest reviewed game I have installed"}})
    assert r is not None, "long multi-step prompt returned None"
    assert r.get("intent") in ("agent", "dag", "multi_task"), (
        f"long prompt not demoted from dispatch, got {r.get('intent')!r}")


def test_long_multistep_chat_promoted_to_agent():
    """Long prompt the model calls chat must also promote (no chat replies
    for multi-step goals)."""
    _install()
    r = _run(LONG_PROMPT, {"intent": "chat", "refined_text": LONG_PROMPT,
                           "reply": "Which game?"})
    assert r is not None
    assert r.get("intent") in ("agent", "dag", "multi_task"), (
        f"long chat survived, got {r.get('intent')!r}")
    assert "reply" not in r


def test_short_dispatch_passthrough_unchanged():
    """Case 2: a short, concrete dispatch passes the guards untouched."""
    _install()
    r = _run(SHORT_DISPATCH, {"intent": "dispatch",
                              "refined_text": SHORT_DISPATCH,
                              "tool": "launch_app", "args": {"name": "chrome"}})
    assert r is not None, "short dispatch returned None"
    assert r.get("intent") == "dispatch", f"short dispatch demoted: {r!r}"
    assert r.get("tool") == "launch_app", f"tool mangled: {r!r}"
    assert r.get("args") == {"name": "chrome"}, f"args mangled: {r!r}"


def test_wordy_dispatch_arg_promoted_to_agent():
    """Former inline-copy defect, de-inlined: the forged envelope goes
    through the REAL refine_intent; a >3-word semantic arg on a non-fastpath
    dispatch must promote to agent (launcher cannot resolve it)."""
    _install()
    r = _run("launch the highest reviewed game", {
        "intent": "dispatch", "refined_text": "launch the best game",
        "tool": "open_app",
        "args": {"name": "the highest reviewed game on disk"}})  # 6 words
    assert r is not None, "forged-envelope call returned None"
    assert r.get("intent") == "agent", (
        f"arg-shape guard missed multi-word semantic arg: {r!r}")


def test_concrete_dispatch_arg_not_promoted():
    """Negative control for the arg-shape guard: concrete short args stay
    dispatch."""
    _install()
    r = _run("open discord", {"intent": "dispatch",
                              "refined_text": "open discord",
                              "tool": "launch_app",
                              "args": {"name": "discord"}})
    assert r is not None
    assert r.get("intent") == "dispatch", f"concrete arg wrongly demoted: {r!r}"


def test_fastpath_verb_wordy_arg_exempt():
    """Pins the deliberate _is_os exemption: OS fastpath dispatches keep their
    args even when wordy (they are window-diff verified downstream)."""
    _install()
    r = _run("open the best search engine", {
        "intent": "dispatch", "refined_text": "open the best search engine",
        "tool": "open_url",
        "args": {"url": "the best search engine today"}})  # 5 words, fastpath
    assert r is not None
    assert r.get("intent") == "dispatch", (
        f"fastpath exemption lost, wrongly promoted: {r!r}")


def test_multi_task_with_fewer_than_two_tasks_degrades():
    """Malformed shape repair: multi_task without a real tasks array (>=2)
    degrades to agent and flags _multi_step."""
    _install()
    r = _run("several things at once", {
        "intent": "multi_task", "refined_text": "several things",
        "tasks": [{"title": "only one goal"}]})
    assert r is not None, "malformed multi_task returned None"
    assert r.get("intent") == "agent", (
        f"single-task multi_task not degraded: {r!r}")
    assert r.get("_multi_step") is True, f"_multi_step flag missing: {r!r}"
    assert "tasks" not in r, f"bogus tasks array survived: {r!r}"


def test_backend_error_returns_none():
    """Refinement failure honesty: a 5xx backend yields None, never a
    fabricated envelope."""
    _install()
    r = _run("open chrome", {"intent": "dispatch",
                             "refined_text": "open chrome"}, status=500)
    assert r is None, f"backend 500 produced a result: {r!r}"


def test_unparseable_prose_returns_none():
    """Refinement failure honesty: prose the lenient parser cannot turn into
    a dict yields None (no fabricated classification)."""
    _install()
    r = _run("open discord", "I am sorry, I can't help with that request.")
    assert r is None, f"unparseable prose produced a result: {r!r}"


def test_empty_model_content_returns_none():
    """Refinement failure honesty: empty model content yields None."""
    _install()
    _FAKE.body = {"choices": [{"message": {"content": ""}}]}
    r = asyncio.run(mr.refine_intent("hello", None))
    assert r is None, f"empty content produced a result: {r!r}"


def test_truncated_json_repaired_to_dict():
    """Malformed-but-recoverable: truncated JSON is repaired by the lenient
    parser; the guards then still run on the recovered envelope."""
    _install()
    _FAKE.body = {"choices": [{"message": {"content":
        '{"intent": "dispatch", "refined_text": "open epiphany", '
        '"tool": "launch_app", "args": {"name": "epiphany"'}}]}
    r = asyncio.run(mr.refine_intent("open epiphany", None))
    assert isinstance(r, dict), f"truncated JSON not repaired: {r!r}"
    assert r.get("intent") == "dispatch" and r.get("tool") == "launch_app", (
        f"repaired envelope wrong: {r!r}")


# ============================================================================
# Live integration coverage (needs a real refine endpoint; OPT-IN)
# ============================================================================

_LIVE_ENV = "MIOS_REFINE_LIVE_ENDPOINT"


def _skip_live(reason: str):
    # Only a live pytest run gets pytest.skip(); standalone mode raises the
    # catchable _Skipped (pytest 8+/9 outcome exceptions are BaseException-
    # derived, so they must not be raised outside a runner that reports them).
    if pytest is not None and os.environ.get("PYTEST_CURRENT_TEST"):
        pytest.skip(reason)
    raise _Skipped(reason)


def _require_live():
    """Live tests run ONLY when explicitly opted in. Without the env var the
    coverage is a reported SKIP -- never counted as a passed verification."""
    ep = (os.environ.get(_LIVE_ENV) or "").strip()
    if not ep:
        _skip_live(
            f"live refine endpoint not configured (set {_LIVE_ENV}="
            "http://host:port to enable); deterministic guard coverage "
            "already ran offline")
    return ep


def _live_server():
    mr.httpx = _REAL_HTTPX  # real transport for the real call
    import server  # noqa: E402  heavy traced production entrypoint (lazy)
    ep = os.environ[_LIVE_ENV]
    if ep.startswith(("http://", "https://")):
        sys.modules["mios_refine"].configure(
            refine_endpoint=ep.rstrip("/"), refine_enabled=True)
    return server


def test_live_long_multistep_intent_not_shallow():
    ep = _require_live()
    server = _live_server()
    r = asyncio.run(server.refine_intent(LONG_PROMPT, history=None))
    assert r is not None, (
        f"live refine ({ep}) returned None for the long multi-step prompt -- "
        "service bypassed or model failed; refusing to count this as pass")
    assert r.get("intent") in ("agent", "dag", "multi_task"), (
        f"live model left a multi-step goal as {r.get('intent')!r}")


def test_live_short_dispatch_not_demoted():
    _require_live()
    server = _live_server()
    r = asyncio.run(server.refine_intent(SHORT_DISPATCH, history=None))
    assert r is not None, (
        "live refine returned None for a short dispatch -- service bypassed "
        "or model failed; refusing to count this as pass")
    assert r.get("intent") in ("dispatch", "agent"), (
        f"live model demoted a short dispatch to {r.get('intent')!r}")


def test_live_actionable_commands_not_chat():
    _require_live()
    server = _live_server()
    for text in ACTIONABLE_CASES:
        r = asyncio.run(server.refine_intent(text, history=None))
        assert r is not None, (
            f"live refine returned None for {text!r} -- service bypassed or "
            "model failed; refusing to count this as pass")
        assert r.get("intent") != "chat", (
            f"live model still classifies {text!r} as chat")


# ============================================================================
# Standalone runner (run-suites.sh unit tier: python3 tests/<this file>.py)
# ============================================================================

def _ordered_tests():
    names = [n for n in globals()
             if n.startswith("test_") and callable(globals()[n])]
    deterministic = [n for n in names if not n.startswith("test_live_")]
    live = [n for n in names if n.startswith("test_live_")]
    return [(n, globals()[n]) for n in deterministic + live]


def test_configuration_restored_after_failure():
    target = importlib.import_module("mios_pipe.routing.refine")
    before = vars(target).copy()
    @_isolated
    def failing_probe():
        _install()
        assert mr.httpx is _FAKE
        raise AssertionError("planted isolation failure")
    try:
        failing_probe()
    except AssertionError as error:
        assert str(error) == "planted isolation failure"
    else:
        raise AssertionError("negative isolation control never ran")
    assert vars(target).keys() == before.keys()
    assert all(vars(target)[name] is value for name, value in before.items()), (
        "test configuration leaked into the production module")


# Both pytest and the standalone compatibility entrypoint receive isolated tests.
for _name, _fn in _ordered_tests():
    globals()[_name] = _isolated(_fn)


def _run_all_standalone() -> int:
    passed = skipped = failed = 0
    for name, fn in _ordered_tests():
        try:
            fn()
        except _Skipped as s:
            skipped += 1
            print(f"[SKIP] {name}: {s}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
        except Exception as e:  # noqa: BLE001 -- honest failure, not a pass
            failed += 1
            print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        else:
            passed += 1
            print(f"[PASS] {name}")
    print(f"\nrefine-guard suite: {passed} passed, {skipped} skipped, "
          f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all_standalone())
