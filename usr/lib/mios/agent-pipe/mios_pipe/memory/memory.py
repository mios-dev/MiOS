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

# --- Letta Server Memory Complement (T-076 & T-077) ---
import os
import json
import httpx
import logging

log = logging.getLogger("letta-memory")

LETTA_MEMORY_BACKEND = False
_LETTA_CLIENT = None
_conv_key_var = None
_db_create = None
_db_post = None
_db_fire = None

class LettaMemoryClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        # Timeout 15 seconds to avoid locking up on slow LLM calls
        self.client = httpx.AsyncClient(base_url=self.endpoint, timeout=15.0)

    async def get_or_create_agent(self, session_id: str) -> str:
        name = session_id or "default"
        try:
            r = await self.client.get("/v1/agents")
            if r.status_code == 200:
                for agent in r.json():
                    if agent.get("name") == name:
                        return agent.get("id")
        except Exception as e:
            log.warning("Letta client get_agents error: %s", e)

        try:
            payload = {
                "name": name,
                "memory": {
                    "blocks": [
                        {"label": "persona", "value": ""},
                        {"label": "human", "value": ""}
                    ]
                }
            }
            r = await self.client.post("/v1/agents", json=payload)
            if r.status_code in (200, 201):
                return r.json().get("id")
        except Exception as e:
            log.warning("Letta client create_agent error: %s", e)
        return name

    async def append_memory(self, session_id: str, label: str, value: str) -> dict:
        agent_id = await self.get_or_create_agent(session_id)
        try:
            r = await self.client.post(
                f"/v1/agents/{agent_id}/memory/blocks",
                json={"label": label, "value": value}
            )
            return {"ok": r.status_code in (200, 201), "status_code": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def search_memory(self, session_id: str, query: str) -> dict:
        agent_id = await self.get_or_create_agent(session_id)
        try:
            r = await self.client.get(
                f"/v1/agents/{agent_id}/archival-memory/search",
                params={"query": query}
            )
            if r.status_code == 200:
                results = r.json()
                memories = []
                for item in results:
                    memories.append({
                        "key": item.get("id") or item.get("key") or "letta",
                        "scope": item.get("scope") or "global",
                        "fact": item.get("text") or item.get("fact") or str(item),
                        "source": "letta"
                    })
                return {"ok": True, "count": len(memories), "memories": memories}
            return {"ok": False, "status_code": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def trigger_compaction(self, session_id: str):
        agent_id = await self.get_or_create_agent(session_id)
        try:
            await self.client.post(
                f"/v1/agents/{agent_id}/messages",
                json={"role": "system", "text": "Compaction hint: summarize the conversation."}
            )
        except Exception as e:
            log.warning("Letta client compaction error: %s", e)

    async def flush_oldest(self, session_id: str):
        agent_id = await self.get_or_create_agent(session_id)
        try:
            await self.client.delete(f"/v1/agents/{agent_id}/in-context-messages/oldest")
        except Exception as e:
            log.warning("Letta client flush oldest error: %s", e)

    async def sync_to_pg(self, session_id: str, db_create_func):
        agent_id = await self.get_or_create_agent(session_id)
        try:
            r = await self.client.get(f"/v1/agents/{agent_id}/memory")
            if r.status_code == 200:
                blocks = r.json().get("blocks") or []
                for b in blocks:
                    val = b.get("value") or ""
                    if val.strip():
                        db_create_func("agent_memory", {
                            "fact": f"[{b.get('label', 'core')}] {val}",
                            "scope": f"conversation:{session_id}",
                            "mem_key": f"letta-{b.get('label')}",
                            "source": "letta"
                        })
        except Exception as e:
            log.warning("Letta client sync_to_pg error: %s", e)

def configure_letta(*, toml_section_func, conv_key_var, db_create, db_post, db_fire):
    global LETTA_MEMORY_BACKEND, _LETTA_CLIENT, _conv_key_var, _db_create, _db_post, _db_fire
    _conv_key_var = conv_key_var
    _db_create = db_create
    _db_post = db_post
    _db_fire = db_fire

    letta_cfg = (toml_section_func("agents") or {}).get("letta", {})
    LETTA_MEMORY_BACKEND = str(
        os.environ.get("MIOS_LETTA_MEMORY_BACKEND")
        or letta_cfg.get("memory_backend", "false")
    ).strip().lower() in {"1", "true", "yes"}
    letta_endpoint = str(
        os.environ.get("MIOS_LETTA_ENDPOINT")
        or letta_cfg.get("endpoint", "http://localhost:8283")
    )
    if LETTA_MEMORY_BACKEND:
        _LETTA_CLIENT = LettaMemoryClient(letta_endpoint)

async def letta_dispatch_handler(tool: str, args: dict, session_id: Optional[str]) -> Optional[dict]:
    if not LETTA_MEMORY_BACKEND or not _LETTA_CLIENT:
        return None

    sid = session_id or (_conv_key_var.get() if _conv_key_var else None) or "default"
    
    if tool in ("remember", "memory_append"):
        fact = args.get("fact") or args.get("text") or args.get("memory") or ""
        scope = args.get("scope") or "global"
        key = args.get("key") or args.get("id") or args.get("name") or f"m{abs(hash(fact)) % (10**10)}"
        res = await _LETTA_CLIENT.append_memory(sid, key, fact)
        if res.get("ok"):
            if _LETTA_CLIENT and _db_fire and _db_post and _db_create:
                await _LETTA_CLIENT.sync_to_pg(sid, lambda table, fields: _db_fire(_db_post(_db_create(table, fields, now_fields=("ts",)))))
            return {"success": True, "tool": tool, "args": args, "output": json.dumps({"ok": True, "op": "add", "key": key, "scope": scope, "stored": True}), "stderr": "", "exit_code": 0}
        else:
            return {"success": False, "tool": tool, "args": args, "output": "", "stderr": res.get("error", "letta error"), "exit_code": 1}

    if tool in ("memory_update", "memory_replace"):
        fact = args.get("fact") or args.get("text") or args.get("memory") or ""
        key = args.get("key") or args.get("id") or args.get("name") or ""
        res = await _LETTA_CLIENT.append_memory(sid, key, fact)
        if res.get("ok"):
            if _LETTA_CLIENT and _db_fire and _db_post and _db_create:
                await _LETTA_CLIENT.sync_to_pg(sid, lambda table, fields: _db_fire(_db_post(_db_create(table, fields, now_fields=("ts",)))))
            return {"success": True, "tool": tool, "args": args, "output": json.dumps({"ok": True, "op": "update", "key": key, "updated": 1, "matched": True}), "stderr": "", "exit_code": 0}
        else:
            return {"success": False, "tool": tool, "args": args, "output": "", "stderr": res.get("error", "letta error"), "exit_code": 1}

    if tool in ("recall", "memory_search"):
        query = args.get("query") or args.get("fact") or args.get("scope") or ""
        res = await _LETTA_CLIENT.search_memory(sid, query)
        if res.get("ok"):
            return {"success": True, "tool": tool, "args": args, "output": json.dumps(res), "stderr": "", "exit_code": 0}
        else:
            return {"success": False, "tool": tool, "args": args, "output": "", "stderr": res.get("error", "letta error"), "exit_code": 1}

    if tool == "memory_forget":
        key = args.get("key") or args.get("id") or args.get("name") or ""
        res = await _LETTA_CLIENT.append_memory(sid, key, "")
        if res.get("ok"):
            if _LETTA_CLIENT and _db_fire and _db_post and _db_create:
                await _LETTA_CLIENT.sync_to_pg(sid, lambda table, fields: _db_fire(_db_post(_db_create(table, fields, now_fields=("ts",)))))
            return {"success": True, "tool": tool, "args": args, "output": json.dumps({"ok": True, "op": "forget", "key": key}), "stderr": "", "exit_code": 0}
        else:
            return {"success": False, "tool": tool, "args": args, "output": "", "stderr": res.get("error", "letta error"), "exit_code": 1}

    return None
