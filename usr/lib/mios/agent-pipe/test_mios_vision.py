# AI-hint: Stdlib assert-script for mios_vision (refactor R9). Covers the two
#   load-bearing branches with stubs (no network/DB): the VISION honest-error gate
#   (_vision_complete returns an honest "vision unavailable" turn when no model is
#   provisioned -- never a raw 5xx or fabricated description; _vision_backend_failed
#   classifies a degraded backend), and the CLIENT-TOOLS handback (_client_tools_loop
#   returns a non-MiOS tool_call assistant message unchanged; _client_tools_wrap shapes
#   finish_reason=tool_calls).
# AI-related: mios_vision.py, mios_native_loop.py
"""Stdlib assert-script for mios_vision (refactor R9).

Covers the two load-bearing branches of the extracted module with stubs (no
network / no DB):

  1. the VISION honest-error gate -- with NO vision model provisioned,
     ``_vision_complete`` returns an HONEST "vision unavailable" assistant turn
     (never a raw 5xx, never a fabricated description); ``_vision_backend_failed``
     classifies a degraded backend correctly.
  2. the CLIENT-TOOLS tool_call handback -- when the model emits a CLIENT
     (non-MiOS) tool_call, ``_client_tools_loop`` hands the whole assistant
     message back UNCHANGED for the caller to execute, and ``_client_tools_wrap``
     shapes it with finish_reason=tool_calls.
"""

import asyncio
import json

import mios_vision


# ── 1. VISION honest-error gate ────────────────────────────────────
def test_vision_unavailable_no_fabrication() -> None:
    # No VLM provisioned (default VISION_MODEL == "").
    mios_vision.configure(vision_model="")
    resp = asyncio.run(mios_vision._vision_complete(
        {"messages": [{"role": "user", "content": "what's in this image?"}]},
        False, "chatcmpl-test", "mios-vision"))
    body = json.loads(bytes(resp.body).decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    # Honest 'can't read images' turn -- NOT a fabricated description.
    assert content == mios_vision._VISION_UNAVAILABLE_MSG, content
    assert "can't read images" in content, content
    assert body["choices"][0]["finish_reason"] == "stop"
    print("ok: vision unavailable -> honest assistant turn, no fabrication")


def test_vision_backend_failed_classifier() -> None:
    # 5xx and llama-swap "model absent" leaf errors -> the VLM did NOT run.
    assert mios_vision._vision_backend_failed(503, "") is True
    assert mios_vision._vision_backend_failed(
        200, "exited prematurely") is True
    assert mios_vision._vision_backend_failed(
        200, "image inputs are not supported") is True
    # A real 200 reply -> NOT a failure (don't mask a genuine answer).
    assert mios_vision._vision_backend_failed(200, "a cat on a mat") is False
    print("ok: _vision_backend_failed classifies degraded backends")


def test_messages_have_image() -> None:
    assert mios_vision._messages_have_image(
        [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:..."}}]}]) is True
    assert mios_vision._messages_have_image(
        [{"role": "user", "content": "plain text"}]) is False
    print("ok: _messages_have_image detects vision content")


# ── 2. CLIENT-TOOLS tool_call handback ─────────────────────────────
def test_client_tools_handback_shape() -> None:
    # Stub every injected dep so no network/DB is touched.
    async def _select_child_tools(surface, intent, cap):
        return []

    mios_vision.configure(
        agent_contract=lambda: "",            # no SOUL contract in the test
        verb_catalog={},                      # empty -> no MiOS surface merged
        resolve_verb_key=lambda name: name,   # identity resolver
        select_child_tools=_select_child_tools,
        default_tool_cap=8,
    )

    # The backend emits a CLIENT (non-MiOS) tool_call -- browser_back is NOT in
    # the (empty) verb catalog, so the loop must HAND IT BACK unchanged.
    handback = {"role": "assistant", "content": "",
                "tool_calls": [{"id": "call_x", "type": "function",
                                "function": {"name": "browser_back",
                                             "arguments": "{}"}}]}

    async def _stub_backend(req):
        return {"choices": [{"message": handback}]}

    orig = mios_vision._client_tools_backend
    mios_vision._client_tools_backend = _stub_backend
    try:
        body = {"messages": [{"role": "user", "content": "go back"}],
                "tools": [{"type": "function",
                           "function": {"name": "browser_back"}}]}
        msg = asyncio.run(mios_vision._client_tools_loop(
            body, {"browser_back"}, "chatcmpl-ct"))
    finally:
        mios_vision._client_tools_backend = orig

    # The client tool_call rides back verbatim (same name, not executed here).
    assert msg.get("tool_calls"), msg
    assert msg["tool_calls"][0]["function"]["name"] == "browser_back", msg

    wrapped = mios_vision._client_tools_wrap(msg, "chatcmpl-ct", "mios")
    assert wrapped["object"] == "chat.completion"
    assert wrapped["choices"][0]["finish_reason"] == "tool_calls", wrapped
    assert wrapped["choices"][0]["message"] is msg
    print("ok: client-tools client tool_call handed back, wrap shape correct")


def test_client_tools_is_mios_gate() -> None:
    # A name absent from the catalog is NOT server-executable (rides back);
    # a name present IS server-executable.
    mios_vision.configure(verb_catalog={"open_app": {}},
                          resolve_verb_key=lambda name: name)
    assert mios_vision._client_tools_is_mios("open_app", set()) is True
    assert mios_vision._client_tools_is_mios("browser_back", set()) is False
    assert mios_vision._client_tools_is_mios("", set()) is False
    print("ok: _client_tools_is_mios gates server-side vs handback")


def test_client_tools_sse_relays_tool_calls() -> None:
    msg = {"role": "assistant", "content": "",
           "tool_calls": [{"id": "c1", "type": "function",
                           "function": {"name": "browser_back",
                                        "arguments": "{}"}}]}

    async def _collect():
        out = []
        async for chunk in mios_vision._client_tools_sse(msg, "cid", "mios"):
            out.append(chunk.decode("utf-8"))
        return "".join(out)

    blob = asyncio.run(_collect())
    assert "browser_back" in blob, blob
    assert "tool_calls" in blob and '"finish_reason": "tool_calls"' in blob, blob
    assert blob.rstrip().endswith("[DONE]"), blob
    print("ok: _client_tools_sse relays tool_calls + [DONE]")


if __name__ == "__main__":
    test_vision_unavailable_no_fabrication()
    test_vision_backend_failed_classifier()
    test_messages_have_image()
    test_client_tools_handback_shape()
    test_client_tools_is_mios_gate()
    test_client_tools_sse_relays_tool_calls()
    print("\nALL mios_vision tests passed")
