# AI-hint: Standalone assert-script unit test for the anti-fabrication guard AI-related: ./mios_pipe/routing/chat.py, ./mios_chat.py, ./test_mios_chat.py AI-...
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for the anti-fabrication tool-result predicate (T-118/T-119)."""

import os
import sys
import types
from unittest import mock

os.environ["MIOS_ANTIFAB_ENABLE"] = "false"

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def _install_stubs():
    """Minimal 3rd-party stand-ins so mios_chat (and the sibling graph it imports)
    loads on a bare checkout -- same recipe as test_mios_chat.py's _install_stubs."""
    for name in ("httpx", "websockets", "uvicorn"):
        sys.modules.setdefault(name, mock.MagicMock(name=name))
    fastapi = types.ModuleType("fastapi")

    class _App:
        def __getattr__(self, _attr):
            def _factory(*_a, **_k):
                def _wrap(fn=None):
                    return fn if fn is not None else (lambda f: f)
                return _wrap
            return _factory

    class _FakeRequest:
        pass

    fastapi.FastAPI = lambda *a, **k: _App()
    fastapi.APIRouter = lambda *a, **k: _App()
    fastapi.Request = _FakeRequest
    fastapi.WebSocket = object
    responses = types.ModuleType("fastapi.responses")

    class _Resp:
        def __init__(self, *a, **k):
            pass

    responses.JSONResponse = type("JSONResponse", (_Resp,), {})
    responses.StreamingResponse = type("StreamingResponse", (_Resp,), {})
    for _c in ("HTMLResponse", "RedirectResponse", "Response", "PlainTextResponse"):
        setattr(responses, _c, type(_c, (_Resp,), {}))
    fastapi.responses = responses
    sys.modules.setdefault("fastapi", fastapi)
    sys.modules.setdefault("fastapi.responses", responses)

_predicate = None
_skip_reason = None
try:
    _install_stubs()
    import mios_chat
    _predicate = mios_chat._contains_tool_result_block
except Exception as exc:  # pragma: no cover -- offline-env fallback, not duplicated logic
    _skip_reason = f"{type(exc).__name__}: {exc}"

_NL = None
_nl_skip = None
try:
    _install_stubs()
    import mios_pipe.routing.native_loop as _NL
except Exception as exc:  # pragma: no cover -- offline-env fallback
    _nl_skip = f"{type(exc).__name__}: {exc}"

def t_tool_output_sentinel():
    out = _predicate("🤝 open_app output: {\"path\": \"/tmp\"}")
    check("sentinel: '🤝 <verb> output:' -> True", out is True, out)

def t_success_json_tool_order():
    out = _predicate('{"success": true, "tool": "launch_app"}')
    check("json(success,tool order): -> True", out is True, out)

def t_tool_json_success_order():
    out = _predicate('{"tool": "launch_app", "success": true}')
    check("json(tool,success order): -> True", out is True, out)

def t_ordinary_prose():
    out = _predicate("Sure, I can help you open that application.")
    check("ordinary prose -> False", out is False, out)

def t_empty_and_none():
    check("empty string -> False", _predicate("") is False)
    check("None -> False", _predicate(None) is False)

_FAB01_SYNTH = (
    "Here are the games installed on your system:\n\n"
    "🤝 apps output (truncated for brevity):\n"
    '{"success": true, "tool": "apps", "apps": ['
    '{"name": "example-app-1", "version": "unknown"}, '
    '{"name": "example-app-2", "version": "unknown"}, '
    '{"name": "example-app-3", "version": "unknown"}, '
    '{"name": "example-app-4", "version": "unknown"}]}'
)

def t_fab01_synth_strips_fired_verb_block():
    ans = _NL._guard_fabricated_execution(
        _FAB01_SYNTH, surfaced_raw_evidence=False, m2=[], enable=True)
    check("FAB-01: fabricated '🤝 apps output' block stripped (fired-membership "
          "does NOT save it)", "🤝" not in ans and "example-app-1" not in ans, ans)
    check("FAB-01: real synthesized prose survives the strip",
          ans.strip().startswith("Here are the games installed"), ans)

def t_fab01_raw_evidence_provenance():
    real_blk = '{"success": true, "tool": "open_app", "pid": 4242}'
    m2 = [{"role": "tool", "name": "open_app", "content": real_blk}]
    keep = _NL._guard_fabricated_execution(
        real_blk, surfaced_raw_evidence=True, m2=m2, enable=True)
    check("FAB-01 raw path: success-JSON matching real _m2 output PRESERVED",
          keep.strip() == real_blk, keep)
    fake_blk = '{"success": true, "tool": "open_app", "pid": 9999}'
    drop = _NL._guard_fabricated_execution(
        fake_blk, surfaced_raw_evidence=True, m2=m2, enable=True)
    check("FAB-01 raw path: NON-matching success-JSON stripped",
          "9999" not in drop, drop)

