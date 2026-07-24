# AI-hint: Remote multi-provider adapter module. Normalizes OpenAI Chat Completions requests for remote [nodes.*] bindings declaring api='anthropic'|'gemini' and translates their responses back into standard OpenAI Chat Completion format via provider_translate. Pure module, never imports server.py.
"""Remote provider adapter for cross-provider node escalation (OpenAI <-> Anthropic / Gemini)."""

from __future__ import annotations

import sys
import os
from typing import Any, Callable, Awaitable

# Ensure agent-pipe path is accessible for imports
_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _base not in sys.path:
    sys.path.insert(0, _base)

from mios_pipe.routing.provider_translate import (
    oai_tools_to_anthropic,
    oai_msgs_to_anthropic,
    anthropic_resp_to_oai,
    oai_tools_to_gemini,
    oai_msgs_to_gemini,
    gemini_resp_to_oai,
)


async def call_remote(
    node_cfg: dict[str, Any],
    oai_request: dict[str, Any],
    transport: Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    """Adapt and issue a chat completion request to a remote node endpoint.

    If node_cfg['api'] is 'anthropic' or 'gemini', translates request format and
    translates provider response back to OpenAI Chat Completion format.
    Otherwise (openai / unset / unknown), passes the request through directly.
    """
    api = str((node_cfg or {}).get("api") or "openai").strip().lower()

    if api == "anthropic":
        system_str, anth_msgs = oai_msgs_to_anthropic(oai_request.get("messages") or [])
        payload: dict[str, Any] = {
            "messages": anth_msgs,
            "max_tokens": oai_request.get("max_tokens") or 1024,
        }
        if system_str:
            payload["system"] = system_str
        tools = oai_request.get("tools")
        if tools:
            anth_tools = oai_tools_to_anthropic(tools)
            if anth_tools:
                payload["tools"] = anth_tools
        if "temperature" in oai_request:
            payload["temperature"] = oai_request["temperature"]
        if "model" in oai_request:
            payload["model"] = oai_request["model"]

        resp_raw = await transport(node_cfg, payload)
        return anthropic_resp_to_oai(resp_raw)

    elif api == "gemini":
        sys_inst, gem_contents = oai_msgs_to_gemini(oai_request.get("messages") or [])
        payload: dict[str, Any] = {
            "contents": gem_contents,
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst
        tools = oai_request.get("tools")
        if tools:
            gem_tools = oai_tools_to_gemini(tools)
            if gem_tools:
                payload["tools"] = gem_tools
        cfg: dict[str, Any] = {}
        if "temperature" in oai_request:
            cfg["temperature"] = oai_request["temperature"]
        if "max_tokens" in oai_request:
            cfg["maxOutputTokens"] = oai_request["max_tokens"]
        if cfg:
            payload["generationConfig"] = cfg

        resp_raw = await transport(node_cfg, payload)
        return gemini_resp_to_oai(resp_raw)

    else:
        # OpenAI or standard passthrough
        return await transport(node_cfg, oai_request)
