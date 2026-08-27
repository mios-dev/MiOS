#!/usr/bin/env python3
# AI-hint: Unit test for mios_subagent_sandbox.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_subagent_sandbox import SubagentSandbox, validate_workspace_path

class TestSubagentSandbox(unittest.TestCase):
    def test_validate_workspace_path(self):
        valid, msg = validate_workspace_path("/tmp/ws/sub", "/tmp/ws")
        self.assertTrue(valid)

        invalid, msg = validate_workspace_path("/etc/shadow", "/tmp/ws")
        self.assertFalse(invalid)

    def test_sandbox_cmd_generation(self):
        sandbox = SubagentSandbox(workspace_path="/tmp/ws")
        cmd = sandbox.build_bwrap_args(["ls", "-la"])
        self.assertIn("bwrap", cmd[0])

if __name__ == "__main__":
    unittest.main()
