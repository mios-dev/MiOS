# AI-hint: !/usr/bin/env python3 Standalone assert-script unit test for mios_endpoints (refactor R-wave leaf extraction). Pure stdlib, no server.py/DB/pytest.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_endpoints_py.md
"""Unit tests for mios_endpoints (refactor R-wave leaf)."""

import os
import sys

os.environ["MIOS_NO_TOOL_CHOICE_HINTS"] = "11436"
os.environ["MIOS_PARALLEL_TOOLS_HINTS"] = "11441"
os.environ["MIOS_KV_PAGING_HINTS"] = "11436"

import mios_endpoints as e  # noqa: E402

_fails = 0

GENERIC = "http://core.example/v1"


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_binding_api():
    check("binding: top-level api, case-folded", e._binding_api({"api": "Llamacpp"}, None) == "llamacpp")
    check("binding: empty when absent", e._binding_api({}, None) == "")
    check("binding: engine api wins, engine key case-insensitive",
          e._binding_api({"engines": {"cpu": {"api": "OpenAI"}}}, "CPU") == "openai")
    check("binding: engine overrides top-level api",
          e._binding_api({"api": "openai", "engines": {"cpu": {"api": "vllm"}}}, "cpu") == "vllm")
    check("binding: falls back to top-level when engine has no api",
          e._binding_api({"api": "v1", "engines": {"cpu": {}}}, "cpu") == "v1")


def t_tool_choice():
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
    t_tool_choice()
    t_parallel()
    t_is_llamacpp()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
