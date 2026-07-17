# AI-hint: stdlib unit test for mios_template (AGY-52).
# AI-related: usr/lib/mios/agent-pipe/test_mios_template.py, usr/lib/mios/agent-pipe/mios_template.py
# AI-functions: TestMiosTemplate, main
"""Unit tests for mios_template command rendering."""

import unittest
import os
from unittest import mock

from mios_template import _template_to_cmd


class TestMiosTemplate(unittest.TestCase):

    def test_basic_substitution(self):
        # Normal required placeholder
        res = _template_to_cmd("test_tool", "echo {message}", {"message": "hello world"})
        self.assertEqual(res, "echo 'hello world'")

    def test_required_or_abort(self):
        # Present -> substitued
        res = _template_to_cmd("test_tool", "echo {message!}", {"message": "hello"})
        self.assertEqual(res, "echo hello")

        # Empty -> aborts entire render (returns None)
        res = _template_to_cmd("test_tool", "echo {message!}", {"message": ""})
        self.assertIsNone(res)

        res = _template_to_cmd("test_tool", "echo {message!}", {})
        self.assertIsNone(res)

    def test_default_values(self):
        # Absent -> fallback to default
        res = _template_to_cmd("test_tool", "echo {message=fallback}", {})
        self.assertEqual(res, "echo fallback")

        # Present -> override default
        res = _template_to_cmd("test_tool", "echo {message=fallback}", {"message": "hello"})
        self.assertEqual(res, "echo hello")

    @mock.patch.dict(os.environ, {"MIOS_TEST_ENV": "env_val"})
    def test_env_defaults(self):
        # Environment default present
        res = _template_to_cmd("test_tool", "echo {message=$MIOS_TEST_ENV:fallback}", {})
        self.assertEqual(res, "echo env_val")

        # Environment default absent -> use fallback
        res = _template_to_cmd("test_tool", "echo {message=$MIOS_NONEXISTENT_ENV:fallback}", {})
        self.assertEqual(res, "echo fallback")

    def test_optional_flags(self):
        # Optional present -> emits "FLAG value"
        res = _template_to_cmd("test_tool", "cmd{arg?-f}", {"arg": "value"})
        self.assertEqual(res, "cmd -f value")

        # Optional absent -> emits nothing
        res = _template_to_cmd("test_tool", "cmd{arg?-f}", {})
        self.assertEqual(res, "cmd")

        # Optional without flag
        res = _template_to_cmd("test_tool", "cmd{arg?}", {"arg": "value"})
        self.assertEqual(res, "cmd value")

    def test_splat_varargs(self):
        # Splat present with list -> space-prefixed space-joined individually quoted elements
        res = _template_to_cmd("test_tool", "cmd{args*}", {"args": ["a", "b", "c"]})
        self.assertEqual(res, "cmd a b c")

        # Splat present with scalar -> space-prefixed single element
        res = _template_to_cmd("test_tool", "cmd{args*}", {"args": "single"})
        self.assertEqual(res, "cmd single")

        # Splat absent -> emits nothing
        res = _template_to_cmd("test_tool", "cmd{args*}", {})
        self.assertEqual(res, "cmd")

    def test_list_flattening(self):
        # Any placeholder resolving to a list/tuple is flattened automatically
        res = _template_to_cmd("test_tool", "cmd --files {files}", {"files": ["file1.txt", "file2.txt"]})
        self.assertEqual(res, "cmd --files file1.txt file2.txt")


if __name__ == "__main__":
    unittest.main()
