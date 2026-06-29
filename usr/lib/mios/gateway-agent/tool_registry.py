import asyncio
import logging
from typing import List, Callable, Any
from smolagents import Tool

log = logging.getLogger("gateway-agent-registry")

class MiOSToolRegistry:
    def __init__(self, mcp_client, main_loop: asyncio.AbstractEventLoop):
        self.mcp_client = mcp_client
        self.main_loop = main_loop
        self._tools = []

    def get_tools(self) -> List[Tool]:
        # Build smolagents.Tool instances dynamically from the MCP cached tools
        tools = []
        for mcp_tool in self.mcp_client.cached_tools:
            try:
                tool_inst = self._create_tool_instance(mcp_tool)
                tools.append(tool_inst)
            except Exception as e:
                log.warning("Failed to map MCP tool %s to smolagents.Tool: %s", getattr(mcp_tool, "name", "unknown"), e)
        return tools

    def _create_tool_instance(self, mcp_tool) -> Tool:
        name = getattr(mcp_tool, "name", "")
        description = getattr(mcp_tool, "description", "")
        
        # Parse inputs schema from inputSchema
        input_schema = getattr(mcp_tool, "inputSchema", {}) or {}
        properties = input_schema.get("properties", {}) or {}
        required = input_schema.get("required", []) or []
        
        inputs = {}
        for param_name, param_schema in properties.items():
            inputs[param_name] = {
                "type": param_schema.get("type", "any"),
                "description": param_schema.get("description", f"Parameter {param_name}")
            }
            if param_name not in required:
                inputs[param_name]["nullable"] = True

        # Dynamic subclass creation
        client = self.mcp_client
        loop = self.main_loop

        class DynamicTool(Tool):
            def __init__(self, name_val, desc_val, inputs_val):
                self.name = name_val
                self.description = desc_val
                self.inputs = inputs_val
                self.output_type = "string"
                self.skip_forward_signature_validation = True
                super().__init__()

            def forward(self, **kwargs) -> str:
                # Dispatch the async call to the running event loop from the executor thread
                coro = client.call_tool(self.name, kwargs)
                fut = asyncio.run_coroutine_threadsafe(coro, loop)
                try:
                    # Timeout 20 seconds to prevent blocking indefinitely
                    return fut.result(timeout=20.0)
                except Exception as e:
                    return f"Error executing tool {self.name}: {e}"

        return DynamicTool(name, description, inputs)
