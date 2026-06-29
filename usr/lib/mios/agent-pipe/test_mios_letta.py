#!/usr/bin/env python3
# AI-hint: Standalone unit test suite for LettaMemoryClient and letta_dispatch_handler (T-077).
# Pure stdlib + asyncio, no live Letta server required. Runs as `python3 test_mios_letta.py` (exit 0 = pass).
# usr/lib/mios/agent-pipe/test_mios_letta.py

import asyncio
import json
import sys
from typing import Optional

# Setup import path for agent-pipe dependencies
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mios_memory

_fails = 0

def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json

class MockHTTPXClient:
    def __init__(self, **kwargs):
        self.history = []

    async def get(self, url, params=None):
        self.history.append(("GET", url, params))
        if url == "/v1/agents":
            return MockResponse(200, [{"name": "test-session", "id": "agent-123"}])
        elif url == "/v1/agents/agent-123/memory":
            return MockResponse(200, {"blocks": [{"label": "persona", "value": "prefers dark mode"}]})
        elif url == "/v1/agents/agent-123/archival-memory/search":
            return MockResponse(200, [{"id": "item-1", "text": "prefers dark mode", "scope": "global"}])
        return MockResponse(404, {})

    async def post(self, url, json=None):
        self.history.append(("POST", url, json))
        if url == "/v1/agents":
            return MockResponse(201, {"id": "agent-123", "name": json.get("name")})
        elif url == "/v1/agents/agent-123/memory/blocks":
            return MockResponse(200, {"ok": True})
        elif url == "/v1/agents/agent-123/messages":
            return MockResponse(200, {"ok": True})
        return MockResponse(404, {})

    async def delete(self, url):
        self.history.append(("DELETE", url, None))
        if url == "/v1/agents/agent-123/in-context-messages/oldest":
            return MockResponse(200, {"ok": True})
        return MockResponse(404, {})

async def test_letta_client_flow():
    # Force client to use mock HTTPX
    client = mios_memory.LettaMemoryClient("http://localhost:8283")
    mock_http = MockHTTPXClient()
    client.client = mock_http

    # 1. Get or create agent
    agent_id = await client.get_or_create_agent("test-session")
    check("letta: resolves existing agent ID", agent_id == "agent-123")

    # 2. Append memory
    res = await client.append_memory("test-session", "persona", "prefers dark mode")
    check("letta: append memory succeeds", res.get("ok") is True)

    # 3. Search memory
    s_res = await client.search_memory("test-session", "dark mode")
    check("letta: search memory succeeds", s_res.get("ok") is True)
    check("letta: search returns formatted memories", len(s_res.get("memories", [])) == 1)

    # 4. Compaction triggers
    await client.trigger_compaction("test-session")
    check("letta: trigger compaction post is recorded", mock_http.history[-1][0] == "POST")

    # 5. Flush oldest context message
    await client.flush_oldest("test-session")
    check("letta: flush oldest delete is recorded", mock_http.history[-1][0] == "DELETE")

async def test_dispatch_handler_remember():
    # Force client to use mock HTTPX and enable backend
    mios_memory.LETTA_MEMORY_BACKEND = True
    mios_memory._LETTA_CLIENT = mios_memory.LettaMemoryClient("http://localhost:8283")
    mock_http = MockHTTPXClient()
    mios_memory._LETTA_CLIENT.client = mock_http

    # Setup database mock helpers inside mios_memory module
    stored_db = []
    def mock_db_create(table, fields, **kw):
        stored_db.append((table, fields))
        return fields
    mios_memory._db_create = mock_db_create
    mios_memory._db_post = lambda x: x
    mios_memory._db_fire = lambda x: x

    # Call letta_dispatch_handler for remember verb
    args = {"fact": "I prefer dark mode", "scope": "global", "key": "persona"}
    res = await mios_memory.letta_dispatch_handler("remember", args, "test-session")
    check("dispatch: intercept remember returns dispatch result", res is not None)
    check("dispatch: remember dispatch succeeds", res.get("success") is True)
    check("dispatch: remember updates local pg snapshot", len(stored_db) > 0)
    check("dispatch: remember local pg scope correct", stored_db[0][1].get("scope") == "conversation:test-session")

def main():
    asyncio.run(test_letta_client_flow())
    asyncio.run(test_dispatch_handler_remember())
    
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    sys.exit(1 if _fails else 0)

if __name__ == "__main__":
    main()
