#!/usr/bin/env python3
# AI-hint: Sibling unit test for mios-text-edit view directory depth logic (T-112).

import os
import sys
import json
import subprocess
import tempfile
import unittest

class TestMiosListDir(unittest.TestCase):
    def setUp(self):
        self.script_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../../../libexec/mios/mios-text-edit"
        ))
        if not os.path.exists(self.script_path):
            self.script_path = "/usr/libexec/mios/mios-text-edit"

    def test_depth_1_listing(self):
        """Verify that mios-text-edit view with --depth 1 lists only immediate children."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1.txt")
            with open(file1, "w") as f:
                f.write("hello")
            
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            
            file2 = os.path.join(subdir, "file2.txt")
            with open(file2, "w") as f:
                f.write("world")

            cmd = [sys.executable, self.script_path, "view", tmpdir, "--depth", "1"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            data = json.loads(res.stdout.strip())
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("kind"), "dir")
            
            entries = data.get("entries", [])
            self.assertIn("file1.txt", entries)
            self.assertIn("subdir/", entries)
            self.assertNotIn(os.path.join("subdir", "file2.txt"), entries)

if __name__ == "__main__":
    unittest.main()
