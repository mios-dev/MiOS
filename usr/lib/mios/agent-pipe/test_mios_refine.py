#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_refine (refactor R5 REFINE-classifier extraction). Pure stdlib, no server.py/DB/network/pytest. Drives the configure() DI seam with stub deps (no-op logger, empty agent registry, a small verb catalog, a fake httpx whose AsyncClient.post returns a canned model body) and asserts: (1) _salvage_refine_dispatch recovers a one-verb dispatch from a RESCUE corpus -- prose with embedded JSON, a VERB(args) call in narration, key=value + bare-positional args, longest-name-first matching, and a pure-prose miss -> None; (2) refine_intent parses representative classifier envelopes (plain JSON, ```json-fenced, <think>-wrapped, and a narrated/salvaged prose reply) end-to-end into the intent/refined_text/web/news/local_state shape with strict-bool coercion. Guards the prompt-sensitive classifier so a later move can't silently change the salvage or envelope-parse contract.
# AI-related: ./mios_refine.py, ./mios_jsonsalvage.py
# AI-functions: check, _configure, t_salvage_corpus, t_refine_envelope, main
"""Unit tests for mios_refine (refactor R5). Offline, stubbed model call."""

import asyncio
import contextvars
import json

import mios_refine as mr

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


class _Log:
    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    warn = warning


# ---- fake httpx (no network) -------------------------------------------------
class _FakeResp:
    def __init__(self, body):
        self.status_code = 200
        self._body = body
        self.text = ""

    def json(self):
        return self._body


class _FakeClient:
    def __init__(self, body):
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        return _FakeResp(self._body)


class _FakeHTTPX:
    HTTPError = Exception

    def __init__(self):
        self.body = None

    def AsyncClient(self, timeout=None):
        return _FakeClient(self.body)


_FAKE = _FakeHTTPX()

_FASTPATH = frozenset(
    {"open_url", "launch_app", "launch_verified", "focus_window", "pc_type"})


# ---- fake backend client for the heavy-path critic->refiner ------------------
# _critic_refine_agent re-invokes the backend via client.post(url, content=...,
# headers=...) (httpx-style) -- distinct from the refine classifier's own
# AsyncClient. A bare object with an async post returning a canned revision body.
class _CritResp:
    def __init__(self, body, status=200):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


class _CritClient:
    def __init__(self, body, status=200):
        self._body = body
        self._status = status
        self.calls = 0

    async def post(self, url, content=None, headers=None):
        self.calls += 1
        return _CritResp(self._body, self._status)


def _configure():
    """Inject stub deps so import-clean module globals become exercise-ready."""
    mr.httpx = _FAKE  # swap the module's httpx for the canned-body fake
    # _env_grounding / _deterministic_action_route are sibling imports the real
    # server configures (mios_grounding / mios_routing). Stub them for an isolated
    # unit -- their own behaviour is covered by their own test_*.py.
    mr._env_grounding = lambda: ""
    mr._deterministic_action_route = lambda _t: None

    async def _route_domain(_txt):
        return None

    mr.configure(
        logger=_Log(),
        agent_registry={},
        verb_catalog={"open_url": {}, "launch_app": {}, "remember": {},
                      "web_search": {}, "focus_window": {}},
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
    )


# ---- RESCUE corpus: prose -> one-verb dispatch -------------------------------
def t_salvage_corpus():
    # 1) Narration with an EMBEDDED JSON object -> returned as-is (intent present).
    d = mr._salvage_refine_dispatch(
        'Sure, here is the plan: '
        '{"intent":"dispatch","tool":"open_url","args":{"url":"https://x.com"}}')
    check("salvage.embedded_json", isinstance(d, dict)
          and d.get("intent") == "dispatch" and d.get("tool") == "open_url",
          repr(d))

    # 2) A VERB(args) call narrated in prose (the canonical 'Open discord' lie).
    d = mr._salvage_refine_dispatch(
        'To open Discord on your desktop, I will launch_app("Discord PTB").')
    check("salvage.verb_call_quoted", isinstance(d, dict)
          and d.get("tool") == "launch_app"
          and (d.get("args") or {}).get("name") == "Discord PTB"
          and d.get("_salvaged") is True, repr(d))

    # 3) key=value args inside the call.
    d = mr._salvage_refine_dispatch(
        'I will now call open_url(url="https://wikipedia.org") for you.')
    check("salvage.kv_args", isinstance(d, dict) and d.get("tool") == "open_url"
          and (d.get("args") or {}).get("url") == "https://wikipedia.org", repr(d))

    # 4) bare positional value -> the verb's primary arg (name for focus_window).
    d = mr._salvage_refine_dispatch("focus_window(Forza)")
    check("salvage.bare_positional", isinstance(d, dict)
          and d.get("tool") == "focus_window"
          and (d.get("args") or {}).get("name") == "Forza", repr(d))

    # 5) longest-name-first: launch_verified beats a launch-prefix substring.
    d = mr._salvage_refine_dispatch("Running launch_verified(Steam) next.")
    check("salvage.longest_first", isinstance(d, dict)
          and d.get("tool") == "launch_verified", repr(d))

    # 6) pure prose with no verb -> None (drop to the normal path, no false action).
    d = mr._salvage_refine_dispatch("I'm sorry, I can't help with that request.")
    check("salvage.pure_prose_none", d is None, repr(d))

    # 7) empty input -> None.
    check("salvage.empty_none", mr._salvage_refine_dispatch("") is None)


