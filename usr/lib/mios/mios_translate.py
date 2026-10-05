# AI-hint: Pure Python translation engine for loop.v1 events, Responses items, and cross-harness frame normalization.
# AI-related: usr/libexec/mios/mios-mcp-server, usr/share/mios/mios.toml [mcp], c:/-dev-loop/bridge/src/lib.rs
"""Pure Python translation engine for cross-harness frames, loop.v1 events and Responses items.

Normalizes frames from AGY, Claude, OpenAI Responses/Codex, and OpenAI Chat Completions
into ordered loop.v1 events and OpenAI Responses items. Enforces credential refusal,
gate evidence validation, and terminal envelope invariants.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

CREDENTIAL_KEYS = {
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "client_secret",
    "password",
    "private_key",
}

ANSI_PATTERN = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\].*?(?:\x1b\\|\x07))")


def strip_ansi(text: str) -> str:
    """Strip ANSI / VT100 / OSC escape sequences from terminal capture."""
    if not text:
        return ""
    return ANSI_PATTERN.sub("", text)


def extract_embedded_receipt(text: str) -> Optional[Dict[str, Any]]:
    """Extract an embedded JSON receipt (e.g. exitCode, output) from terminal text."""
    if not text:
        return None
    cleaned = strip_ansi(text)
    for match in re.finditer(r"\{[^{}]*\"exitCode\"\s*:\s*\d+[^{}]*\}", cleaned):
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict) and "exitCode" in parsed:
                return parsed
        except ValueError:
            continue
    for match in re.finditer(r"(\{.*\})", cleaned, re.DOTALL):
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and ("exitCode" in parsed or "status" in parsed):
                return parsed
        except ValueError:
            continue
    return None


def credential_key(value: Any) -> Optional[str]:
    """Recursively search for sensitive credential keys in a data structure."""
    if isinstance(value, dict):
        for k, v in value.items():
            norm = k.lower().replace("-", "_")
            if norm in CREDENTIAL_KEYS:
                return k
            found = credential_key(v)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = credential_key(item)
            if found:
                return found
    return None


def detect_source(frame: Dict[str, Any]) -> Optional[str]:
    """Sniff the wire dialect of a single frame."""
    if not isinstance(frame, dict):
        return None
    if "event" in frame:
        return "agy"
    if frame.get("object") == "response" or str(frame.get("type", "")).startswith("response."):
        return "openai"
    obj = frame.get("object")
    if obj in ("chat.completion", "chat.completion.chunk") or "tool_call_id" in frame or "tool_calls" in frame:
        return "openai_chat"
    kind = frame.get("type")
    if kind in ("result", "system", "assistant", "user"):
        if "message" in frame or "result" in frame or "is_error" in frame:
            return "claude"
    if kind in ("function_call", "function_call_output"):
        return "openai"
    if kind == "message":
        content = frame.get("content") or []
        if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") in ("output_text", "input_text") for b in content
        ):
            return "openai"
        if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "text" for b in content
        ):
            return "claude"
    return None


def _parse_arguments(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            raise ValueError("MALFORMED TOOL ARGUMENTS")
    return value if isinstance(value, dict) else {}


def _required_str(value: Dict[str, Any], key: str, context: str) -> str:
    res = value.get(key)
    if not res or not isinstance(res, str):
        raise ValueError(f"{context}: missing {key}")
    return res


def _agy(frame: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "event" not in frame and "status" in frame:
        return _agy({"event": "result", "result": frame})
    ev = frame.get("event")
    if ev == "init":
        return []
    if ev == "step_update":
        step = frame.get("step_update")
        if not isinstance(step, dict):
            raise ValueError("AGY STEP MISSING")
        st = step.get("step_type")
        if st == "agent_response":
            txt = step.get("text_delta")
            if txt:
                return [{"kind": "text", "role": "assistant", "text": txt}]
            return []
        if st == "tool" and step.get("state") == "DONE":
            info = step.get("tool_info") or {}
            call_id = step.get("call_id")
            if not call_id:
                idx = step.get("step_index", 0)
                conv = frame.get("conversation_id", "session")
                call_id = f"agy:{conv}:{idx}"
            name = step.get("tool_name") or info.get("name")
            if not name:
                raise ValueError("AGY TOOL NAME MISSING")
            args = info.get("parameters") or {}
            res = [{"kind": "tool_call", "call_id": call_id, "name": name, "arguments": args}]
            if "output" in info and info["output"] is not None:
                res.append({"kind": "tool_output", "call_id": call_id, "output": info["output"]})
            return res
        if st in ("tool", "subagent", "user_input", "system_message"):
            return []
        raise ValueError(f"AGY UNKNOWN STEP TYPE: {st}")
    if ev == "result":
        res = frame.get("result")
        if not isinstance(res, dict):
            raise ValueError("AGY RESULT MISSING")
        status = "delivered" if res.get("status") == "SUCCESS" else "errored"
        error = res.get("error")
        text = res.get("response") or ""
        return [{"kind": "terminal", "status": status, "text": text, "error": error}]
    raise ValueError(f"AGY UNKNOWN EVENT: {ev}")


def _claude(frame: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "type" not in frame and "result" in frame:
        wrapped = dict(frame)
        wrapped["type"] = "result"
        return _claude(wrapped)
    kind = frame.get("type")
    if kind == "system":
        return []
    if kind in ("assistant", "user"):
        msg = frame.get("message")
        if not isinstance(msg, dict):
            raise ValueError("CLAUDE MESSAGE MISSING")
        role = msg.get("role") or kind
        blocks = msg.get("content")
        if not isinstance(blocks, list):
            raise ValueError("CLAUDE CONTENT MISSING")
        events = []
        for b in blocks:
            btype = b.get("type")
            if btype == "text":
                txt = b.get("text")
                if txt is None:
                    raise ValueError("CLAUDE TEXT MISSING")
                events.append({"kind": "text", "role": role, "text": txt})
            elif btype == "tool_use":
                cid = b.get("id")
                name = b.get("name")
                if not cid:
                    raise ValueError("CLAUDE TOOL ID MISSING")
                if not name:
                    raise ValueError("CLAUDE TOOL NAME MISSING")
                events.append({"kind": "tool_call", "call_id": cid, "name": name, "arguments": b.get("input") or {}})
            elif btype == "tool_result":
                cid = b.get("tool_use_id")
                if not cid:
                    raise ValueError("CLAUDE TOOL RESULT ID MISSING")
                events.append({"kind": "tool_output", "call_id": cid, "output": b.get("content")})
            else:
                raise ValueError(f"CLAUDE UNKNOWN CONTENT: {btype}")
        return events
    if kind == "result":
        is_err = frame.get("is_error") is True
        text = frame.get("result") or ""
        error = text if is_err else None
        status = "errored" if is_err else "delivered"
        return [{"kind": "terminal", "status": status, "text": text if not is_err else "", "error": error}]
    raise ValueError(f"CLAUDE UNKNOWN EVENT: {kind}")


def _openai_item(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    kind = item.get("type")
    if kind == "message":
        role = item.get("role") or "assistant"
        blocks = item.get("content")
        if not isinstance(blocks, list):
            raise ValueError("RESPONSES MESSAGE CONTENT MISSING")
        events = []
        for b in blocks:
            btype = b.get("type")
            if btype in ("output_text", "input_text"):
                txt = b.get("text")
                if txt is None:
                    raise ValueError("RESPONSES TEXT MISSING")
                events.append({"kind": "text", "role": role, "text": txt})
            else:
                raise ValueError(f"RESPONSES UNKNOWN CONTENT: {btype}")
        return events
    if kind == "function_call":
        cid = item.get("call_id")
        name = item.get("name")
        if not cid:
            raise ValueError("RESPONSES CALL ID MISSING")
        if not name:
            raise ValueError("RESPONSES FUNCTION NAME MISSING")
        args = item.get("arguments")
        if args is None:
            raise ValueError("RESPONSES ARGUMENTS MISSING")
        return [{"kind": "tool_call", "call_id": cid, "name": name, "arguments": _parse_arguments(args)}]
    if kind == "function_call_output":
        cid = item.get("call_id")
        if not cid:
            raise ValueError("RESPONSES OUTPUT CALL ID MISSING")
        if "output" not in item:
            raise ValueError("RESPONSES OUTPUT MISSING")
        return [{"kind": "tool_output", "call_id": cid, "output": item["output"]}]
    raise ValueError(f"RESPONSES UNKNOWN ITEM: {kind}")


def _openai(frame: Dict[str, Any]) -> List[Dict[str, Any]]:
    if frame.get("object") == "response":
        output = frame.get("output")
        if not isinstance(output, list):
            raise ValueError("RESPONSES OUTPUT ARRAY MISSING")
        events = []
        for it in output:
            events.extend(_openai_item(it))
        has_err = bool(frame.get("error"))
        status = "delivered" if frame.get("status") == "completed" and not has_err else "errored"
        err_msg = frame.get("error", {}).get("message") if isinstance(frame.get("error"), dict) else None
        events.append({"kind": "terminal", "status": status, "text": "", "error": err_msg})
        return events
    kind = frame.get("type")
    if kind == "response.output_item.done":
        it = frame.get("item")
        if not isinstance(it, dict):
            raise ValueError("RESPONSES STREAM ITEM MISSING")
        return _openai_item(it)
    if kind in ("response.completed", "response.failed"):
        resp = frame.get("response") or {}
        has_err = kind == "response.failed" or bool(resp.get("error"))
        status = "errored" if has_err else "delivered"
        err_msg = resp.get("error", {}).get("message") if isinstance(resp.get("error"), dict) else None
        return [{"kind": "terminal", "status": status, "text": "", "error": err_msg}]
    if kind in ("response.output_item.added", "response.output_text.delta"):
        return []
    if kind in ("message", "function_call", "function_call_output"):
        return _openai_item(frame)
    raise ValueError(f"RESPONSES UNKNOWN EVENT: {kind}")


def _chat_message(frame: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    role = frame.get("role")
    if role == "tool":
        cid = frame.get("tool_call_id") or ""
        events.append({"kind": "tool_output", "call_id": cid, "output": frame.get("content")})
        return events
    content = frame.get("content")
    if content:
        events.append({"kind": "text", "role": role or "assistant", "text": str(content)})
    tool_calls = frame.get("tool_calls")
    if isinstance(tool_calls, list):
        for call in tool_calls:
            fn = call.get("function")
            if not isinstance(fn, dict):
                raise ValueError("CHAT TOOL FUNCTION MISSING")
            cid = call.get("id")
            if not cid:
                raise ValueError("CHAT TOOL ID MISSING")
            name = fn.get("name")
            if not name:
                raise ValueError("CHAT TOOL NAME MISSING")
            if "arguments" not in fn:
                raise ValueError("CHAT ARGUMENTS MISSING")
            args = _parse_arguments(fn["arguments"])
            events.append({"kind": "tool_call", "call_id": cid, "name": name, "arguments": args})
    return events


def _openai_chat(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    pending: List[Optional[Dict[str, Any]]] = []

    def flush():
        for slot in pending:
            if slot is not None:
                if not slot.get("id") or not slot.get("name"):
                    raise ValueError("CHAT STREAM TOOL ID OR NAME MISSING")
                full_args = "".join(slot["arguments_fragments"])
                parsed_args = _parse_arguments(full_args if full_args else "{}")
                events.append({
                    "kind": "tool_call",
                    "call_id": slot["id"],
                    "name": slot["name"],
                    "arguments": parsed_args,
                })
        pending.clear()

    for frame in frames:
        obj = frame.get("object")
        if obj == "chat.completion":
            flush()
            choices = frame.get("choices") or []
            for choice in choices:
                msg = choice.get("message") or {}
                events.extend(_chat_message(msg))
                fr = choice.get("finish_reason")
                if fr in ("stop", "tool_calls"):
                    events.append({"kind": "terminal", "status": "delivered", "text": "", "error": None})
                elif fr:
                    events.append({"kind": "terminal", "status": "errored", "text": "", "error": f"CHAT FINISH REASON: {fr}"})
        elif obj == "chat.completion.chunk":
            choices = frame.get("choices") or []
            for choice in choices:
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    events.append({"kind": "text", "role": delta.get("role") or "assistant", "text": str(content)})
                tool_calls = delta.get("tool_calls")
                if isinstance(tool_calls, list):
                    for call in tool_calls:
                        idx = call.get("index", 0)
                        if idx > 255:
                            raise ValueError("CHAT TOOL INDEX OUT OF RANGE")
                        while len(pending) <= idx:
                            pending.append(None)
                        if pending[idx] is None:
                            pending[idx] = {"id": "", "name": "", "arguments_fragments": []}
                        slot = pending[idx]
                        if call.get("id"):
                            slot["id"] = call["id"]
                        fn = call.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["arguments_fragments"].append(fn["arguments"])
                fr = choice.get("finish_reason")
                if fr:
                    flush()
                    if fr in ("stop", "tool_calls"):
                        events.append({"kind": "terminal", "status": "delivered", "text": "", "error": None})
                    else:
                        events.append({"kind": "terminal", "status": "errored", "text": "", "error": f"CHAT FINISH REASON: {fr}"})
        else:
            flush()
            events.extend(_chat_message(frame))

    flush()
    return events


def responses_items(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Project loop.v1 events into OpenAI Responses items."""
    items = []
    for ev in events:
        k = ev.get("kind")
        if k == "text":
            role = ev.get("role", "assistant")
            content_type = "output_text" if role == "assistant" else "input_text"
            items.append({
                "type": "message",
                "role": role,
                "content": [{"type": content_type, "text": ev.get("text", "")}],
            })
        elif k == "tool_call":
            items.append({
                "type": "function_call",
                "call_id": ev.get("call_id", ""),
                "name": ev.get("name", ""),
                "arguments": json.dumps(ev.get("arguments", {}), ensure_ascii=False),
            })
        elif k == "tool_output":
            items.append({
                "type": "function_call_output",
                "call_id": ev.get("call_id", ""),
                "output": ev.get("output"),
            })
    return items


