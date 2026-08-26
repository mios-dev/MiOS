# AI-hint: Asynchronous tool execution batching for non-dependent parallel tool invocations.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-tool-batch.py
"""
MiOS Agent-Pipe Parallel Tool Execution Batcher.
Separates read-only tool calls for concurrent asyncio execution from mutating sequential calls.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Tuple


class ToolBatcher:
    """Batches read-only tools concurrently and sequences mutating tools."""

    READ_ONLY_TOOLS = {
        "view_file", "list_dir", "grep_search", "find_by_name",
        "read_url_content", "search_web", "check_status"
    }

    def partition_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Separates parallelizable read-only calls from sequential mutating calls."""
        parallel_batch = []
        sequential_batch = []
        for call in tool_calls:
            name = call.get("name", "")
            if name in self.READ_ONLY_TOOLS:
                parallel_batch.append(call)
            else:
                sequential_batch.append(call)
        return parallel_batch, sequential_batch

    async def execute_batch(
        self,
        tool_calls: List[Dict[str, Any]],
        executor: Callable[[Dict[str, Any]], Coroutine[Any, Any, Any]]
    ) -> List[Any]:
        """Executes read-only tools concurrently and mutating tools in sequence."""
        parallel_calls, sequential_calls = self.partition_tool_calls(tool_calls)
        results = []

        if parallel_calls:
            parallel_results = await asyncio.gather(*(executor(call) for call in parallel_calls))
            results.extend(parallel_results)

        for call in sequential_calls:
            seq_res = await executor(call)
            results.append(seq_res)

        return results
