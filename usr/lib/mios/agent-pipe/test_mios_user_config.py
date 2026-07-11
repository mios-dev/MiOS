#!/usr/bin/env python3
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Resolve workspace path relative to this file
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
libexec_dir = os.path.join(base_dir, "usr/libexec/mios")

import importlib.util
spec = importlib.util.spec_from_file_location("muc", os.path.join(libexec_dir, "materialize-user-config.py"))
muc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(muc)

class TestMiosUserConfig(unittest.TestCase):

    def test_parse_simple_toml_tomllib(self):
        # Create a temp TOML file containing complex TOML features (comments, inline tables, etc)
        temp_toml = "/tmp/test_complex_spec.toml"
        content = """
        # Global settings comment
        [ai]
        db_authoritative = true
        models = ["granite", "gpt-oss"] # inline comment
        
        [mcp.servers.github]
        enabled = true
        args = { token = "xyz", repo = "mios" } # inline table
        """
        with open(temp_toml, "w") as f:
            f.write(content)
            
        try:
            parsed = muc.parse_simple_toml(temp_toml)
            self.assertEqual(parsed["ai"]["db_authoritative"], True)
            self.assertEqual(parsed["ai"]["models"], ["granite", "gpt-oss"])
            self.assertEqual(parsed["mcp"]["servers"]["github"]["enabled"], True)
            self.assertEqual(parsed["mcp"]["servers"]["github"]["args"]["token"], "xyz")
        finally:
            if os.path.exists(temp_toml):
                os.remove(temp_toml)

    def test_path_escape_guard(self):
        # We want to check the logic of preventing path traversal home-escape.
        # Home: /home/bob
        # Target Rel: ../bob-evil/.bashrc
        # Resolved target: /home/bob-evil/.bashrc
        home_dir = "/home/bob"
        
        # Test case 1: Normal path inside home
        rel_path_ok = ".config/mios/mios.toml"
        target_ok = os.path.abspath(os.path.join(home_dir, rel_path_ok))
        home_abs = os.path.abspath(home_dir)
        self.assertEqual(os.path.commonpath([home_abs, target_ok]), home_abs)

        # Test case 2: Traverse escape path
        rel_path_escape = "../bob-evil/.bashrc"
        target_escape = os.path.abspath(os.path.join(home_dir, rel_path_escape))
        self.assertNotEqual(os.path.commonpath([home_abs, target_escape]), home_abs)

if __name__ == "__main__":
    unittest.main()