# ---- envelope parse + strict-bool coercion (stubbed model call) --------------
def _run(user_text, body):
    _FAKE.body = {"choices": [{"message": {"content": body}}]}
    return asyncio.run(mr.refine_intent(user_text, None))


def t_refine_envelope():
    # plain JSON chat envelope -> intent chat, bools coerced, metadata stamped.
    p = _run("hey there", json.dumps(
        {"intent": "chat", "refined_text": "hey there", "reply": "Hi!",
         "web": False, "news": False, "local_state": False}))
    check("refine.chat_intent", isinstance(p, dict) and p.get("intent") == "chat",
          repr(p))
    check("refine.metadata_stamped",
          p.get("_model") == "test-refine" and "_elapsed_s" in p, repr(p))
    check("refine.bools_strict", p.get("web") is False and p.get("news") is False
          and p.get("local_state") is False, repr(p))

    # ```json-fenced agent envelope with web=true (string truthy coercion path).
    p = _run("latest news on X", "```json\n" + json.dumps(
        {"intent": "agent", "refined_text": "latest news on X",
         "web": True, "news": "true", "local_state": False}) + "\n```")
    check("refine.fenced_agent", isinstance(p, dict) and p.get("intent") == "agent",
          repr(p))
    check("refine.web_true", p.get("web") is True, repr(p))
    check("refine.news_str_coerced", p.get("news") is True, repr(p))

    # <think>-wrapped envelope -> think stripped, JSON parsed.
    p = _run("open epiphany", "<think>the user wants a launch</think>" + json.dumps(
        {"intent": "dispatch", "refined_text": "open epiphany",
         "tool": "launch_app", "args": {"name": "epiphany"},
         "web": False, "news": False, "local_state": False}))
    check("refine.think_stripped", isinstance(p, dict)
          and p.get("intent") == "dispatch" and p.get("tool") == "launch_app",
          repr(p))

    # local_state envelope -> domain_type derived to 'internal'.
    p = _run("what's my cpu", json.dumps(
        {"intent": "agent", "refined_text": "report local cpu",
         "web": False, "news": False, "local_state": True}))
    check("refine.local_state_internal",
          p.get("local_state") is True and p.get("domain_type") == "internal",
          repr(p))

    # truncated-but-repairable envelope -> _loads_lenient structurally recovers
    # the plan (the 'parse_fail REPAIRED' path) instead of dropping the turn.
    p = _run("open epiphany",
             '{"intent": "dispatch", "refined_text": "open epiphany", '
             '"tool": "launch_app", "args": {"name": "epiphany"')
    check("refine.truncated_repaired", isinstance(p, dict)
          and p.get("intent") == "dispatch" and p.get("tool") == "launch_app",
          repr(p))

    # narrated prose with no recoverable JSON -> None (degrade-open to the legacy
    # router; the current lenient loader returns None rather than raising, so the
    # prose-salvage branch stays a no-op -- behaviour preserved verbatim).
    p = _run("open discord",
             "To open Discord I will launch_app(\"Discord\").")
    check("refine.prose_none", p is None, repr(p))

    # empty content -> None (degrade-open to the legacy router).
    p = _run("hello", "")
    check("refine.empty_content_none", p is None, repr(p))


