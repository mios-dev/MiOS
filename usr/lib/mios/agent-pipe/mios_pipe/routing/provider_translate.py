# AI-hint: Pure cross-provider wire-format adapter extracted from server.py (refactor WS R2 leaf wave). MiOS's internal contract is OpenAI Chat Completions; an agent binding may declare api='anthropic'|'gemini', and this layer normalises tools, messages, and responses BOTH directions so alternative-provider endpoints are drop-in ("entire stacks to OpenAI standards for UNIVERSAL MODEL compatibility"). Invariants: OpenAI `arguments` is a JSON STRING while Anthropic `input` / Gemini `args` are OBJECTS; call-id correlation; results are messages; JSON-Schema scrub (drop top-level $ref/$schema/additionalProperties, force Gemini array items.type, relocate provider-rejected keywords into description). Self-contained pure functions -- only dependency is mios_jsonsalvage.loads_lenient (lenient JSON parse of model-emitted argument strings) + stdlib json. server.py re-imports every name under its original _-prefixed alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_jsonsalvage.py, ./mios_interop.py, ./test_mios_provider_translate.py
# AI-functions: scrub_schema, oai_tools_to_anthropic, oai_tools_to_gemini, args_obj, oai_msgs_to_anthropic, anthropic_resp_to_oai, oai_msgs_to_gemini, gemini_resp_to_oai
"""OpenAI <-> Anthropic/Gemini wire-format translation (model-adapter gateway).

Extracted verbatim from ``server.py`` (model-adapter gateway, item #1 slice 4).
Every function is pure and side-effect-free; ``server.py`` imports them back under
their original ``_``-prefixed names so the module's public surface is unchanged.
"""

from __future__ import annotations

import json

from mios_jsonsalvage import loads_lenient as _loads_lenient

# Providers reject/ignore several JSON-Schema keywords and choke on $ref/$schema;
# Gemini additionally needs array items to declare a type. Relocated keywords go
# into the field description so the model still sees the constraint as guidance.
ANTH_REJECT_KEYS = ("$schema", "$ref", "additionalProperties")
GEMINI_DROP_KEYS = ("format", "minLength", "maxLength", "pattern",
                    "minimum", "maximum", "default", "examples",
                    "additionalProperties", "$schema", "$ref")


def scrub_schema(node, *, gemini: bool):
    """Return a provider-safe copy of a JSON-Schema node. Some providers reject/ignore
    several keywords (relocated into description) and REQUIRE array items to
    declare a type; both providers choke on $ref/$schema. Recursive, copy-only."""
    if isinstance(node, list):
        return [scrub_schema(n, gemini=gemini) for n in node]
    if not isinstance(node, dict):
        return node
    out: dict = {}
    moved: list = []
    drop = GEMINI_DROP_KEYS if gemini else ANTH_REJECT_KEYS
    for k, v in node.items():
        if k in drop:
            if gemini and k in ("format", "pattern", "minLength", "maxLength",
                                "minimum", "maximum"):
                moved.append(f"{k}={v}")
            continue
        if k in ("properties",) and isinstance(v, dict):
            out[k] = {pk: scrub_schema(pv, gemini=gemini) for pk, pv in v.items()}
        elif k in ("items", "additionalItems"):
            out[k] = scrub_schema(v, gemini=gemini)
        elif k in ("anyOf", "allOf", "oneOf") and isinstance(v, list):
            out[k] = [scrub_schema(n, gemini=gemini) for n in v]
        else:
            out[k] = v
    if gemini and out.get("type") == "array":
        it = out.get("items")
        if not isinstance(it, dict) or "type" not in it:
            out["items"] = {**(it if isinstance(it, dict) else {}), "type": "string"}
    if moved:
        out["description"] = (str(out.get("description") or "")
                              + " (" + "; ".join(moved) + ")").strip()
    return out


def oai_tools_to_anthropic(tools: list) -> list:
    out = []
    for t in (tools or []):
        fn = (t.get("function") if isinstance(t, dict) else None) or {}
        name = str(fn.get("name") or "").strip()
        if not name:
            continue
        out.append({"name": name,
                    "description": str(fn.get("description") or ""),
                    "input_schema": scrub_schema(
                        fn.get("parameters") or {"type": "object", "properties": {}},
                        gemini=False)})
    return out


