#!/usr/bin/env python3
# AI-hint: Golden fixture test runner for mios-new template generator across all 20 template types.
# AI-related: /usr/libexec/mios/mios-new, /usr/share/mios/templates/, tests/templates/golden/
# AI-functions: generate_golden_snapshots, test_templates_match_golden

import os
import sys
import unittest
import importlib.machinery
import importlib.util
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS_LIBEXEC = os.path.join(ROOT, "usr/libexec/mios")
GOLDEN_DIR = os.path.join(ROOT, "tests/templates/golden")

# Load extensionless script mios-new
mios_new_path = os.path.join(SYS_LIBEXEC, "mios-new")
loader = importlib.machinery.SourceFileLoader("mios_new", mios_new_path)
spec = importlib.util.spec_from_loader(loader.name, loader)
mios_new = importlib.util.module_from_spec(spec)
loader.exec_module(mios_new)

TYPES = [
    "adr", "roadmap-ws", "markdown-doc", "roadmap", "automation-step",
    "drift-check", "bash-verb", "bash-tool", "bash", "python-module",
    "python-test", "python-tool", "rust", "typescript", "powershell",
    "toml-config", "yaml", "json-schema", "systemd-unit", "quadlet"
]

def render_for_type(type_name):
    tmpl_path = os.path.join(ROOT, "usr/share/mios/templates", type_name)
    with open(tmpl_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    name = "0012-sample-test" if type_name == "adr" else "sample-test"
    rendered = mios_new.render_template(content, name, type_name)
    rendered = re.sub(r"\d{4}-\d{2}-\d{2}", "2026-07-17", rendered)
    return rendered

class TestTemplatesGolden(unittest.TestCase):
    def test_all_templates_have_golden_fixtures(self):
        os.makedirs(GOLDEN_DIR, exist_ok=True)
        for t in TYPES:
            golden_file = os.path.join(GOLDEN_DIR, f"{t}.snap")
            expected = render_for_type(t)
            if not os.path.exists(golden_file):
                with open(golden_file, "w", encoding="utf-8", newline="\n") as f:
                    f.write(expected)
            with open(golden_file, "r", encoding="utf-8") as f:
                actual = f.read()
            self.assertEqual(actual, expected, f"Mismatch in golden snapshot for template '{t}'")

if __name__ == "__main__":
    unittest.main()
