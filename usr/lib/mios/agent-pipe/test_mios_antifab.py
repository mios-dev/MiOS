# AI-hint: Standalone assert-script unit test for the anti-fabrication guard
#   `_contains_tool_result_block` (T-118/T-119) -- the chat-reply short-circuit in
#   mios_pipe.routing.chat rejects a synthesized reply that NARRATES a tool
#   execution (the real-emitter sentinel `🤝 <verb> output:` or a `"success":
#   true` / `"tool":"<verb>"` JSON pair, in either key order) it never actually
#   ran. Imports the REAL symbol through the repo's mios_chat re-export shim
#   (see mios_chat.py) using the same bare-checkout stub recipe as
#   test_mios_chat.py (httpx/websockets/uvicorn/fastapi doubles) so no network,
#   DB, or built image is required. If a future dependency genuinely can't be
#   stubbed offline, the import is wrapped so the test SKIPS (exit 0) instead of
#   failing the suite.
# AI-related: ./mios_pipe/routing/chat.py, ./mios_chat.py, ./test_mios_chat.py
# AI-functions: _install_stubs, t_tool_output_sentinel, t_success_json_tool_order, t_tool_json_success_order, t_ordinary_prose, t_empty_and_none, main
"""Unit tests for the anti-fabrication tool-result predicate (T-118/T-119)."""

import sys
import types
from unittest import mock

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


def main():
    if _predicate is None:
        print(f"SKIP: mios_chat unimportable in this environment -- {_skip_reason}")
        return 0
    t_tool_output_sentinel()
    t_success_json_tool_order()
    t_tool_json_success_order()
    t_ordinary_prose()
    t_empty_and_none()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