def translate(request: Dict[str, Any]) -> Dict[str, Any]:
    """Translate frames into loop.v1 events and Responses items."""
    if not isinstance(request, dict):
        raise ValueError("INVALID TRANSLATE REQUEST")
    source_raw = request.get("source", "")
    frames = request.get("frames")
    if not isinstance(frames, list):
        raise ValueError("INVALID TRANSLATE REQUEST: frames must be a list")

    known = {
        "auto", "agy", "claude", "openai", "openai_responses", "codex",
        "openai_chat", "chat_completions", "openai_compatible", "generic",
    }
    if source_raw not in known:
        raise ValueError(f"UNKNOWN SOURCE: {source_raw}")

    # Credential key check across all frames
    for f in frames:
        key = credential_key(f)
        if key:
            raise ValueError(f"CREDENTIAL FIELD REFUSED: {key}")

    if source_raw == "auto":
        detected = None
        for f in frames:
            detected = detect_source(f)
            if detected:
                break
        if not detected:
            raise ValueError("AUTO DETECTION FAILED: no known frame shape")
        source = detected
    else:
        source = source_raw

    # Dialect translation
    if source in ("openai_chat", "chat_completions", "openai_compatible", "generic"):
        events = _openai_chat(frames)
    elif source == "agy":
        events = []
        for f in frames:
            events.extend(_agy(f))
    elif source == "claude":
        events = []
        for f in frames:
            events.extend(_claude(f))
    elif source in ("openai", "openai_responses", "codex"):
        events = []
        for f in frames:
            events.extend(_openai(f))
    else:
        raise ValueError(f"UNKNOWN SOURCE: {source}")

    # Ensure at least one Text event exists
    if not any(ev.get("kind") == "text" for ev in events):
        for ev in reversed(events):
            if ev.get("kind") == "terminal" and ev.get("text"):
                t_idx = next((i for i, e in enumerate(events) if e.get("kind") == "terminal"), len(events))
                events.insert(t_idx, {"kind": "text", "role": "assistant", "text": ev["text"]})
                break

    # Ensure terminal envelope
    if not any(ev.get("kind") == "terminal" for ev in events):
        events.append({"kind": "terminal", "status": "errored", "text": "", "error": "MISSING TERMINAL ENVELOPE"})

    # Denied action check
    denied = any(
        bool((f.get("result") or f).get("denied_actions") or (f.get("result") or f).get("permission_denials"))
        for f in frames if isinstance(f, dict)
    )

    evidence = request.get("evidence")
    for ev in events:
        if ev.get("kind") == "terminal" and ev.get("status") == "delivered":
            if denied:
                ev["status"] = "refused"
            elif evidence is not None:
                if evidence.get("timed_out"):
                    ev["status"] = "timed_out"
                elif evidence.get("exit_code", 0) != 0:
                    ev["status"] = "errored"
                elif not evidence.get("tree_restored", True):
                    ev["status"] = "control_invalid"
                elif not evidence.get("positive") or not evidence.get("negative"):
                    ev["status"] = "gate_failed"
                elif evidence.get("diff_bytes", 0) == 0:
                    ev["status"] = "vacuous"
                else:
                    ev["status"] = "delivered"
            else:
                ev["status"] = "unverified"

    return {
        "schema": "loop.v1",
        "events": events,
        "responses_items": responses_items(events),
    }