# ---- routing cutoffs read from SSOT (configure() injection) ------------------
def t_cutoffs_ssot():
    # (A) Char cutoffs: injecting non-default values re-renders the prompt cues
    # AND moves the runtime promote gate (one SSOT constant feeds both).
    mr.configure(promote_chars=5, chat_chars=7, dispatch_chars=11)
    check("cutoffs.char_globals",
          mr.REFINE_PROMOTE_CHARS == 5 and mr.REFINE_CHAT_CHARS == 7
          and mr.REFINE_DISPATCH_CHARS == 11)
    check("cutoffs.prompt_cue_rerendered",
          "<7 chars" in mr._REFINE_SYSTEM and "<11 chars" in mr._REFINE_SYSTEM
          and ">5 chars" in mr._REFINE_SYSTEM, "cue numbers not re-rendered")
    # 9-char chat input now exceeds promote_chars=5 -> promoted to agent
    # (with the default 100 it would stay chat).
    p = _run("hey there", json.dumps(
        {"intent": "chat", "refined_text": "hey there", "reply": "Hi!",
         "web": False, "news": False, "local_state": False}))
    check("cutoffs.promote_gate_follows",
          isinstance(p, dict) and p.get("intent") == "agent", repr(p))

    # (B) Wordy-arg cutoff: a 2-word arg on a NON-fastpath dispatch promotes to
    # agent once the word cap drops to 1 (promote_chars high so length is inert).
    mr.configure(promote_chars=100, dispatch_arg_max_words=1)
    check("cutoffs.word_global", mr.REFINE_DISPATCH_ARG_MAX_WORDS == 1)
    p = _run("save this", json.dumps(
        {"intent": "dispatch", "tool": "remember", "args": {"text": "two words"},
         "web": False, "news": False, "local_state": False}))
    check("cutoffs.wordy_gate_follows",
          isinstance(p, dict) and p.get("intent") == "agent", repr(p))

    # Restore baselines so any later test ordering stays clean + assert the
    # default cues are byte-faithful (40/60/100).
    mr.configure(chat_chars=40, dispatch_chars=60, promote_chars=100,
                 dispatch_arg_max_words=3)
    check("cutoffs.restored_defaults",
          mr.REFINE_PROMOTE_CHARS == 100 and mr.REFINE_DISPATCH_ARG_MAX_WORDS == 3
          and "<40 chars" in mr._REFINE_SYSTEM and ">100 chars" in mr._REFINE_SYSTEM,
          "default cues not restored")


# ---- heavy-path critic->refiner (DCI critic gate) ----------------------------
def t_critic_refine():
    base_body = {"messages": [{"role": "user", "content": "hi"}]}
    long_raw = "x" * 600          # >= the default MIN_CHARS (500)
    revised = {"choices": [{"message": {"content": "REVISED ANSWER"}}]}
    cli = _CritClient(revised)
    # Inject the heavy-path knobs via the SAME configure() seam the server uses;
    # stub the session-event emitter + the DCI critic/trigger constants the module
    # imports from mios_dci (overridden on the module object for an isolated unit).
    mr.configure(critic_refine_enabled=True, critic_refine_max=1,
                 critic_refine_min_chars=500)
    mr._emit_session_event = lambda *a, **k: None
    mr.DCI_ENABLED = True
    mr.DCI_FLOW_TRIGGER_CONF = 0.7

    def _call(raw, critic_ret):
        async def _crit(*a, **k):
            return critic_ret
        mr.dci_critic_pass = _crit
        return asyncio.run(mr._critic_refine_agent(
            raw, "user question", {"intent": "agent"}, "sess-1",
            client=cli, target_endpoint="http://stub.local",
            headers={}, base_body=base_body))

    # (1) disabled -> raw passes through untouched (critic never consulted).
    mr.configure(critic_refine_enabled=False)
    check("critic.disabled_raw",
          _call(long_raw, {"act": "challenge", "confidence": 0.9}) == long_raw)
    mr.configure(critic_refine_enabled=True)

    # (2) too short (< MIN_CHARS) -> raw unchanged.
    check("critic.too_short_raw",
          _call("short answer", {"act": "challenge", "confidence": 0.9})
          == "short answer")

    # (3) critic satisfied -> raw stands (non-challenge act, None, AND low conf).
    check("critic.satisfied_affirm",
          _call(long_raw, {"act": "affirm", "confidence": 0.9}) == long_raw)
    check("critic.satisfied_none",
          _call(long_raw, None) == long_raw)
    check("critic.satisfied_lowconf",
          _call(long_raw, {"act": "challenge", "confidence": 0.3}) == long_raw)

    # (4) high-confidence challenge with a concern -> revised answer returned.
    out = _call(long_raw, {"act": "challenge", "confidence": 0.9,
                           "content": "you omitted X"})
    check("critic.revised_on_challenge", out == "REVISED ANSWER", repr(out))
    # empty concern -> no re-invoke, raw stands.
    check("critic.challenge_empty_concern",
          _call(long_raw, {"act": "ask", "confidence": 0.95, "content": "  "})
          == long_raw)


def main():
    _configure()
    t_salvage_corpus()
    t_refine_envelope()
    t_cutoffs_ssot()
    t_critic_refine()
    print(f"\n{'ALL PASS' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
