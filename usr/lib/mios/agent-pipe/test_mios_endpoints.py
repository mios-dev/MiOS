#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_endpoints (refactor R-wave leaf extraction). Pure stdlib, no server.py/DB/pytest. Pins the endpoint protocol/capability invariants that drive lane routing: _binding_api reads the per-engine then per-agent `api` field (case-folded); _endpoint_is_ollama / _endpoint_is_llamacpp / _endpoint_supports_tool_choice are CONFIG-FIRST (an `api`/`tool_choice` field wins) and otherwise fall back to env-SSOT host:port hint substrings; _endpoint_supports_parallel_tools is hint-only opt-in. Sets the MIOS_*_HINTS env vars BEFORE import so the module-load-time hint tuples are deterministic (independent of mios.toml [dispatch]). Guards the extracted leaf so a later move/refactor can't silently change which dialect/feature-set a lane is classified as.
# AI-related: ./mios_endpoints.py
# AI-functions: check, t_binding_api, t_is_ollama, t_tool_choice, t_parallel, t_is_llamacpp, main
"""Unit tests for mios_endpoints (refactor R-wave leaf)."""

import os
import sys

# Pin the env-SSOT hint tuples BEFORE import so the module-load-time constants are
# deterministic regardless of any mios.toml [dispatch] overrides on this host.
os.environ["MIOS_OLLAMA_API_HINTS"] = "11434,11435"
os.environ["MIOS_NO_TOOL_CHOICE_HINTS"] = "11436"
os.environ["MIOS_PARALLEL_TOOLS_HINTS"] = "11441"
os.environ["MIOS_KV_PAGING_HINTS"] = "11436"

import mios_endpoints as e  # noqa: E402

_fails = 0

# A generic OpenAI endpoint that contains NONE of the port hint substrings.
GENERIC = "http://core.example/v1"


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_binding_api():
    check("binding: top-level api, case-folded", e._binding_api({"api": "Ollama"}, None) == "ollama")
    check("binding: empty when absent", e._binding_api({}, None) == "")
    check("binding: engine api wins, engine key case-insensitive",
          e._binding_api({"engines": {"cpu": {"api": "OpenAI"}}}, "CPU") == "openai")
    check("binding: engine overrides top-level api",
          e._binding_api({"api": "openai", "engines": {"cpu": {"api": "ollama"}}}, "cpu") == "ollama")
    check("binding: falls back to top-level when engine has no api",
          e._binding_api({"api": "v1", "engines": {"cpu": {}}}, "cpu") == "v1")


def t_is_ollama():
    # CONFIG-FIRST: explicit api wins over any hint.
    check("ollama: api=ollama -> True", e._endpoint_is_ollama(GENERIC, {"api": "ollama"}) is True)
    check("ollama: api=native -> True", e._endpoint_is_ollama(GENERIC, {"api": "native"}) is True)
    check("ollama: api=openai overrides matching port hint",
          e._endpoint_is_ollama("http://h:11434/", {"api": "openai"}) is False)
    # Hint fallback (no api declared).
    check("ollama: default port hint -> True", e._endpoint_is_ollama("http://h:11434/api/chat", {}) is True)
    check("ollama: generic OpenAI endpoint -> False", e._endpoint_is_ollama(GENERIC, {}) is False)
    check("ollama: llamacpp port (11436) not an ollama hint -> False",
          e._endpoint_is_ollama("http://h:11436/v1", {}) is False)


def t_tool_choice():
    # llama.cpp 400s on tool_choice='required'.
    check("tool_choice: api=llamacpp -> False",
          e._endpoint_supports_tool_choice(GENERIC, {"api": "llamacpp"}) is False)
    check("tool_choice: explicit tool_choice=False -> False",
          e._endpoint_supports_tool_choice(GENERIC, {"tool_choice": False}) is False)
    check("tool_choice: per-engine tool_choice=False -> False",
          e._endpoint_supports_tool_choice(GENERIC, {"engines": {"ig": {"tool_choice": False}}}, "ig") is False)
    check("tool_choice: iGPU port hint (11436) -> False",
          e._endpoint_supports_tool_choice("http://h:11436/v1", {}) is False)
    check("tool_choice: generic OpenAI endpoint -> True",
          e._endpoint_supports_tool_choice(GENERIC, {}) is True)


def t_parallel():
    check("parallel: heavy-lane port hint (11441) -> True",
          e._endpoint_supports_parallel_tools("http://h:11441/v1") is True)
    check("parallel: generic endpoint -> False (sequential default)",
          e._endpoint_supports_parallel_tools(GENERIC) is False)
    check("parallel: light-lane port -> False",
          e._endpoint_supports_parallel_tools("http://h:11434/v1") is False)


def t_is_llamacpp():
    check("llamacpp: api=llamacpp -> True", e._endpoint_is_llamacpp(GENERIC, {"api": "llamacpp"}) is True)
    check("llamacpp: api=vulkan -> True", e._endpoint_is_llamacpp(GENERIC, {"api": "vulkan"}) is True)
    check("llamacpp: api=llama.cpp -> True", e._endpoint_is_llamacpp(GENERIC, {"api": "llama.cpp"}) is True)
    check("llamacpp: KV paging port hint (11436) -> True",
          e._endpoint_is_llamacpp("http://h:11436/v1", {}) is True)
    check("llamacpp: generic OpenAI endpoint -> False", e._endpoint_is_llamacpp(GENERIC, {}) is False)


def main():
    t_binding_api()
    t_is_ollama()
    t_tool_choice()
    t_parallel()
    t_is_llamacpp()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
