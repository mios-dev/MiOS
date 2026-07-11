#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_knowledge (refactor R6 KNOWLEDGE-cluster extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the recency-weighting invariants (_recency_mult: inert==1.0 when rank_age==0; bounded decay so a fresh row outranks an older one within the half-life and the factor stays in [1-rank_age, 1.0]), the possessive recall-floor (_recall_floor drops to the lower preference floor only when a 1st/2nd-person possessive is present, else the default), and the blended pgvector rerank (_recall_knowledge_pg, driven through the DI seam with async stubs for _embed_one/_MEMORY.retrieve/_rls_owner/_db_fire/_db_update) so a hot+satisfied+frequently-accessed row outranks a cold+unsatisfied one at equal cosine. Guards the extracted cluster so a later move can't silently change the recency math, the floor logic, or the recall ordering.
# AI-related: ./mios_knowledge.py
# AI-functions: check, t_recall_floor, t_recency_mult, t_recall_blend, _FakeVar, t_rls_owner, t_recall_agent_memory, t_kg_lookup, main
"""Unit tests for mios_knowledge (refactor R6). No DB / network / pytest."""

import asyncio
import re
import sys
import time

import mios_knowledge as k

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_recall_floor():
    k.configure(
        recall_possessive_re=re.compile(r"\b(my|mine|your|yours|our|ours)\b", re.I),
        knowledge_recall_min_score=0.62,
        knowledge_recall_pref_min_score=0.50,
    )
    # No possessive -> default floor.
    check("recall_floor default (no possessive)",
          k._recall_floor("what is the capital of France") == 0.62,
          str(k._recall_floor("what is the capital of France")))
    # Possessive present -> the lower preference floor.
    check("recall_floor preference (possessive)",
          k._recall_floor("what is my favorite editor") == 0.50,
          str(k._recall_floor("what is my favorite editor")))
    # Never raises above the default even if pref floor were higher.
    k.configure(knowledge_recall_pref_min_score=0.99)
    check("recall_floor never above default",
          k._recall_floor("what is my X") == 0.62,
          str(k._recall_floor("what is my X")))
    # restore for later tests
    k.configure(knowledge_recall_pref_min_score=0.50)


def t_recency_mult():
    # rank_age==0 -> inert (always 1.0), backward-compatible.
    k.configure(knowledge_rank_age=0.0, knowledge_recall_halflife_days=7.0)
    check("recency_mult inert when rank_age==0",
          k._recency_mult({"ts": time.time() - 9 * 86400}) == 1.0)

    # rank_age>0 -> bounded decay: newer outranks older, factor in [1-rank_age, 1].
    k.configure(knowledge_rank_age=0.3, knowledge_recall_halflife_days=7.0)
    now = time.time()
    m_fresh = k._recency_mult({"last_access": now})
    m_halflife = k._recency_mult({"last_access": now - 7 * 86400})
    m_old = k._recency_mult({"last_access": now - 60 * 86400})
    check("recency_mult fresh ~1.0", abs(m_fresh - 1.0) < 1e-6, str(m_fresh))
    check("recency_mult newer > older within half-life", m_fresh > m_halflife > m_old,
          f"{m_fresh:.4f} {m_halflife:.4f} {m_old:.4f}")
    check("recency_mult at one half-life == (1-ra)+ra*0.5",
          abs(m_halflife - ((1 - 0.3) + 0.3 * 0.5)) < 1e-6, str(m_halflife))
    check("recency_mult bounded below by 1-rank_age", m_old >= (1 - 0.3) - 1e-9, str(m_old))
    # last_access takes precedence over ts; missing both -> 1.0 (degrade-open).
    check("recency_mult no timestamp -> 1.0", k._recency_mult({}) == 1.0)
    k.configure(knowledge_rank_age=0.0)  # restore inert for the blend test


