#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_sse (refactor WS R2 leaf extraction). Pure stdlib, no server.py/DB/pytest/FastAPI. Pins the OpenAI-streaming SSE wire shapes the whole pipe streams on: _sse_chunk emits `data: {json}\n\n` with a chat.completion.chunk delta and dual reasoning_content+reasoning fields; _sse_done is the [DONE] sentinel; _sse_status emits a content-empty mios_status pill AND (when STATUS_AS_REASONING + real content) a persistent reasoning line, suppressing bare contentless markers; _sse_status_phase resolves _HUMAN_LABELS; _stream_answer char-paces the answer byte-for-byte; _iter_answer_chunks splits at word boundaries (whitespace preserved, oversize tokens whole); _tail_latest_status lifts the newest hermes-tail event into a status chunk. Guards the extracted streaming layer against silent wire-shape drift.
# AI-related: ./mios_sse.py
# AI-functions: check, _decode, t_chunk, t_done, t_status, t_status_phase, t_stream_answer, t_tail, t_iter_chunks, main
"""Unit tests for mios_sse (refactor R2)."""

import asyncio
import json
import os
import sys
import tempfile

import mios_sse as e

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _decode(b):
    """`data: {json}\\n\\n` -> the parsed chunk dict."""
    s = b.decode("utf-8")
    assert s.startswith("data: ") and s.endswith("\n\n"), s
    return json.loads(s[len("data: "):].strip())


def t_chunk():
    c = _decode(e._sse_chunk("hello", chat_id="cid", model="m", role="assistant"))
    check("chunk: object type", c["object"] == "chat.completion.chunk")
    check("chunk: id+model", c["id"] == "cid" and c["model"] == "m")
    check("chunk: content delta", c["choices"][0]["delta"]["content"] == "hello")
    check("chunk: role", c["choices"][0]["delta"]["role"] == "assistant")
    r = _decode(e._sse_chunk(None, chat_id="cid", model="m", reasoning="thinking"))
    d = r["choices"][0]["delta"]
    check("chunk: dual reasoning fields", d.get("reasoning_content") == "thinking" and d.get("reasoning") == "thinking")
    check("chunk: mios_status passthrough",
          _decode(e._sse_chunk("", chat_id="c", model="m", mios_status={"emoji": "x"})).get("mios_status") == {"emoji": "x"})


def t_done():
    check("done: [DONE] sentinel", e._sse_done() == b"data: [DONE]\n\n")


def t_status():
    b = e._sse_status(chat_id="c", model="m", emoji="🔎", label="search", detail="cats")
    c = _decode(b)
    st = c["mios_status"]
    check("status: payload emoji/label/done", st["emoji"] == "🔎" and st["done"] is False)
    check("status: detail appended to label", "cats" in st["label"] and st.get("detail") == "cats")
    # with content + STATUS_AS_REASONING, a reasoning line persists
    if e.STATUS_AS_REASONING:
        check("status: persists reasoning when content", c["choices"][0]["delta"].get("reasoning_content"))
    # a BARE contentless marker (no label, no detail) must NOT persist reasoning
    bare = _decode(e._sse_status(chat_id="c", model="m", emoji="👂", label="", detail=None))
    check("status: bare marker no reasoning", not bare["choices"][0]["delta"].get("reasoning_content"))
    check("status: bare marker still a pill", bare.get("mios_status", {}).get("emoji") == "👂")


def t_status_phase():
    c = _decode(e._sse_status_phase(chat_id="c", model="m", phase="tool"))
    check("phase: known phase emoji from _HUMAN_LABELS", c["mios_status"]["emoji"] == e._HUMAN_LABELS["tool"][0])
    c2 = _decode(e._sse_status_phase(chat_id="c", model="m", phase="nope"))
    check("phase: unknown -> fallback glyph", c2["mios_status"]["emoji"] == "·")


def t_stream_answer():
    os.environ["MIOS_ANSWER_CHUNK_CHARS"] = "4"
    out = []
    async def run():
        async for b in e._stream_answer("abcdefgh", chat_id="c", model="m"):
            out.append(_decode(b)["choices"][0]["delta"]["content"])
    asyncio.run(run())
    check("stream: char-exact reassembly", "".join(out) == "abcdefgh", "".join(out))
    check("stream: chunked by size", out == ["abcd", "efgh"], str(out))
    empty = []
    async def run2():
        async for b in e._stream_answer("", chat_id="c", model="m"):
            empty.append(b)
    asyncio.run(run2())
    check("stream: empty -> nothing", empty == [])


def t_tail():
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"events": [{"ts": 10, "kind": "tool_call", "detail": "ran X"},
                                  {"ts": 20, "kind": "subagent_done", "detail": "done Y"}]}, fh)
        e._HERMES_TAIL_PATH = path  # point at the fixture
        chunk, new_ts = e._tail_latest_status(0.0, chat_id="c", model="m")
        check("tail: advances to newest ts", new_ts == 20)
        st = _decode(chunk)["mios_status"]
        check("tail: emoji from kind map", st["emoji"] == e._TAIL_KIND_EMOJI["subagent_done"])
        check("tail: detail carried", st.get("detail") == "done Y")
        none_chunk, ts2 = e._tail_latest_status(20.0, chat_id="c", model="m")
        check("tail: nothing newer -> (None, ts)", none_chunk is None and ts2 == 20.0)
    finally:
        os.unlink(path)


def t_iter_chunks():
    # size<=0 or text shorter than size -> a single chunk (whole text)
    check("iter: size<=0 -> one chunk", list(e._iter_answer_chunks("hello world", 0)) == ["hello world"])
    check("iter: text<=size -> one chunk", list(e._iter_answer_chunks("hi", 8)) == ["hi"])
    # splits at WORD boundaries, never mid-word; whitespace preserved
    out = list(e._iter_answer_chunks("alpha beta gamma delta", 8))
    check("iter: lossless reassembly", "".join(out) == "alpha beta gamma delta", str(out))
    check("iter: word-boundary chunks (whitespace kept)",
          out == ["alpha ", "beta ", "gamma ", "delta"], str(out))
    # a single token longer than size is emitted whole (no mid-word cut)
    big = list(e._iter_answer_chunks("supercalifragilistic", 5))
    check("iter: oversize token emitted whole", big == ["supercalifragilistic"], str(big))
    # empty text -> one empty chunk
    check("iter: empty text -> ['']", list(e._iter_answer_chunks("", 4)) == [""])


def main():
    t_chunk()
    t_done()
    t_status()
    t_status_phase()
    t_stream_answer()
    t_tail()
    t_iter_chunks()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
