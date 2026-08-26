#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI / PROMPT-01 contextual prompt compression and token pruning.
# AI-related: usr/libexec/mios/prompt/pruning.py, usr/share/doc/mios/manual/ch02-architecture.md
"""
Automated unit tests for linguistic token pruning, AST/code syntax preservation,
message list compression, and CLI execution.
"""

from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "prompt"))

try:
    import pruning
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "pruning", os.path.join(_ROOT, "usr", "libexec", "mios", "prompt", "pruning.py")
    )
    if _spec and _spec.loader:
        pruning = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(pruning)
    else:
        raise


class TestPromptPruning(unittest.TestCase):
    """Validates compression ratio, syntax preservation, and header deduplication."""

    def setUp(self):
        self.pruner = pruning.PromptPruner()

    def test_filler_pruning_ratio(self):
        sample_context = (
            "Please be advised that in order to configure the system properly, "
            "it is critically necessary to ensure that the following parameters are set: "
            "port=8080 host=127.0.0.1. Furthermore, we would like to note that default values apply. "
            "If you have any further questions, please let me know. Best regards!"
        )
        compressed, stats = self.pruner.compress(sample_context, target_ratio=0.25)
        self.assertGreaterEqual(stats["reduction_ratio"], 0.20)
        self.assertIn("port=8080", compressed)
        self.assertIn("host=127.0.0.1", compressed)
        self.assertNotIn("Please be advised that", compressed)
        self.assertNotIn("If you have any further questions", compressed)

    def test_code_syntax_preservation(self):
        raw_code = (
            "def calculate_hash(key: str, salt: bytes, rounds: int = 1000) -> str:\n"
            "    # Internal HMAC digest calculation\n"
            "    val = hmac.new(salt, key.encode('utf-8'), hashlib.sha256).hexdigest()\n"
            "    return val[:32]"
        )
        code_block = f"```python\n{raw_code}\n```"
        prompt = (
            "As an AI language model, I would be happy to help you with that.\n"
            "Here is the function you requested:\n"
            f"{code_block}\n"
            "Let me know if you need anything else!"
        )
        compressed, stats = self.pruner.compress(prompt, preserve_code=True)
        self.assertIn(raw_code, compressed)
        self.assertIn("```python", compressed)
        self.assertNotIn("As an AI language model", compressed)
        self.assertNotIn("Let me know if you need anything else", compressed)

        # Verify the python code inside is still 100% valid AST
        parsed = ast.parse(raw_code)
        self.assertIsInstance(parsed, ast.Module)

    def test_inline_code_preservation(self):
        text = (
            "Please note that you should run `systemctl restart mios-llm-light.service` "
            "in order to apply the new configuration to `/etc/mios/profile.toml`."
        )
        compressed, stats = self.pruner.compress(text, preserve_code=True)
        self.assertIn("`systemctl restart mios-llm-light.service`", compressed)
        self.assertIn("`/etc/mios/profile.toml`", compressed)

    def test_message_list_pruning(self):
        messages = [
            {
                "role": "system",
                "content": "As an AI assistant, it is important to note that you must respond strictly in JSON."
            },
            {
                "role": "user",
                "content": "Please be advised that I need the status of port 8080."
            },
            {
                "role": "assistant",
                "content": "```json\n{\"port\": 8080, \"status\": \"active\"}\n```\nHope this helps!"
            }
        ]
        pruned_msgs, stats = self.pruner.prune_messages(messages, target_ratio=0.25)
        self.assertEqual(len(pruned_msgs), 3)
        self.assertIn("respond strictly in JSON", pruned_msgs[0]["content"])
        self.assertNotIn("As an AI assistant", pruned_msgs[0]["content"])
        self.assertNotIn("Please be advised that", pruned_msgs[1]["content"])
        self.assertIn("{\"port\": 8080, \"status\": \"active\"}", pruned_msgs[2]["content"])
        self.assertNotIn("Hope this helps!", pruned_msgs[2]["content"])
        self.assertGreater(stats["reduction_ratio"], 0.15)
        self.assertGreater(stats["saved_tokens_approx"], 0)

    def test_empty_and_whitespace_edge_cases(self):
        # Empty string
        comp, stats = self.pruner.compress("")
        self.assertEqual(comp, "")
        self.assertEqual(stats["reduction_ratio"], 0.0)

        # Whitespace string
        comp_ws, stats_ws = self.pruner.compress("   \n\t\n   ")
        self.assertEqual(comp_ws, "   \n\t\n   ")

        # Single word
        comp_single, stats_single = self.pruner.compress("Status")
        self.assertEqual(comp_single, "Status")

        # Empty messages list
        pruned_empty, stats_empty = self.pruner.prune_messages([])
        self.assertEqual(pruned_empty, [])
        self.assertEqual(stats_empty["original_chars"], 0)

    def test_markdown_formatting_normalization(self):
        doc = (
            "# System Architecture\n\n"
            "# System Architecture\n\n"
            "---\n---\n---\n\n\n\n"
            "This section details the node interconnect.\n"
        )
        compressed, stats = self.pruner.compress(doc)
        # Should deduplicate consecutive identical headers
        self.assertEqual(compressed.count("# System Architecture"), 1)
        # Should collapse horizontal rules
        self.assertNotIn("---\n---", compressed)
        # Should collapse excessive blank lines
        self.assertNotIn("\n\n\n", compressed)

    def test_long_retrieval_context_compression(self):
        verbose_retrieval_context = (
            "# Documentation for MiOS Node Federation\n\n"
            "Please be advised that in order to establish a secure peer connection, "
            "it is critically necessary to ensure that each node utilizes an Ed25519 signing key. "
            "Furthermore, we would like to note that prior to transmitting any payload, "
            "the node conducts an investigation of the peer's AgentCard signature.\n\n"
            "```python\n"
            "def verify_node(node_id: int, card_signature: bytes) -> bool:\n"
            "    # Validate against trusted registry\n"
            "    pubkey = get_trusted_key(node_id)\n"
            "    return ed25519.verify(pubkey, card_signature)\n"
            "```\n\n"
            "Due to the fact that network latency can vary, a large number of nodes "
            "give consideration to caching verified credentials at the present time. "
            "It is worth noting that subsequent to verification, heartbeats are dispatched every 5 seconds. "
            "If you have any further questions, please let me know. Best regards!"
        )
        compressed, stats = self.pruner.compress(verbose_retrieval_context, target_ratio=0.25)
        self.assertGreaterEqual(stats["reduction_ratio"], 0.20)
        self.assertIn("def verify_node(node_id: int, card_signature: bytes) -> bool:", compressed)
        self.assertIn("get_trusted_key(node_id)", compressed)
        self.assertNotIn("Please be advised that", compressed)
        self.assertNotIn("Furthermore, we would like to note that", compressed)

    def test_cli_execution_text_mode(self):
        input_text = "Please be advised that the port is 8080. Hope this helps!"
        with patch("sys.stdin", io.StringIO(input_text)), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = pruning.main(["--stats"])
            self.assertEqual(exit_code, 0)
            out = mock_stdout.getvalue()
            self.assertIn("port is 8080", out)
            self.assertNotIn("Please be advised that", out)

    def test_cli_execution_stats_only(self):
        input_text = "Please be advised that in order to run tests, execute pytest. Cheers!"
        with patch("sys.stdin", io.StringIO(input_text)), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = pruning.main(["--stats-only"])
            self.assertEqual(exit_code, 0)
            data = json.loads(mock_stdout.getvalue())
            self.assertIn("reduction_ratio", data)
            self.assertIn("original_chars", data)
            self.assertGreater(data["reduction_ratio"], 0.20)

    def test_cli_execution_json_messages(self):
        msgs = [{"role": "user", "content": "Please be advised that I need help. Hope this helps!"}]
        with patch("sys.stdin", io.StringIO(json.dumps(msgs))), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = pruning.main(["--json"])
            self.assertEqual(exit_code, 0)
            data = json.loads(mock_stdout.getvalue())
            self.assertEqual(len(data), 1)
            self.assertNotIn("Please be advised that", data[0]["content"])

    def test_cli_file_input_output(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as in_f:
            in_f.write("Please be advised that host is localhost. Best regards!")
            in_path = in_f.name

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as out_f:
            out_path = out_f.name

        try:
            exit_code = pruning.main(["-i", in_path, "-o", out_path])
            self.assertEqual(exit_code, 0)
            with open(out_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Host is localhost", content)
            self.assertNotIn("Please be advised that", content)
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_cli_error_cases(self):
        # Nonexistent file
        exit_code = pruning.main(["-i", "/nonexistent/file/path/here.txt"])
        self.assertEqual(exit_code, 1)

        # Invalid JSON
        with patch("sys.stdin", io.StringIO("NOT_VALID_JSON")):
            exit_code = pruning.main(["--json"])
            self.assertEqual(exit_code, 1)

    def test_multipart_messages_with_non_text(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please note that I want to analyze this image. Hope this helps!"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image.png"}
                    }
                ]
            }
        ]
        pruned_msgs, stats = self.pruner.prune_messages(messages)
        self.assertEqual(len(pruned_msgs), 1)
        parts = pruned_msgs[0]["content"]
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[1]["type"], "image_url")
        self.assertNotIn("Please note that", parts[0]["text"])
        self.assertIn("I want to analyze this image", parts[0]["text"])

    def test_multilanguage_code_blocks_preservation(self):
        multilang = (
            "Please be advised that you must configure the following files:\n\n"
            "```bash\n"
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "echo \"Starting container...\"\n"
            "podman run -d --name mios-db -p 5432:5432 pgvector:latest\n"
            "```\n\n"
            "And write the Rust connector:\n\n"
            "```rust\n"
            "pub fn connect_db(url: &str) -> Result<Pool, Error> {\n"
            "    let pool = Pool::new(url)?;\n"
            "    Ok(pool)\n"
            "}\n"
            "```\n\n"
            "Let me know if you need anything else!"
        )
        compressed, stats = self.pruner.compress(multilang, preserve_code=True)
        self.assertIn("podman run -d --name mios-db -p 5432:5432 pgvector:latest", compressed)
        self.assertIn("pub fn connect_db(url: &str) -> Result<Pool, Error>", compressed)
        self.assertNotIn("Please be advised that", compressed)
        self.assertNotIn("Let me know if you need anything else", compressed)

    def test_target_ratio_bounds(self):
        text = "Please be advised that in order to start, run mios. Best regards!"
        # Target ratio 0.0 should still produce valid result
        c0, s0 = self.pruner.compress(text, target_ratio=0.0)
        self.assertIsNotNone(c0)
        self.assertIn("original_chars", s0)

        # Target ratio 0.5 should perform aggressive pruning
        c5, s5 = self.pruner.compress(text, target_ratio=0.5)
        self.assertGreater(s5["reduction_ratio"], 0.30)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPromptPruning)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