def t_recall_blend():
    """_recall_knowledge_pg blended rerank: at equal cosine, a hot+satisfied+
    frequently-accessed row must outrank a cold+unsatisfied one. Recency held
    inert (rank_age==0) so the ordering isolates the cosine+outcome+tier+access
    blend. All deps supplied through the DI seam with async stubs -- no DB."""
    fired = []

    async def _embed_one(_q, *args, **kwargs):
        return [0.1] * 8

    class _Mem:
        async def retrieve(self, qv, *, table=None, k=None, owner=None, emb_version=None, rls_owner=None, **kwargs):
            # deliberately returned in the WRONG order to prove the rerank sorts.
            return [
                {"id": 2, "score": 0.70, "q": "COLD question", "answer": "a2",
                 "ts": time.time(), "satisfied": False, "tier": "warm",
                 "access_count": 0},
                {"id": 1, "score": 0.70, "q": "HOT question", "answer": "a1",
                 "ts": time.time(), "satisfied": True, "tier": "hot",
                 "access_count": 10},
            ]

    def _db_fire(coro):
        fired.append(coro)
        try:
            coro.close()  # we don't run the bump; just don't leak the coro
        except Exception:
            pass

    async def _db_update(*a, **kw):
        return None

    # _rls_owner now lives in this module (no longer injected); with rls_mode off
    # (real default) it returns None, so the recall stays unscoped here.
    k.configure(
        embed_one=_embed_one,
        memory=_Mem(),
        db_fire=_db_fire,
        db_update=_db_update,
        knowledge_table="knowledge",
        knowledge_recall_k=3,
        knowledge_recall_candidates=60,
        knowledge_recall_min_score=0.62,
        knowledge_rank_outcome=0.05,
        knowledge_rank_hot=0.03,
        knowledge_rank_access=0.02,
        knowledge_hot_threshold=5,
        knowledge_rank_age=0.0,
    )
    block = asyncio.run(k._recall_knowledge_pg("anything"))
    check("recall_pg returns a non-empty injectable block",
          isinstance(block, str) and "HOT question" in block and "COLD question" in block,
          repr(block[:80]))
    # Blend must place HOT (satisfied/hot/accessed) before COLD at equal cosine.
    check("recall_pg blended order: hot+satisfied outranks cold+unsatisfied",
          block.index("HOT question") < block.index("COLD question"))
    # A page-in bump was queued for the surfaced rows (fire-and-forget).
    check("recall_pg queued page-in bump", len(fired) >= 1, str(len(fired)))

    # Below-floor candidates -> clean empty-string miss.
    class _MemLow:
        async def retrieve(self, qv, *, table=None, k=None, owner=None, emb_version=None, rls_owner=None, **kwargs):
            return [{"id": 9, "score": 0.10, "q": "x", "answer": "y",
                     "ts": time.time()}]
    k.configure(memory=_MemLow())
    check("recall_pg below-floor -> ''", asyncio.run(k._recall_knowledge_pg("q")) == "")


class _FakeVar:
    """Minimal contextvar stand-in: .get([default]) -> the stored value."""
    def __init__(self, v):
        self._v = v
    def get(self, default=None):
        return self._v


def t_rls_owner():
    """_rls_owner: None unless [pgvector].rls_mode == 'enforce' AND a principal was
    forwarded. Drive _toml_section + _client_env_var directly (module globals)."""
    _orig_toml = k._toml_section
    _orig_env = k._client_env_var
    try:
        # rls_mode absent -> 'off' -> None regardless of any forwarded principal.
        k._toml_section = lambda _s: {}
        k._client_env_var = _FakeVar({"user_name": "zqxprincipal"})
        check("rls_owner off -> None", k._rls_owner() is None, repr(k._rls_owner()))
        # enforce + principal -> the principal id.
        k._toml_section = lambda _s: {"rls_mode": "enforce"}
        check("rls_owner enforce+principal -> owner",
              k._rls_owner() == "zqxprincipal", repr(k._rls_owner()))
        # enforce, NO principal forwarded -> None (degrade to unscoped).
        k._client_env_var = _FakeVar({})
        check("rls_owner enforce+no-principal -> None",
              k._rls_owner() is None, repr(k._rls_owner()))
        # email falls back when user_name absent.
        k._client_env_var = _FakeVar({"user_email": "wbz@vorp"})
        check("rls_owner falls back to user_email",
              k._rls_owner() == "wbz@vorp", repr(k._rls_owner()))
    finally:
        k._toml_section = _orig_toml
        k._client_env_var = _orig_env


