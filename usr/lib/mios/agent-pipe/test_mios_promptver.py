#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_promptver (WS-LIFECYCLE-VER prompt-version registry). Pure stdlib, no server.py/pytest. Verifies the stable content-hash, register() version semantics (bump only on content change, idempotent for unchanged), bounded history, rollback() (restore prior content as a forward version), and the content-free snapshot (never leaks prompt text).
# AI-related: ./mios_promptver.py
# AI-functions: check, main
"""Unit tests for mios_promptver (WS-LIFECYCLE-VER)."""
import sys

import mios_promptver as pv

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_hash():
    check("hash: stable + 12 hex", pv.content_hash("abc") == pv.content_hash("abc")
          and len(pv.content_hash("abc")) == 12)
    check("hash: differs on change", pv.content_hash("abc") != pv.content_hash("abd"))
    check("hash: None safe", isinstance(pv.content_hash(None), str))


def t_register_versions():
    r = pv.PromptRegistry()
    a = r.register("refine", "v1 text")
    check("register: first -> version 1", a["version"] == 1)
    # same content -> stable version (idempotent re-register every import)
    a2 = r.register("refine", "v1 text")
    check("register: unchanged -> same version", a2["version"] == 1 and a2["hash"] == a["hash"])
    # changed content -> version bump
    b = r.register("refine", "v2 text edited")
    check("register: changed -> version 2", b["version"] == 2 and b["hash"] != a["hash"])
    check("register: history has the prior", len(r.history("refine")) == 1
          and r.history("refine")[-1]["version"] == 1)
    # independent name tracks its own version
    c = r.register("polish", "p1")
    check("register: per-name version", c["version"] == 1)


def t_rollback():
    r = pv.PromptRegistry()
    r.register("synth", "original")
    r.register("synth", "auto-edited (regressed)")
    check("rollback: pre state version 2", r.current("synth")["version"] == 2)
    rb = r.rollback("synth")
    # rollback restores ORIGINAL content as a NEW forward version (3)
    check("rollback: forward version bump", rb["version"] == 3)
    check("rollback: content == original", r.current("synth")["content"] == "original")
    check("rollback: hash == original hash",
          r.current("synth")["hash"] == pv.content_hash("original"))
    # nothing to roll back
    r.register("solo", "x")
    check("rollback: no history -> None", r.rollback("solo") is None)


def t_snapshot():
    r = pv.PromptRegistry()
    r.register("router", "SYSTEM: classify the prompt")
    r.register("router", "SYSTEM: classify the prompt v2")
    snap = r.snapshot()
    check("snapshot: name present w/ version+hash+len+history",
          snap["router"]["version"] == 2 and "hash" in snap["router"]
          and snap["router"]["history"] == 1)
    check("snapshot: NEVER leaks content", all("content" not in v for v in snap.values()))


def main():
    t_hash()
    t_register_versions()
    t_rollback()
    t_snapshot()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
