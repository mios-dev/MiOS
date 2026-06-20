#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_memory (WS-A15 MemoryProvider seam). Pure stdlib + asyncio, no server.py / DB / pytest -- runs as `python3 test_mios_memory.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Uses an injected FakeBackend (records recall/insert calls) to prove the PgVectorMemoryProvider forwards retrieve/add VERBATIM (golden parity vs the old direct mios_pg calls), and that get_memory_provider is fail-CLOSED (ValueError on an unknown name) + register_provider works.
# AI-related: ./mios_memory.py
# AI-functions: check, main, class FakeBackend
"""Unit tests for mios_memory (WS-A15)."""

import asyncio
import sys

import mios_memory as mem

_fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))


class FakeBackend:
    """Stands in for mios_pg: records the exact (args, kwargs) of each call."""

    def __init__(self):
        self.recall_calls = []
        self.insert_calls = []

    async def recall(self, qvec, **kw):
        self.recall_calls.append((qvec, kw))
        return [{"score": 0.9, "fact": "x"}]

    async def insert(self, table, fields, **kw):
        self.insert_calls.append((table, fields, kw))
        return {"ok": True}


def t_factory():
    fb = FakeBackend()
    p = mem.get_memory_provider("pgvector", fb)
    check("factory: returns PgVectorMemoryProvider", isinstance(p, mem.PgVectorMemoryProvider))
    check("factory: default name -> pgvector", isinstance(mem.get_memory_provider("", fb),
          mem.PgVectorMemoryProvider))
    check("factory: provider isinstance MemoryProvider", isinstance(p, mem.MemoryProvider))
    raised = False
    try:
        mem.get_memory_provider("redis-vectors", fb)
    except ValueError:
        raised = True
    check("factory: FAIL-CLOSED on unknown name (ValueError)", raised)


def t_retrieve_parity():
    fb = FakeBackend()
    p = mem.get_memory_provider("pgvector", fb)
    rows = asyncio.run(p.retrieve([0.1, 0.2], table="knowledge", k=3, owner="alice"))
    check("retrieve: returns backend rows", rows == [{"score": 0.9, "fact": "x"}])
    check("retrieve: forwards ALL kwargs verbatim (golden parity)",
          fb.recall_calls == [([0.1, 0.2], {"table": "knowledge", "k": 3, "owner": "alice"})],
          f"{fb.recall_calls}")
    # agent_memory-style call (no owner) -- the seam must not inject defaults.
    asyncio.run(p.retrieve([0.3], table="agent_memory", k=5))
    check("retrieve: no-owner call forwards exactly (no injected owner)",
          fb.recall_calls[-1] == ([0.3], {"table": "agent_memory", "k": 5}))


def t_add_parity():
    fb = FakeBackend()
    p = mem.get_memory_provider("pgvector", fb)
    r = asyncio.run(p.add("knowledge", {"q": "hi", "answer": "yo"}))
    check("add: returns backend result", r == {"ok": True})
    check("add: forwards table+fields verbatim",
          fb.insert_calls == [("knowledge", {"q": "hi", "answer": "yo"}, {})], f"{fb.insert_calls}")


def t_register():
    class MockProvider(mem.MemoryProvider):
        def __init__(self, backend): self.backend = backend
        async def retrieve(self, qvec, **kw): return ["mock"]
        async def add(self, table, fields, **kw): return None
    mem.register_provider("mock", MockProvider)
    p = mem.get_memory_provider("mock", FakeBackend())
    check("register: custom provider resolvable", isinstance(p, MockProvider))
    check("register: custom retrieve used", asyncio.run(p.retrieve([0.0])) == ["mock"])


def main() -> int:
    t_factory()
    t_retrieve_parity()
    t_add_parity()
    t_register()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