def t_recall_agent_memory():
    """_recall_agent_memory: default-off -> ''; enabled -> an injectable block of
    the durable facts above the score floor, scope-tagged for non-global scopes."""
    async def _embed_one(_q):
        return [0.2] * 8

    class _Mem:
        async def retrieve(self, qv, *, table=None, k=None, owner=None, emb_version=None, rls_owner=None):
            return [
                {"fact": "the zqxw codeword is vorpaline", "score": 0.91,
                 "scope": "global"},
                {"fact": "blixfap lives on port wibble", "score": 0.77,
                 "scope": "devbox"},
                {"fact": "below-floor noise", "score": 0.10, "scope": "global"},
            ]

    _orig_toml = k._toml_section
    try:
        k._toml_section = lambda _s: {}  # rls off -> _rls_owner() None (unscoped)
        # Default-off: no recall even with PG primary.
        k.configure(agent_memory_recall_enabled=False, pg_primary=True,
                    embed_one=_embed_one, memory=_Mem(),
                    agent_memory_recall_min_score=0.45)
        check("agent-memory recall default-off -> ''",
              asyncio.run(k._recall_agent_memory("anything")) == "")
        # Enabled: facts above the floor are surfaced; the below-floor row is dropped.
        k.configure(agent_memory_recall_enabled=True,
                    agent_memory_table="agent_memory", agent_memory_recall_k=3)
        block = asyncio.run(k._recall_agent_memory("anything"))
        check("agent-memory recall surfaces above-floor facts",
              "vorpaline" in block and "blixfap" in block, repr(block[:80]))
        check("agent-memory recall drops below-floor row",
              "below-floor noise" not in block)
        check("agent-memory recall tags non-global scope",
              "(devbox)" in block and "(global)" not in block, repr(block[-80:]))
        # No PG primary -> '' (degrade-open).
        k.configure(pg_primary=False)
        check("agent-memory recall no-PG -> ''",
              asyncio.run(k._recall_agent_memory("x")) == "")
        k.configure(pg_primary=True)
    finally:
        k._toml_section = _orig_toml


def t_recall_agent_memory_recency():
    """A7: agent_memory recall applies the SHARED blended rerank (not flat cosine).
    With rank_age>0 a recently-saved fact OUTRANKS a stale one at EQUAL cosine
    (recency breaks the tie); at rank_age==0 the blend is inert (pure cosine), so the
    contrast proves the recency weighting drove the order. DEGRADE-OPEN: agent_memory
    has no access/tier/outcome columns -> those blend terms read neutral, only cosine
    + ts contribute, and nothing crashes."""
    now = time.time()

    async def _embed_one(_q, *args, **kwargs):
        return [0.3] * 8

    class _Mem:
        async def retrieve(self, qv, *, table=None, k=None, owner=None, emb_version=None, rls_owner=None, **kwargs):
            # Equal cosine; returned STALE-first so a reorder is observable.
            return [
                {"fact": "STALE fact zqx", "score": 0.80, "scope": "global",
                 "ts": now - 60 * 86400},
                {"fact": "FRESH fact zqx", "score": 0.80, "scope": "global",
                 "ts": now},
            ]

    _orig_toml = k._toml_section
    try:
        k._toml_section = lambda _s: {}  # rls off -> _rls_owner() None (unscoped)
        k.configure(agent_memory_recall_enabled=True, pg_primary=True,
                    embed_one=_embed_one, memory=_Mem(),
                    agent_memory_table="agent_memory", agent_memory_recall_k=3,
                    agent_memory_recall_min_score=0.45,
                    knowledge_recall_candidates=60,
                    knowledge_rank_outcome=0.05, knowledge_rank_hot=0.03,
                    knowledge_rank_access=0.02,
                    knowledge_rank_age=0.3, knowledge_recall_halflife_days=7.0)
        block = asyncio.run(k._recall_agent_memory("anything"))
        check("agent-memory recency: fresh fact outranks stale at equal cosine",
              "FRESH fact zqx" in block and "STALE fact zqx" in block
              and block.index("FRESH fact zqx") < block.index("STALE fact zqx"),
              repr(block[:120]))
        # Inert at rank_age==0 -> pure cosine; equal-cosine ties keep input order
        # (stable sort), so STALE (listed first) leads -> isolates the recency effect.
        k.configure(knowledge_rank_age=0.0)
        block0 = asyncio.run(k._recall_agent_memory("anything"))
        check("agent-memory recency: inert at rank_age==0 (input order kept)",
              block0.index("STALE fact zqx") < block0.index("FRESH fact zqx"),
              repr(block0[:120]))
    finally:
        k._toml_section = _orig_toml
        k.configure(knowledge_rank_age=0.0)  # leave inert for any later test


