#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_refine (refactor R5 REFINE-classifier extraction). Pure stdlib, no server.py/DB/network/pytest.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_refine_py.md
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


def t_salvage_corpus():
    d = mr._salvage_refine_dispatch(
        'Sure, here is the plan: '
        '{"intent":"dispatch","tool":"open_url","args":{"url":"https://x.com"}}')
    check("salvage.embedded_json", isinstance(d, dict)
          and d.get("intent") == "dispatch" and d.get("tool") == "open_url",
          repr(d))

    d = mr._salvage_refine_dispatch(
        'To open Discord on your desktop, I will launch_app("Discord PTB").')
    check("salvage.verb_call_quoted", isinstance(d, dict)
          and d.get("tool") == "launch_app"
          and (d.get("args") or {}).get("name") == "Discord PTB"
          and d.get("_salvaged") is True, repr(d))

    d = mr._salvage_refine_dispatch(
        'I will now call open_url(url="https://wikipedia.org") for you.')
    check("salvage.kv_args", isinstance(d, dict) and d.get("tool") == "open_url"
          and (d.get("args") or {}).get("url") == "https://wikipedia.org", repr(d))

    d = mr._salvage_refine_dispatch("focus_window(Forza)")
    check("salvage.bare_positional", isinstance(d, dict)
          and d.get("tool") == "focus_window"
          and (d.get("args") or {}).get("name") == "Forza", repr(d))

    d = mr._salvage_refine_dispatch("Running launch_verified(Steam) next.")
    check("salvage.longest_first", isinstance(d, dict)
          and d.get("tool") == "launch_verified", repr(d))

    d = mr._salvage_refine_dispatch("I'm sorry, I can't help with that request.")
    check("salvage.pure_prose_none", d is None, repr(d))

    check("salvage.empty_none", mr._salvage_refine_dispatch("") is None)


def _run(user_text, body):
    _FAKE.body = {"choices": [{"message": {"content": body}}]}
    return asyncio.run(mr.refine_intent(user_text, None))


def t_refine_envelope():
    p = _run("hey there", json.dumps(
        {"intent": "chat", "refined_text": "hey there", "reply": "Hi!",
         "web": False, "news": False, "local_state": False}))
    check("refine.chat_intent", isinstance(p, dict) and p.get("intent") == "chat",
          repr(p))
    check("refine.metadata_stamped",
          p.get("_model") == "test-refine" and "_elapsed_s" in p, repr(p))
    check("refine.bools_strict", p.get("web") is False and p.get("news") is False
          and p.get("local_state") is False, repr(p))

    p = _run("latest news on X", "```json\n" + json.dumps(
        {"intent": "agent", "refined_text": "latest news on X",
         "web": True, "news": "true", "local_state": False}) + "\n```")
    check("refine.fenced_agent", isinstance(p, dict) and p.get("intent") == "agent",
          repr(p))
    check("refine.web_true", p.get("web") is True, repr(p))
    check("refine.news_str_coerced", p.get("news") is True, repr(p))

    p = _run("open epiphany", "<think>the user wants a launch</think>" + json.dumps(
        {"intent": "dispatch", "refined_text": "open epiphany",
         "tool": "launch_app", "args": {"name": "epiphany"},
         "web": False, "news": False, "local_state": False}))
    check("refine.think_stripped", isinstance(p, dict)
          and p.get("intent") == "dispatch" and p.get("tool") == "launch_app",
          repr(p))

    p = _run("what's my cpu", json.dumps(
        {"intent": "agent", "refined_text": "report local cpu",
         "web": False, "news": False, "local_state": True}))
    check("refine.local_state_internal",
          p.get("local_state") is True and p.get("domain_type") == "internal",
          repr(p))

    p = _run("open epiphany",
             '{"intent": "dispatch", "refined_text": "open epiphany", '
             '"tool": "launch_app", "args": {"name": "epiphany"')
    check("refine.truncated_repaired", isinstance(p, dict)
          and p.get("intent") == "dispatch" and p.get("tool") == "launch_app",
          repr(p))

    p = _run("open discord",
             "To open Discord I will launch_app(\"Discord\").")
    check("refine.prose_none", p is None, repr(p))

    p = _run("hello", "")
    check("refine.empty_content_none", p is None, repr(p))


def t_cutoffs_ssot():
    mr.configure(promote_chars=5, chat_chars=7, dispatch_chars=11)
    check("cutoffs.char_globals",
          mr.REFINE_PROMOTE_CHARS == 5 and mr.REFINE_CHAT_CHARS == 7
          and mr.REFINE_DISPATCH_CHARS == 11)
    check("cutoffs.prompt_cue_rerendered",
          "<7 chars" in mr._REFINE_SYSTEM and "<11 chars" in mr._REFINE_SYSTEM
          and ">5 chars" in mr._REFINE_SYSTEM, "cue numbers not re-rendered")
    p = _run("hey there", json.dumps(
        {"intent": "chat", "refined_text": "hey there", "reply": "Hi!",
         "web": False, "news": False, "local_state": False}))
    check("cutoffs.promote_gate_follows",
          isinstance(p, dict) and p.get("intent") == "agent", repr(p))

    mr.configure(promote_chars=100, dispatch_arg_max_words=1)
    check("cutoffs.word_global", mr.REFINE_DISPATCH_ARG_MAX_WORDS == 1)
    p = _run("save this", json.dumps(
        {"intent": "dispatch", "tool": "remember", "args": {"text": "two words"},
         "web": False, "news": False, "local_state": False}))
    check("cutoffs.wordy_gate_follows",
          isinstance(p, dict) and p.get("intent") == "agent", repr(p))

    mr.configure(chat_chars=40, dispatch_chars=60, promote_chars=100,
                 dispatch_arg_max_words=3)
    check("cutoffs.restored_defaults",
          mr.REFINE_PROMOTE_CHARS == 100 and mr.REFINE_DISPATCH_ARG_MAX_WORDS == 3
          and "<40 chars" in mr._REFINE_SYSTEM and ">100 chars" in mr._REFINE_SYSTEM,
          "default cues not restored")


def t_critic_refine():
    base_body = {"messages": [{"role": "user", "content": "hi"}]}
    long_raw = "x" * 600          # >= the default MIN_CHARS (500)
    revised = {"choices": [{"message": {"content": "REVISED ANSWER"}}]}
    cli = _CritClient(revised)
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

    mr.configure(critic_refine_enabled=False)
    check("critic.disabled_raw",
          _call(long_raw, {"act": "challenge", "confidence": 0.9}) == long_raw)
    mr.configure(critic_refine_enabled=True)

    check("critic.too_short_raw",
          _call("short answer", {"act": "challenge", "confidence": 0.9})
          == "short answer")

    check("critic.satisfied_affirm",
          _call(long_raw, {"act": "affirm", "confidence": 0.9}) == long_raw)
    check("critic.satisfied_none",
          _call(long_raw, None) == long_raw)
    check("critic.satisfied_lowconf",
          _call(long_raw, {"act": "challenge", "confidence": 0.3}) == long_raw)

    out = _call(long_raw, {"act": "challenge", "confidence": 0.9,
                           "content": "you omitted X"})
    check("critic.revised_on_challenge", out == "REVISED ANSWER", repr(out))
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
