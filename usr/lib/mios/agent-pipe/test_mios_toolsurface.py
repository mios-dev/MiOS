# AI-hint: Unit tests for mios_pipe.routing.toolsurface.
"""Unit tests for worker tool surface assembly and child tool selection."""

import asyncio
import unittest

from mios_pipe.routing.toolsurface import (
    _select_child_tools,
    _worker_tools_surface,
    configure,
)


def mock_verb_to_openai_tool(name, cfg):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": cfg.get("description", ""),
            "parameters": {"type": "object", "properties": {}},
        },
    }


class TestToolSurface(unittest.TestCase):

    def setUp(self):
        self.stub_catalog = {
            "read_file": {"permission": "read", "description": "Read file contents"},
            "run_cmd": {"permission": "exec", "description": "Run terminal command"},
        }
        configure(
            worker_tools_scope="all",
            child_tool_select=True,
            stable_prefix=False,
            child_tool_floor=1,
            verb_catalog=self.stub_catalog,
            verb_to_openai_tool=mock_verb_to_openai_tool,
        )

    def test_worker_tools_surface_shape(self):
        surface = _worker_tools_surface()
        self.assertEqual(len(surface), 2)
        names = [t["function"]["name"] for t in surface]
        self.assertIn("read_file", names)
        self.assertIn("run_cmd", names)

    def test_select_child_tools_capping(self):
        surface = _worker_tools_surface()
        res = asyncio.run(_select_child_tools(surface, "read a file", cap=1))
        self.assertEqual(len(res), 1)


if __name__ == "__main__":
    unittest.main()
