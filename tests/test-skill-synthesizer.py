#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-ORCH automatic skill synthesis.
# AI-related: usr/libexec/mios/ai/skill-synthesizer.py
"""Automated tests for WS-ORCH trace distillation and SKILL.md markdown generation."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SYNTH_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "skill-synthesizer.py")

spec = importlib.util.spec_from_file_location("skill_synthesizer", _SYNTH_PATH)
if spec and spec.loader:
    skill_synthesizer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = skill_synthesizer
    spec.loader.exec_module(skill_synthesizer)
else:
    raise ImportError(f"Could not load skill-synthesizer module from {_SYNTH_PATH}")


class TestSkillSynthesizer(unittest.TestCase):
    """Validates SKILL.md template generation and step formatting."""

    def test_skill_synthesis(self):
        synth = skill_synthesizer.SkillSynthesizer()
        tools = ["view_file", "replace_file_content", "run_command"]
        doc = synth.synthesize_skill_md(
            skill_name="code_refactor_pipeline",
            description="Automated multi-file code refactoring and validation",
            tool_sequence=tools
        )
        self.assertIn("name: code_refactor_pipeline", doc)
        self.assertIn("Step 1: Use `view_file`", doc)
        self.assertIn("Step 2: Use `replace_file_content`", doc)
        self.assertIn("Step 3: Use `run_command`", doc)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSkillSynthesizer)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
