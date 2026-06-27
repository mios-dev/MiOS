# AI-hint: Stdlib unit tests for mios_promptfmt (pure prompt text-block
#   formatters). No network/DB/stubs needed -- the functions are args-in /
#   string-out. Asserts: empty input -> "" for all three; _council_role_lens
#   builds an SSOT role+strengths lens and degrades to "" with neither;
#   _format_satisfaction_block marks satisfied/unsatisfied + emits the P5
#   write-action-unmet anti-fabrication NOTE; _format_tool_history renders the
#   chronological ledger with ok/FAILED labels.
# AI-related: mios_promptfmt.py
"""Stdlib assert-tests for mios_promptfmt (no network/DB)."""

import unittest

from mios_promptfmt import (
    _council_role_lens,
    _format_satisfaction_block,
    _format_tool_history,
    _build_agent_hint,
    _multi_task_preamble,
)


class TestCouncilRoleLens(unittest.TestCase):
    def test_empty_when_no_role_or_strengths(self):
        self.assertEqual(_council_role_lens("a", {}), "")
        self.assertEqual(_council_role_lens("a", {"role": "  ", "strengths": []}), "")

    def test_role_and_strengths_render(self):
        out = _council_role_lens("coder", {"role": "Engineering",
                                            "strengths": ["git", "tests"]})
        self.assertIn("agent 'coder'", out)
        self.assertIn("the engineering lens", out)        # lowercased
        self.assertIn("strengths: git, tests", out)
        self.assertIn("COUNCIL", out)

    def test_role_only(self):
        out = _council_role_lens("r", {"role": "reasoning"})
        self.assertIn("the reasoning lens", out)
        self.assertNotIn("strengths:", out)


class TestSatisfactionBlock(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_format_satisfaction_block([]), "")

    def test_satisfied_and_unsatisfied_markers(self):
        rows = [
            {"kind": "user_query_satisfied", "summary": "all good"},
            {"kind": "user_query_unsatisfied", "summary": "missed",
             "payload": {"reason": "no tool ran",
                         "failed_tools": [{"tool": "x", "exit_code": 1,
                                           "stderr_preview": "boom"}]}},
        ]
        out = _format_satisfaction_block(rows)
        self.assertIn("✓ satisfied: all good", out)
        self.assertIn("✗ UNSATISFIED: missed", out)
        self.assertIn("reason: no tool ran", out)
        self.assertIn("failed: x exit=1", out)

    def test_p5_write_action_unmet_note(self):
        rows = [{"kind": "user_query_satisfied", "summary": "ok",
                 "payload": {"write_action_unmet": {"hinted": ["save_file"]}}}]
        out = _format_satisfaction_block(rows)
        self.assertIn("NO such action actually ran", out)
        self.assertIn("save_file", out)


class TestToolHistory(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_format_tool_history([]), "")

    def test_ok_and_failed_labels(self):
        rows = [
            {"tool": "read_file", "args": {"path": "a"}, "success": True,
             "result_preview": "data"},
            {"tool": "write_file", "args": {}, "success": False, "exit_code": 2},
        ]
        out = _format_tool_history(rows)
        self.assertIn("[1] read_file(", out)
        self.assertIn("-> ok", out)
        self.assertIn("result: data", out)
        self.assertIn("FAILED (exit=2)", out)


class TestBuildAgentHint(unittest.TestCase):
    def test_minimal_plan_renders_header_and_global_access(self):
        out = _build_agent_hint({}, "coder")
        self.assertIn("target_agent: coder", out)
        self.assertIn("tool_access: GLOBAL", out)

    def test_intent_outcome_hints_and_tool_cards(self):
        out = _build_agent_hint({
            "intent": "fix bug", "intended_outcome": "tests pass",
            "refined_text": "patch X", "hint_tools": ["file_edit"],
            "hint_skills": ["git"],
            "tool_cards": [{"tool": "file_edit", "why": "edit", "args_hint": {"p": 1}}],
        }, "eng")
        self.assertIn("intent: fix bug", out)
        self.assertIn("intended_outcome: tests pass", out)
        self.assertIn("hint_tools: file_edit", out)
        self.assertIn("tool_cards:", out)
        self.assertIn("tool=file_edit", out)


class TestMultiTaskPreamble(unittest.TestCase):
    def test_empty_or_single_returns_blank(self):
        self.assertEqual(_multi_task_preamble([]), "")
        self.assertEqual(_multi_task_preamble([{"title": "solo"}]), "")

    def test_multi_lists_active_and_queued(self):
        out = _multi_task_preamble([{"title": "A"}, {"title": "B"}, {"title": "C"}])
        self.assertIn("Queued 3 tasks", out)
        self.assertIn("Starting now: _A_", out)
        self.assertIn("- B", out)
        self.assertIn("- C", out)


if __name__ == "__main__":
    unittest.main()
