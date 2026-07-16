#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for MCPClientPool (CONV-13).
# Mocks stdio/sse clients to assert startup/shutdown and unified tools listing.
# AI-related: ./mios_gateway_queue.py

import os
import sys
import asyncio
from unittest import mock

try:
    import mcp
    from mios_gateway_queue import MCPClientPool
except ImportError as e:
    print(f"Skipping test_mios_mcp_pool.py: missing dependencies ({e})")
    sys.exit(0)

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

class MockTool:
    def __init__(self, name, description, inputSchema):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

class MockToolsResult:
    def __init__(self, tools):
        self.tools = tools

class MockSession:
    def __init__(self, tools):
        self.tools = tools
        self.inited = False
        self.closed = False

    async def list_tools(self):
        return MockToolsResult(self.tools)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.closed = True

async def test_mcp_pool_lifecycle():
    # Setup server configs
    server_configs = {
        "playwright": {
            "enabled": True,
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@playwright/mcp"],
            "env": {"TEST_VAR": "value"}
        },
        "disabled_srv": {
            "enabled": False,
            "transport": "stdio"
        }
    }

    # Setup mock session with a tool
    mock_tool = MockTool(
        name="navigate",
        description="Navigate to URL",
        inputSchema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
    )
    mock_session = MockSession(tools=[mock_tool])

    # Instantiate pool
    pool = MCPClientPool(server_configs)

    # Check initialization
    check("pool: clients created", "playwright" in pool.clients)
    check("pool: disabled client ignored", "disabled_srv" not in pool.clients)

    # Mock StdioClient.connect
    async def mock_connect(self):
        self.session = mock_session
        return mock_session

    async def mock_close(self):
        pass

    with mock.patch.object(mcp.StdioClient, "connect", mock_connect), \
         mock.patch.object(mcp.StdioClient, "close", mock_close):
        
        # Test startup
        await pool.startup()
        
        tools = pool.get_tools()
        check("pool: fetched tool successfully", len(tools) == 1)
        check("pool: namespaced tool name", tools[0]["name"] == "mcp.playwright.navigate")
        check("pool: tool description matches", tools[0]["description"] == "Navigate to URL")
        check("pool: inputSchema is preserved", "properties" in tools[0]["inputSchema"])
        
        # Test shutdown
        await pool.shutdown()
        check("pool: shutdown clears clients dict", len(pool.clients) == 0)
        check("pool: shutdown clears tools cache", len(pool.get_tools()) == 0)

async def main():
    await test_mcp_pool_lifecycle()
    if _fails > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
