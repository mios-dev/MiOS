#!/usr/bin/env python3
# AI-hint: Offline unit test for the mios-a2a-test loopback smoke-test helper -- exercises the pure message-builder, artifact extractor, and task classifier with stub A2A Task dicts (no network, no live services), mirroring the stub-based agent-pipe test style.
# AI-related: /usr/libexec/mios/mios-a2a-test
# AI-functions: _load_tester, test_build_message, test_extract_artifact_text, test_classify_task, main
"""Offline tests for T-066 (A2A federation loopback smoke test).

The network/CLI half of mios-a2a-test needs a live agent-pipe; the pure
protocol helpers (build_message / extract_artifact_text / classify_task) are
exercised here with stub Task payloads so the round-trip's shape logic is
guarded without any live service.
"""
import importlib.machinery
import importlib.util
import os
import sys

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _load_tester():
    # Resolve the extension-less CLI relative to this test so it loads on the
    # image (/usr/libexec/...), a WSL checkout, or a Windows checkout alike.
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    path = os.path.join(repo, "usr", "libexec", "mios", "mios-a2a-test")
    # The CLI has no .py suffix, so give spec loading an explicit source loader.
    loader = importlib.machinery.SourceFileLoader("mios_a2a_test", path)
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("mios_a2a_test", loader))
    loader.exec_module(mod)
    return mod


def test_build_message(T):
    m = T.build_message("hello", "ctx-1", "mid-1")
    check("message has user role", m["role"] == "user")
    check("message carries one text part",
          m["parts"] == [{"kind": "text", "text": "hello"}])
    check("message threads contextId", m.get("contextId") == "ctx-1")
    check("message carries messageId", m.get("messageId") == "mid-1")
    m2 = T.build_message("x", "", "mid-2")
    check("absent contextId omitted (not empty-string)", "contextId" not in m2)


def test_extract_artifact_text(T):
    task_art = {"artifacts": [{"parts": [{"kind": "text", "text": "the answer"}]}]}
    check("artifact text extracted", T.extract_artifact_text(task_art) == "the answer")
    task_hist = {"artifacts": [], "history": [
        {"role": "user", "parts": [{"kind": "text", "text": "q"}]},
        {"role": "agent", "parts": [{"kind": "text", "text": "fallback reply"}]},
    ]}
    check("falls back to last agent history text",
          T.extract_artifact_text(task_hist) == "fallback reply")
    check("empty task -> empty string", T.extract_artifact_text({}) == "")


def test_classify_task(T):
    good = {"id": "t1", "contextId": "c1",
            "status": {"state": "completed"},
            "artifacts": [{"parts": [{"kind": "text", "text": "done"}]}]}
    v = T.classify_task(good)
    check("completed+artifact => completed", v["completed"] is True)
    check("completed+artifact => has_artifact", v["has_artifact"] is True)
    check("task_id surfaced", v["task_id"] == "t1")
    check("context_id surfaced", v["context_id"] == "c1")

    working = {"id": "t2", "status": {"state": "working"}, "artifacts": []}
    v2 = T.classify_task(working)
    check("non-completed state not marked completed", v2["completed"] is False)
    check("no artifact => has_artifact False", v2["has_artifact"] is False)

    no_art = {"id": "t3", "status": {"state": "completed"}, "artifacts": []}
    v3 = T.classify_task(no_art)
    check("completed but artifact-less flagged", v3["has_artifact"] is False)


def main():
    T = _load_tester()
    test_build_message(T)
    test_extract_artifact_text(T)
    test_classify_task(T)
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