def oai_tools_to_gemini(tools: list) -> list:
    decls = []
    for t in (tools or []):
        fn = (t.get("function") if isinstance(t, dict) else None) or {}
        name = str(fn.get("name") or "").strip()
        if not name:
            continue
        decls.append({"name": name,
                      "description": str(fn.get("description") or ""),
                      "parameters": scrub_schema(
                          fn.get("parameters") or {"type": "object", "properties": {}},
                          gemini=True)})
    return [{"functionDeclarations": decls}] if decls else []


def args_obj(args) -> dict:
    """OpenAI tool-call arguments (a JSON STRING) -> object for Claude/Gemini."""
    if isinstance(args, str):
        try:
            args = _loads_lenient(args)
        except Exception:  # noqa: BLE001
            args = {}
    return args if isinstance(args, dict) else {}


def oai_msgs_to_anthropic(msgs: list) -> tuple:
    """OpenAI messages -> (system_str, anthropic_messages). system messages fold
    into the top-level `system` param; assistant.tool_calls -> tool_use blocks;
    role:tool -> a user message with a tool_result block (tool_use_id linked)."""
    system_parts: list = []
    out: list = []
    for m in (msgs or []):
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(str(m["content"]))
        elif role == "tool":
            out.append({"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id") or m.get("name") or "",
                "content": str(m.get("content") or "")}]})
        elif role == "assistant":
            blocks: list = []
            if m.get("content"):
                blocks.append({"type": "text", "text": str(m["content"])})
            for tc in (m.get("tool_calls") or []):
                fn = tc.get("function") or {}
                blocks.append({"type": "tool_use", "id": tc.get("id") or "",
                               "name": fn.get("name") or "",
                               "input": args_obj(fn.get("arguments"))})
            out.append({"role": "assistant",
                        "content": blocks or [{"type": "text", "text": ""}]})
        else:  # user / anything else
            out.append({"role": "user",
                        "content": [{"type": "text", "text": str(m.get("content") or "")}]})
    return "\n\n".join(system_parts), out


def anthropic_resp_to_oai(resp: dict) -> dict:
    """Anthropic Messages response -> OpenAI assistant message {content,
    tool_calls}. tool_use blocks -> tool_calls[] with arguments as a JSON STRING."""
    text_parts: list = []
    tool_calls: list = []
    for block in (resp.get("content") or []):
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text_parts.append(str(block.get("text") or ""))
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id") or f"call{len(tool_calls)}",
                "type": "function",
                "function": {"name": block.get("name") or "",
                             "arguments": json.dumps(block.get("input") or {},
                                                     ensure_ascii=False)}})
    msg: dict = {"role": "assistant", "content": "".join(text_parts)}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def oai_msgs_to_gemini(msgs: list) -> tuple:
    """OpenAI messages -> (system_instruction|None, gemini contents[]). roles:
    user->user, assistant->model, tool->user(functionResponse). tool_calls ->
    functionCall parts; tool results -> functionResponse parts."""
    system_parts: list = []
    contents: list = []
    for m in (msgs or []):
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(str(m["content"]))
        elif role == "tool":
            contents.append({"role": "user", "parts": [{"functionResponse": {
                "name": m.get("name") or m.get("tool_call_id") or "tool",
                "response": {"result": str(m.get("content") or "")}}}]})
        elif role == "assistant":
            parts: list = []
            if m.get("content"):
                parts.append({"text": str(m["content"])})
            for tc in (m.get("tool_calls") or []):
                fn = tc.get("function") or {}
                parts.append({"functionCall": {"name": fn.get("name") or "",
                                               "args": args_obj(fn.get("arguments"))}})
            contents.append({"role": "model", "parts": parts or [{"text": ""}]})
        else:
            contents.append({"role": "user",
                             "parts": [{"text": str(m.get("content") or "")}]})
    si = {"parts": [{"text": "\n\n".join(system_parts)}]} if system_parts else None
    return si, contents


def gemini_resp_to_oai(resp: dict) -> dict:
    """Gemini generateContent response -> OpenAI assistant message."""
    cand = (resp.get("candidates") or [{}])[0] or {}
    parts = ((cand.get("content") or {}).get("parts")) or []
    text_parts: list = []
    tool_calls: list = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        if "text" in p:
            text_parts.append(str(p.get("text") or ""))
        elif "functionCall" in p:
            fc = p.get("functionCall") or {}
            tool_calls.append({
                "id": f"call{len(tool_calls)}", "type": "function",
                "function": {"name": fc.get("name") or "",
                             "arguments": json.dumps(fc.get("args") or {},
                                                     ensure_ascii=False)}})
    msg: dict = {"role": "assistant", "content": "".join(text_parts)}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg
