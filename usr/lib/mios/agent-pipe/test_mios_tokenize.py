# AI-hint: !/usr/bin/env python3 Standalone assert-script unit test for mios_tokenize (WS-A5 tokenizer seam). Pure stdlib, no server.py/DB/pytest.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_tokenize_py.md
"""Unit tests for mios_tokenize (WS-A5)."""

import json
import os
import sys
import types

import mios_tokenize as tok

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_count_parity():
    s = "hello world " * 17
    check("count_text == prior len//4", tok.count_text(s) == len(s) // 4, f"{tok.count_text(s)} vs {len(s)//4}")
    check("count_text empty -> 0", tok.count_text("") == 0)
    check("count_text None-safe", tok.count_text(None) == 0)
    check("backend_name is heuristic", tok.backend_name() == "heuristic-chars4")


def t_count_messages_parity():
    msgs = [{"role": "user", "content": "a" * 40}, {"role": "assistant", "content": "b" * 12}]
    tools = [{"type": "function", "function": {"name": "x"}}]
    expect = (sum(len(str(m.get("content") or "")) for m in msgs) + len(json.dumps(tools))) // 4
    check("count_messages == _fit_context //4 estimate",
          tok.count_messages(msgs, tools) == expect, f"{tok.count_messages(msgs, tools)} vs {expect}")
    check("count_messages no tools", tok.count_messages(msgs) == (40 + 12) // 4)
    check("count_messages empty -> 0", tok.count_messages([]) == 0)


def t_truncate():
    s = "x" * 1000
    check("truncate: 50 tokens == [:200] char slice",
          tok.truncate_to_tokens(s, 50) == s[:200])
    check("truncate: under budget unchanged", tok.truncate_to_tokens("short", 100) == "short")
    check("truncate: rstrips trailing space", not tok.truncate_to_tokens("a b " * 100, 10).endswith(" "))
    check("truncate: 0 tokens -> empty-ish", tok.truncate_to_tokens(s, 0) == "")
    big = "y" * 5000
    check("truncate: slow-lane block round-trips to 1500 chars",
          tok.truncate_to_tokens(big, 1500 // 4) == big[:1500])


def t_set_backend():
    class Double:
        chars_per_token = 2
        name = "double"
        def count(self, text):
            return len(text) // 2
    try:
        tok.set_backend(Double())
        check("set_backend: name swapped", tok.backend_name() == "double")
        check("set_backend: count uses new backend", tok.count_text("abcd") == 2)
        tok.set_backend(None)  # invalid -> ignored, keeps Double
        check("set_backend: None ignored (degrade-safe)", tok.backend_name() == "double")
    finally:
        tok.set_backend(mios_tokenize_default())


def t_usage_estimate():
    u = tok._usage_estimate("", "")
    check("usage: empty floors to 1/1/2",
          u.get("prompt_tokens") == 1 and u.get("completion_tokens") == 1 and u.get("total_tokens") == 2, str(u))
    u2 = tok._usage_estimate("a" * 40, "b" * 12)
    check("usage: counts via count_text (40//4, 12//4)",
          u2.get("prompt_tokens") == 10 and u2.get("completion_tokens") == 3 and u2.get("total_tokens") == 13, str(u2))


def mios_tokenize_default():
    return tok.HeuristicBackend()


class _FakeEnc:
    def encode(self, text, disallowed_special=None):
        return [ord(c) for c in str(text)]

    def decode(self, ids):
        return "".join(chr(i) for i in ids)


def _install_fake_tiktoken():
    mod = types.ModuleType("tiktoken")
    mod.get_encoding = lambda name: _FakeEnc()
    sys.modules["tiktoken"] = mod


class _FakeHFEncoding:
    def __init__(self, ids):
        self.ids = ids


class _FakeTokenizer:
    @classmethod
    def from_file(cls, path):
        t = cls()
        t._path = path
        return t

    def encode(self, text):
        return _FakeHFEncoding([ord(c) for c in str(text)])

    def decode(self, ids):
        return "".join(chr(i) for i in ids)


def _install_fake_tokenizers():
    mod = types.ModuleType("tokenizers")
    mod.Tokenizer = _FakeTokenizer
    sys.modules["tokenizers"] = mod


def t_make_backend_tiktoken():
    _install_fake_tiktoken()
    be = tok.make_backend("tiktoken", encoding="cl100k_base")
    check("make_backend tiktoken -> TiktokenBackend", isinstance(be, tok.TiktokenBackend))
    check("tiktoken: name reflects the encoding", be.name == "tiktoken-cl100k_base", be.name)
    check("tiktoken: count is exact (fake 1 token/char)", be.count("hello") == 5, str(be.count("hello")))
    check("tiktoken: truncate is token-EXACT", be.truncate("hello world", 5) == "hello",
          be.truncate("hello world", 5))
    check("tiktoken: truncate no-op under budget", be.truncate("hi", 10) == "hi")


def t_tiktoken_cache_dir_env():
    _install_fake_tiktoken()
    prior = os.environ.get("TIKTOKEN_CACHE_DIR")
    os.environ.pop("TIKTOKEN_CACHE_DIR", None)
    try:
        tok.make_backend("tiktoken", encoding="x", cache_dir="/baked/tt")
        check("tiktoken: SSOT cache_dir baked into TIKTOKEN_CACHE_DIR when unset (offline blob)",
              os.environ.get("TIKTOKEN_CACHE_DIR") == "/baked/tt", os.environ.get("TIKTOKEN_CACHE_DIR"))
    finally:
        if prior is None:
            os.environ.pop("TIKTOKEN_CACHE_DIR", None)
        else:
            os.environ["TIKTOKEN_CACHE_DIR"] = prior


def t_make_backend_hf():
    _install_fake_tokenizers()
    be = tok.make_backend("hf", path="/m/tokenizer.json")
    check("make_backend hf -> HFTokenizerBackend", isinstance(be, tok.HFTokenizerBackend))
    check("hf: name from the tokenizer.json basename", be.name == "hf-tokenizer.json", be.name)
    check("hf: count is exact", be.count("abc") == 3, str(be.count("abc")))
    check("hf: truncate token-exact", be.truncate("abcdef", 3) == "abc", be.truncate("abcdef", 3))


def t_make_backend_degrade_open():
    sys.modules.pop("tiktoken", None)
    check("make_backend tiktoken w/o dep -> None (degrade-open)",
          tok.make_backend("tiktoken", encoding="x") is None)
    sys.modules.pop("tokenizers", None)
    check("make_backend hf w/o dep -> None (degrade-open)",
          tok.make_backend("hf", path="/x") is None)
    check("make_backend unknown kind -> None", tok.make_backend("no_such_backend") is None)
    check("make_backend heuristic -> HeuristicBackend",
          isinstance(tok.make_backend("heuristic"), tok.HeuristicBackend))
    _install_fake_tiktoken()
    check("make_backend tiktoken w/o encoding -> None (no hardcoded encoding default)",
          tok.make_backend("tiktoken", encoding="") is None and tok.make_backend("tiktoken") is None)


def t_real_backend_measures_via_seam():
    _install_fake_tiktoken()
    be = tok.make_backend("tiktoken", encoding="x")
    try:
        tok.set_backend(be)
        check("seam: backend_name swapped to the real tokenizer", tok.backend_name() == "tiktoken-x")
        check("seam: count_text uses the tokenizer (1/char)", tok.count_text("hello") == 5)
        msgs = [{"role": "user", "content": "abc"}, {"role": "assistant", "content": "de"}]
        check("seam: count_messages routes through the tokenizer (not char//4)",
              tok.count_messages(msgs) == 5, str(tok.count_messages(msgs)))
        check("seam: truncate_to_tokens is token-exact via the backend",
              tok.truncate_to_tokens("hello world", 5) == "hello",
              tok.truncate_to_tokens("hello world", 5))
    finally:
        tok.set_backend(tok.HeuristicBackend())
        check("seam: restored heuristic after the real-backend test",
              tok.backend_name() == "heuristic-chars4")


def main():
    t_count_parity()
    t_count_messages_parity()
    t_truncate()
    t_set_backend()
    t_usage_estimate()
    t_make_backend_tiktoken()
    t_tiktoken_cache_dir_env()
    t_make_backend_hf()
    t_make_backend_degrade_open()
    t_real_backend_measures_via_seam()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