def t_kg_lookup():
    """kg_lookup: alias exact-match returns the resolved app_install row; an empty
    phrase short-circuits to None; an all-empty result-set falls through to None."""
    hit = {"short_name": "vorpalapp", "app_id": "wz1", "source": "winget",
           "label": "Vorpal", "launch_hint": "vorpal://"}

    async def _db_read_hit(sql, **kw):
        return [{"result": [{"phrase": "wibblephrase", "apps": [hit]}]}]

    async def _db_read_miss(sql, **kw):
        return [{"result": []}]

    k.configure(db_read=_db_read_hit)
    check("kg_lookup empty phrase -> None",
          asyncio.run(k.kg_lookup("")) is None)
    res = asyncio.run(k.kg_lookup("wibblephrase"))
    check("kg_lookup alias hit -> resolved app",
          isinstance(res, dict) and res.get("source") == "alias"
          and res.get("app") == hit, repr(res))
    k.configure(db_read=_db_read_miss)
    check("kg_lookup no match -> None",
          asyncio.run(k.kg_lookup("nothere")) is None)


def t_hybrid_and_rerank():
    async def _embed_one(_q, *args, **kwargs):
        return [0.1] * 8

    retrieved_kwargs = {}

    class _MemTrack:
        async def retrieve(self, qv, **kwargs):
            retrieved_kwargs.update(kwargs)
            return [
                {"id": 1, "score": 0.8, "q": "what is your favorite editor", "answer": "Neovim",
                 "ts": time.time(), "satisfied": True, "tier": "hot", "access_count": 5}
            ]

    k.configure(
        embed_one=_embed_one,
        memory=_MemTrack(),
        knowledge_table="knowledge",
        knowledge_recall_k=3,
        knowledge_recall_candidates=60,
        knowledge_recall_min_score=0.62,
        knowledge_rank_age=0.0,
        knowledge_rag_hybrid=True,
        knowledge_rag_rerank=True,
    )

    try:
        block = asyncio.run(k._recall_knowledge_pg("what is your favorite editor"))
        check("hybrid: query_text passed to memory.retrieve", retrieved_kwargs.get("query_text") == "what is your favorite editor")
        check("hybrid: hybrid=True passed to memory.retrieve", retrieved_kwargs.get("hybrid") is True)
        check("hybrid: rerank=True passed to memory.retrieve", retrieved_kwargs.get("rerank") is True)
        check("hybrid: recall returns content correctly", "Neovim" in block, repr(block))
    finally:
        k.configure(
            knowledge_rag_hybrid=False,
            knowledge_rag_rerank=False,
        )


def main():
    t_recall_floor()
    t_recency_mult()
    t_recall_blend()
    t_rls_owner()
    t_recall_agent_memory()
    t_recall_agent_memory_recency()
    t_kg_lookup()
    t_hybrid_and_rerank()
    if _fails:
        print(f"\n{_fails} FAILED")
        sys.exit(1)
    print("\nok")


if __name__ == "__main__":
    main()
