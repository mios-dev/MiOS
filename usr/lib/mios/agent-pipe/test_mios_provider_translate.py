#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_provider_translate (refactor WS R2 leaf extraction). Pure stdlib, no server.py/DB/pytest. Pins the OpenAI<->Anthropic/Gemini wire-format invariants that make alternative-provider endpoints drop-in: schema scrub drops $ref/$schema/additionalProperties (both) and relocates Gemini-rejected keywords (format/min*/max*/pattern) into description + forces array items.type; OpenAI tool arguments (JSON STRING) round-trip to Anthropic input / Gemini args OBJECTS and back to a JSON STRING; system messages fold to the top-level system param; assistant.tool_calls -> tool_use/functionCall and role:tool -> tool_result/functionResponse with id correlation. Guards the extracted leaf so a later move/refactor can't silently change provider wire shapes.
# AI-related: ./mios_provider_translate.py
# AI-functions: check, t_scrub, t_tools, t_args_obj, t_msgs_anthropic, t_resp_anthropic, t_msgs_gemini, t_resp_gemini, main
"""Unit tests for mios_provider_translate (refactor R2)."""

import json
import sys

import mios_provider_translate as p

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_scrub():
    schema = {
        "type": "object", "$schema": "x", "additionalProperties": False,
        "properties": {
            "n": {"type": "integer", "minimum": 1, "maximum": 9, "format": "int32"},
            "tags": {"type": "array"},  # gemini: must gain items.type
            "ref": {"$ref": "#/x"},
        },
    }
    a = p.scrub_schema(schema, gemini=False)
    check("scrub/anth: drops $schema", "$schema" not in a)
    check("scrub/anth: drops additionalProperties", "additionalProperties" not in a)
    check("scrub/anth: keeps minimum (not a reject key)", a["properties"]["n"].get("minimum") == 1)
    check("scrub/anth: drops $ref in nested", "$ref" not in a["properties"]["ref"])
    g = p.scrub_schema(schema, gemini=True)
    n = g["properties"]["n"]
    check("scrub/gem: drops format/minimum/maximum", all(k not in n for k in ("format", "minimum", "maximum")))
    check("scrub/gem: relocates into description", "format=int32" in (n.get("description") or ""), n)
    check("scrub/gem: forces array items.type", g["properties"]["tags"].get("items", {}).get("type") == "string")
    check("scrub: copy-only (input unmutated)", "$schema" in schema)


def t_tools():
    tools = [{"type": "function", "function": {"name": "f", "description": "d",
                                               "parameters": {"type": "object", "properties": {}}}},
             {"type": "function", "function": {"name": "", "parameters": {}}}]  # nameless dropped
    a = p.oai_tools_to_anthropic(tools)
    check("tools/anth: one tool, nameless dropped", len(a) == 1 and a[0]["name"] == "f")
    check("tools/anth: has input_schema", "input_schema" in a[0])
    g = p.oai_tools_to_gemini(tools)
    check("tools/gem: functionDeclarations wrapper", g and "functionDeclarations" in g[0])
    check("tools/gem: one decl", len(g[0]["functionDeclarations"]) == 1)
    check("tools/gem: empty -> []", p.oai_tools_to_gemini([]) == [])


def t_args_obj():
    check("args: JSON string -> object", p.args_obj('{"a": 1}') == {"a": 1})
    check("args: dict passthrough", p.args_obj({"b": 2}) == {"b": 2})
    check("args: bad JSON -> {}", p.args_obj("not json") == {})
    check("args: non-str/dict -> {}", p.args_obj(5) == {})


def t_msgs_anthropic():
    msgs = [{"role": "system", "content": "S"},
            {"role": "user", "content": "U"},
            {"role": "assistant", "content": "A", "tool_calls": [
                {"id": "c1", "function": {"name": "f", "arguments": '{"x":1}'}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "R"}]
    system, out = p.oai_msgs_to_anthropic(msgs)
    check("msgs/anth: system folded", system == "S")
    check("msgs/anth: user message", out[0] == {"role": "user", "content": [{"type": "text", "text": "U"}]})
    asst = out[1]
    check("msgs/anth: assistant tool_use block", any(b.get("type") == "tool_use" and b["name"] == "f" for b in asst["content"]))
    check("msgs/anth: tool_use input is OBJECT", asst["content"][-1]["input"] == {"x": 1})
    check("msgs/anth: tool_result linked by id", out[2]["content"][0]["tool_use_id"] == "c1")


def t_resp_anthropic():
    resp = {"content": [{"type": "text", "text": "hi"},
                        {"type": "tool_use", "id": "t1", "name": "f", "input": {"y": 2}}]}
    m = p.anthropic_resp_to_oai(resp)
    check("resp/anth: content text", m["content"] == "hi")
    check("resp/anth: tool_calls present", m["tool_calls"][0]["function"]["name"] == "f")
    check("resp/anth: arguments is JSON STRING", json.loads(m["tool_calls"][0]["function"]["arguments"]) == {"y": 2})


def t_msgs_gemini():
    msgs = [{"role": "system", "content": "S"},
            {"role": "assistant", "tool_calls": [{"function": {"name": "f", "arguments": '{"x":1}'}}]},
            {"role": "tool", "name": "f", "content": "R"}]
    si, contents = p.oai_msgs_to_gemini(msgs)
    check("msgs/gem: system_instruction", si == {"parts": [{"text": "S"}]})
    check("msgs/gem: assistant -> model role", contents[0]["role"] == "model")
    check("msgs/gem: functionCall args OBJECT", contents[0]["parts"][-1]["functionCall"]["args"] == {"x": 1})
    check("msgs/gem: tool -> functionResponse", "functionResponse" in contents[1]["parts"][0])


def t_resp_gemini():
    resp = {"candidates": [{"content": {"parts": [
        {"text": "hi"}, {"functionCall": {"name": "f", "args": {"z": 3}}}]}}]}
    m = p.gemini_resp_to_oai(resp)
    check("resp/gem: content text", m["content"] == "hi")
    check("resp/gem: tool_calls name", m["tool_calls"][0]["function"]["name"] == "f")
    check("resp/gem: arguments is JSON STRING", json.loads(m["tool_calls"][0]["function"]["arguments"]) == {"z": 3})


def main():
    t_scrub()
    t_tools()
    t_args_obj()
    t_msgs_anthropic()
    t_resp_anthropic()
    t_msgs_gemini()
    t_resp_gemini()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
