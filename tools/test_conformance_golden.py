#!/usr/bin/env python3
# AI-hint: Golden CLI fixture test runner for check-template-conformance CLI output and behavior.
# AI-related: /usr/libexec/mios/check-template-conformance, tests/templates/conform-cli/
# AI-functions: test_conformance_golden_cli

import os
import sys
import unittest
import subprocess
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_BIN = os.path.join(ROOT, "usr/libexec/mios/check-template-conformance")
GOLDEN_DIR = os.path.join(ROOT, "tests/templates/conform-cli")

class TestConformanceGolden(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mios_conform_test_")
        # Copy mios.toml for templates matching config
        os.makedirs(os.path.join(self.tmpdir, "usr/share/mios"), exist_ok=True)
        shutil.copy(
            os.path.join(ROOT, "usr/share/mios/mios.toml"),
            os.path.join(self.tmpdir, "usr/share/mios/mios.toml")
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def run_check(self, root_dir, max_unconforming=0):
        env = os.environ.copy()
        env["MIOS_THEME_ROOT"] = ROOT
        env["MIOS_TOML_ROOT"] = root_dir
        cmd = [sys.executable, CHECK_BIN, "--root", root_dir, "--max-unconforming", str(max_unconforming)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        return res.returncode, res.stdout, res.stderr

    def test_conformant_mini_tree(self):
        # Create a conformant python tool
        bin_dir = os.path.join(self.tmpdir, "usr/libexec/mios")
        os.makedirs(bin_dir, exist_ok=True)
        fpath = os.path.join(bin_dir, "mios-test-tool.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\n# AI-hint: Test tool\n# AI-related: none\n# AI-functions: main\n\ndef main():\n    pass\n")

        code, stdout, stderr = self.run_check(self.tmpdir)
        self.assertEqual(code, 0)
        self.assertIn("[conformance] checked=", stdout)
        self.assertIn("unconforming=0", stdout)

    def test_missing_ai_hint_header(self):
        bin_dir = os.path.join(self.tmpdir, "usr/libexec/mios")
        os.makedirs(bin_dir, exist_ok=True)
        fpath = os.path.join(bin_dir, "mios-no-hint.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\n\ndef main():\n    pass\n")

        code, stdout, stderr = self.run_check(self.tmpdir)
        self.assertEqual(code, 1)
        self.assertIn("Missing AI-hint header", stderr)

if __name__ == "__main__":
    unittest.main()