def t_fab01_skill_recipe_subsumed():
    ans = ("You can do that with a recipe.\n\n"
           "🤝 skill:foo output: {\"steps\": 3}")
    out = _NL._guard_fabricated_execution(
        ans, surfaced_raw_evidence=False, m2=[], enable=True)
    check("FAB-01: skill/recipe sentinel in synthesized prose stripped "
          "(false-positive subsumed)", "🤝" not in out, out)

_FAB02_CORPUS = (
    "In 2024, notable releases included Prince of Persia: The Lost Crown, a "
    "Metroidvania from Ubisoft Montpellier, and Eiyuden Chronicle: Hundred Heroes, "
    "a spiritual successor to Suikoden. Source: Wikipedia, Polygon."
)
_FAB02_ANS = (
    "## Notable 2024 Games\n\n"
    "Prince of Persia: The Lost Crown launched in January 2024, and Eiyuden "
    "Chronicle: Hundred Heroes followed. Both were widely covered by Polygon.\n\n"
    "## Major 2025 Announcements\n\n"
    "Starfield Shattered Space DLC, FIFA 26, and a God of War Ragnarok expansion "
    "were unveiled, according to IGN, though not captured in the excerpt."
)

def t_fab02_strips_only_ungrounded_section():
    out = _NL._guard_entity_grounding(
        _FAB02_ANS, _FAB02_CORPUS, gate=True, enable=True,
        min_entities=3, ground_min=0.34, note="(unverified omitted)")
    check("FAB-02: fabricated 2025 section stripped",
          "Starfield" not in out and "FIFA 26" not in out and "Ragnarok" not in out, out)
    check("FAB-02: grounded 2024 section survives",
          "Prince of Persia" in out and "Eiyuden Chronicle" in out, out)
    check("FAB-02: honest note appended", "(unverified omitted)" in out, out)

def t_fab02_all_grounded_untouched():
    grounded = ("## Notable 2024 Games\n\nPrince of Persia: The Lost Crown and "
                "Eiyuden Chronicle: Hundred Heroes released in 2024 per Polygon.")
    out = _NL._guard_entity_grounding(
        grounded, _FAB02_CORPUS, gate=True, enable=True,
        min_entities=3, ground_min=0.34, note="(unverified omitted)")
    check("FAB-02: fully grounded answer untouched", out == grounded, out)

def t_fab02_degrade_open():
    out = _NL._guard_entity_grounding(
        _FAB02_ANS, "", gate=True, enable=True,
        min_entities=3, ground_min=0.34, note="(unverified omitted)")
    check("FAB-02: empty corpus degrades-open (byte-identical)", out == _FAB02_ANS, out)
    cjk = "## 概要\n\nこれは日本語のテキストです。ゲームについて。\n\n## 続き\n\nもっと日本語。"
    out2 = _NL._guard_entity_grounding(
        cjk, _FAB02_CORPUS, gate=True, enable=True,
        min_entities=3, ground_min=0.34, note="(unverified omitted)")
    check("FAB-02: caseless/CJK answer degrades-open (byte-identical)", out2 == cjk, out2)

def t_flag_off_passthrough():
    check("gate: native-loop _ANTIFAB_ENABLE reflects env=false",
          _NL._ANTIFAB_ENABLE is False, _NL._ANTIFAB_ENABLE)
    ex = _NL._guard_fabricated_execution(
        _FAB01_SYNTH, surfaced_raw_evidence=False, m2=[], enable=_NL._ANTIFAB_ENABLE)
    check("gate: FAB-01 guard passthrough when disabled (byte-identical)",
          ex == _FAB01_SYNTH, ex)
    gr = _NL._guard_entity_grounding(
        _FAB02_ANS, _FAB02_CORPUS, gate=True, enable=_NL._ANTIFAB_ENABLE,
        min_entities=3, ground_min=0.34, note="(unverified omitted)")
    check("gate: FAB-02 guard passthrough when disabled (byte-identical)",
          gr == _FAB02_ANS, gr)

def main():
    if _predicate is None:
        print(f"SKIP: mios_chat unimportable in this environment -- {_skip_reason}")
        return 0
    t_tool_output_sentinel()
    t_success_json_tool_order()
    t_tool_json_success_order()
    t_ordinary_prose()
    t_empty_and_none()
    if _NL is None:
        print(f"SKIP: native_loop unimportable in this environment -- {_nl_skip}")
    else:
        t_fab01_synth_strips_fired_verb_block()
        t_fab01_raw_evidence_provenance()
        t_fab01_skill_recipe_subsumed()
        t_fab02_strips_only_ungrounded_section()
        t_fab02_all_grounded_untouched()
        t_fab02_degrade_open()
        t_flag_off_passthrough()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0

if __name__ == "__main__":
    sys.exit(main())
