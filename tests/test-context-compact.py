#!/usr/bin/env python3
# AI-hint: Automated unit test suite for semantic KV-cache context compaction and episodic trajectory retention.
# AI-related: usr/lib/mios/agent-pipe/mios_kv_compact.py, usr/share/mios/mios.toml
"""Unit and integration test suite for KVCompactEngine and mios_kv_compact CLI (T-548)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe", "mios_kv_compact.py")

spec = importlib.util.spec_from_file_location("mios_kv_compact", _TARGET_PATH)
if spec and spec.loader:
    mios_kv_compact = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mios_kv_compact
    spec.loader.exec_module(mios_kv_compact)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestContextCompact(unittest.TestCase):
    """Test suite for context compaction thresholds, system prompt immutability, and episodic archives."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-test-compact-")
        self.episode_dir = os.path.join(self.tmpdir.name, "episodes")
        os.makedirs(self.episode_dir, exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_estimate_tokens(self):
        msg = {"role": "user", "content": "Hello MiOS agent pipe"}
        tokens = mios_kv_compact.estimate_tokens(msg)
        self.assertGreater(tokens, 0)

        msgs = [
            {"role": "system", "content": "System identity"},
            {"role": "user", "content": "User request"},
            {"role": "assistant", "content": "Assistant answer"},
        ]
        total_tokens = mios_kv_compact.estimate_tokens(msgs)
        self.assertGreater(total_tokens, tokens)

    def test_extract_factual_anchors(self):
        text = "Modified file usr/libexec/mios/sec/livepatch_mgr.py and completed task T-545."
        anchors = mios_kv_compact.extract_factual_anchors(text)
        self.assertTrue(any("livepatch_mgr.py" in a for a in anchors))
        self.assertIn("T-545", anchors)

    def test_should_compact_threshold(self):
        engine = mios_kv_compact.KVCompactEngine(max_tokens=1000, compact_threshold=0.75, mock=True)
        small_msgs = [{"role": "user", "content": "Small prompt"}]
        self.assertFalse(engine.should_compact(small_msgs))

        # Long conversation exceeding 750 tokens (~3000 chars)
        large_msgs = [
            {"role": "system", "content": "System prompt"},
            {"role": "assistant", "content": "Very long output text with logs and tool execution " * 100},
        ]
        self.assertTrue(engine.should_compact(large_msgs))

    def test_system_prompt_immutability(self):
        engine = mios_kv_compact.KVCompactEngine(episode_dir=self.episode_dir, mock=True)
        canonical_system_prompt = "You are MiOS Master AI under Architectural Law 5."
        messages = [
            {"role": "system", "content": canonical_system_prompt},
            {"role": "user", "content": "Query 1"},
            {"role": "assistant", "content": "Verbose tool trace " * 60},
            {"role": "tool", "name": "view_file", "content": "Long file dump line " * 80},
            {"role": "user", "content": "Latest query"},
        ]

        res = engine.compact_messages(messages, force=True)
        self.assertTrue(res["compacted"])

        compacted_messages = res["messages"]
        self.assertEqual(compacted_messages[0]["role"], "system")
        self.assertEqual(compacted_messages[0]["content"], canonical_system_prompt)

    def test_token_reduction_and_milestone_creation(self):
        engine = mios_kv_compact.KVCompactEngine(episode_dir=self.episode_dir, mock=True)
        messages = [
            {"role": "system", "content": "System instructions."},
            {"role": "user", "content": "Step 1: Check hardware status."},
            {"role": "assistant", "content": "Running lspci and dmesg tools... " * 50},
            {"role": "tool", "name": "bash", "content": "00:02.0 VGA compatible controller Intel Corporation... " * 100},
            {"role": "assistant", "content": "Step 2: Allocate model matrix... " * 50},
            {"role": "tool", "name": "bash", "content": "Allocated 8GB VRAM for Qwen2.5-Coder... " * 100},
            {"role": "user", "content": "Step 3: What is the final allocation?"},
            {"role": "assistant", "content": "Ready for final confirmation."},
        ]

        res = engine.compact_messages(messages, preserve_recent_turns=2, force=True)
        self.assertTrue(res["compacted"])
        self.assertLess(res["final_tokens"], res["initial_tokens"])
        self.assertLess(res["reduction_ratio"], 0.60)

        compacted_msgs = res["messages"]
        self.assertTrue(any(m.get("_compacted_milestone") for m in compacted_msgs))
        self.assertEqual(compacted_msgs[-1]["content"], "Ready for final confirmation.")
        self.assertEqual(compacted_msgs[-2]["content"], "Step 3: What is the final allocation?")

    def test_episodic_archive_persistence(self):
        engine = mios_kv_compact.KVCompactEngine(episode_dir=self.episode_dir, mock=False)
        messages = [
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "Do task"},
            {"role": "assistant", "content": "Heavy processing " * 50},
            {"role": "user", "content": "Final step"},
        ]

        res = engine.compact_messages(messages, session_id="test-session-123", force=True)
        self.assertTrue(res["compacted"])
        self.assertTrue(res["archive"]["archived"])
        self.assertTrue(os.path.isfile(res["archive"]["path"]))

        with open(res["archive"]["path"], "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["session_id"], "test-session-123")
        self.assertEqual(data["turns_count"], 4)

    def test_multi_turn_60_turns_compaction(self):
        engine = mios_kv_compact.KVCompactEngine(episode_dir=self.episode_dir, mock=True)
        messages = [{"role": "system", "content": "System prompt"}]
        for i in range(30):
            messages.append({"role": "user", "content": f"Turn {i} question regarding file_{i}.py"})
            messages.append({"role": "assistant", "content": f"Turn {i} verbose response log " * 20})

        self.assertEqual(len(messages), 61)
        res = engine.compact_messages(messages, force=True, preserve_recent_turns=4)
        self.assertTrue(res["compacted"])
        # Head (1) + Milestone (1) + Tail (4) = 6 messages
        self.assertEqual(len(res["messages"]), 6)
        self.assertEqual(res["messages"][0]["role"], "system")
        self.assertTrue(res["messages"][1].get("_compacted_milestone"))

    def test_cli_execution_mock(self):
        with patch.object(sys, "argv", ["mios_kv_compact.py", "--mock", "--compact", "--json"]):
            code = mios_kv_compact.main()
            self.assertEqual(code, 0)

if __name__ == "__main__":
    unittest.main()
