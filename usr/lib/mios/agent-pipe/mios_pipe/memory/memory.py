# AI-hint: WS-A15 pluggable MemoryProvider seam for the agent-pipe. Wraps the pgvector recall/store path behind a small MemoryProvider interface (retrieve/add) so the agent's long-term memory backend is swappable (a different vector store, a remote memory service, a test fake) without touching the recall call sites. PgVectorMemoryProvider is the default, delegating verbatim to the mios_pg client; get_memory_provider(name, backend) is a fail-CLOSED factory (raises ValueError on an unknown name). server.py owns the wiring (resolve [pgvector].memory_provider, build the module-global _MEMORY, route _recall_agent_memory/_recall_knowledge_pg through it); this module owns only the seam.
# AI-related: ./mios_pg.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_memory.py
# AI-functions: retrieve, add, get_memory_provider, register_provider, class MemoryProvider, class PgVectorMemoryProvider
"""mios_memory -- pluggable agent-memory provider seam (WS-A15, the AIOS
Memory-Manager abstraction).

Pure stdlib so it unit-tests in isolation (the default provider takes its
backend by INJECTION, so a fake stands in for mios_pg with no DB). server.py
owns the wiring (SSOT [pgvector].memory_provider, the module-global _MEMORY, and
routing the recall call sites through it); this module owns only the interface +
the pgvector-backed default.

Why a seam
==========
Before WS-A15 the recall path called mios_pg.recall(...) directly at each site,
so the storage backend was hard-wired. The MemoryProvider interface (retrieve /
add) lets the backend be swapped -- a different vector DB, a remote memory
service, or a test double -- behind ONE resolution point, without editing the
recall logic. The default (pgvector) is a verbatim pass-through to mios_pg, so
behaviour is byte-identical until a different provider is configured.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryProvider(ABC):
    """The long-term memory backend contract: semantic retrieve + add."""

    @abstractmethod
    async def retrieve(self, qvec, **kw) -> Any:
        """Semantic recall for an embedded query. Keyword args (table/k/owner/...)
        are passed through to the backend unchanged."""
        raise NotImplementedError

    @abstractmethod
    async def add(self, table: str, fields: dict, **kw) -> Any:
        """Persist one memory row to `table`."""
        raise NotImplementedError


class PgVectorMemoryProvider(MemoryProvider):
    """The default provider: a verbatim pass-through to the injected mios_pg-like
    backend (recall/insert). Holds NO logic of its own, so it is byte-identical
    to the pre-WS-A15 direct calls."""

    name = "pgvector"

    def __init__(self, backend) -> None:
        # `backend` is the mios_pg module (or any object exposing async
        # recall(qvec, **kw) + insert(table, fields, **kw)).
        self._pg = backend

    async def retrieve(self, qvec, **kw) -> Any:
        return await self._pg.recall(qvec, **kw)

    async def add(self, table: str, fields: dict, **kw) -> Any:
        return await self._pg.insert(table, fields, **kw)


# Provider registry. A new backend registers a factory(backend) -> MemoryProvider.
_PROVIDERS = {"pgvector": PgVectorMemoryProvider}


def register_provider(name: str, factory) -> None:
    """Register an additional provider factory under `name` (lowercased)."""
    _PROVIDERS[str(name).strip().lower()] = factory


def get_memory_provider(name: str, backend) -> MemoryProvider:
    """Resolve a MemoryProvider by name, constructing it over `backend`.
    FAIL-CLOSED: an unknown name raises ValueError (a typo must not silently
    fall through to an unintended backend). server.py catches this at startup
    and degrades to the default with a loud log."""
    key = str(name or "pgvector").strip().lower() or "pgvector"
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise ValueError(
            f"unknown memory provider {name!r}; known: {sorted(_PROVIDERS)} "
            f"(fail-closed)")
    return cls(backend)
