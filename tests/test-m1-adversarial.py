#!/usr/bin/env python3
# AI-hint: Adversarial stress testing harness for Milestone 1 (T-382 Self-Healing and T-383 Synthetic QA).
# AI-related: usr/libexec/mios/ai/self_heal.py, usr/libexec/mios/ai/synthetic_qa.py
"""Adversarial Stress Test Suite for Milestone 1: 1. Self-Healing Circuit Breaker & Safe Remediation Engine (T-382)    - Rapid bursts of failures (100 rapid events)    - Multi-unit isolation & interleaved failure/recovery sequences    - Circuit breaker window expiration & quarantine timing    - Invalid / binary / corrupted journal logs    - Malformed & traversal /usr immutability attack paths    - Corrupted state JSON recovery and schema validation    - SafeConfigEditor atomic file operations & error handling  2. Synthetic Training Q&A Data Pipeline (T-383)    - Secret redactor: nested keys (JSON/YAML/TOML/Env), multi-line keys (RSA/EC/SSH), tokens, bearer auth    - Secret redactor: multi-word passwords inside quotes    - Secret redactor: false-positive preservation on standard prose and config keys    - Hierarchical markdown parser: 6-level deep headers, header level jumping, headers inside code blocks    - Unclosed code fences, malformed tables, empty sections, unicode/emoji handling    - Q&A synthesis schema adherence & JSONL single-line validation"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SELF_HEAL_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "self_heal.py")
_SYNTH_QA_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "synthetic_qa.py")

# Import self_heal
spec_sh = importlib.util.spec_from_file_location("self_heal", _SELF_HEAL_PATH)
if spec_sh and spec_sh.loader:
    self_heal = importlib.util.module_from_spec(spec_sh)
    sys.modules[spec_sh.name] = self_heal
    spec_sh.loader.exec_module(self_heal)
else:
    raise ImportError(f"Cannot load self_heal from {_SELF_HEAL_PATH}")

# Import synthetic_qa
spec_sq = importlib.util.spec_from_file_location("synthetic_qa", _SYNTH_QA_PATH)
if spec_sq and spec_sq.loader:
    synthetic_qa = importlib.util.module_from_spec(spec_sq)
    sys.modules[spec_sq.name] = synthetic_qa
    spec_sq.loader.exec_module(synthetic_qa)
else:
    raise ImportError(f"Cannot load synthetic_qa from {_SYNTH_QA_PATH}")

class TestSelfHealAdversarial(unittest.TestCase):
    """Adversarial stress testing for T-382 Self-Healing Code Remediation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mios_adv_selfheal_")
        self.state_file = os.path.join(self.temp_dir, "circuit.json")
        self.log_file = os.path.join(self.temp_dir, "self-heal.log")
        self.breaker = self_heal.CircuitBreaker(max_attempts=3, window_seconds=900.0, state_file=self.state_file)
        self.enforcer = self_heal.ImmutabilityEnforcer()
        self.editor = self_heal.SafeConfigEditor(self.enforcer)
        self.healer = self_heal.SelfHealer(
            circuit_breaker=self.breaker,
            enforcer=self.enforcer,
            editor=self.editor,
            log_file=self.log_file,
        )

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rapid_burst_failures(self):
        """Stress: 100 rapid failure attempts within milliseconds on a single unit."""
        unit = "burst-service.service"
        t0 = 10000.0

        # Attempt 1: allowed
        self.assertTrue(self.breaker.can_attempt(unit, now=t0))
        self.breaker.record_attempt(unit, success=False, now=t0)

        # Attempt 2: allowed
        self.assertTrue(self.breaker.can_attempt(unit, now=t0 + 0.001))
        self.breaker.record_attempt(unit, success=False, now=t0 + 0.001)

        # Attempt 3: allowed, trips breaker upon failure
        self.assertTrue(self.breaker.can_attempt(unit, now=t0 + 0.002))
        tripped = not self.breaker.record_attempt(unit, success=False, now=t0 + 0.002)
        self.assertTrue(tripped)

        # Attempts 4..100: all must be rejected
        for i in range(3, 100):
            ts = t0 + (i * 0.001)
            self.assertFalse(self.breaker.can_attempt(unit, now=ts), f"Attempt {i+1} should have been rejected")
            self.assertTrue(self.breaker.is_quarantined(unit, now=ts))

    def test_multi_unit_isolation_and_interleaved_lifecycle(self):
        """Stress: 10 distinct units failing and recovering in interleaved order."""
        t = 5000.0
        units = [f"unit-{i:02d}.service" for i in range(10)]

        # Fail each unit once
        for u in units:
            self.assertTrue(self.breaker.can_attempt(u, now=t))
            self.breaker.record_attempt(u, success=False, now=t)
            t += 1.0

        # Fail odd units a second time
        for idx, u in enumerate(units):
            if idx % 2 == 1:
                self.assertTrue(self.breaker.can_attempt(u, now=t))
                self.breaker.record_attempt(u, success=False, now=t)
                t += 1.0

        # Fail unit-03 a third time -> should trip unit-03 only
        u3 = "unit-03.service"
        self.assertTrue(self.breaker.can_attempt(u3, now=t))
        self.breaker.record_attempt(u3, success=False, now=t)
        self.assertTrue(self.breaker.is_quarantined(u3, now=t))
        self.assertFalse(self.breaker.can_attempt(u3, now=t))

        # Other units (e.g. unit-00, unit-01, unit-02) must NOT be quarantined
        for u in ["unit-00.service", "unit-01.service", "unit-02.service", "unit-04.service"]:
            self.assertFalse(self.breaker.is_quarantined(u, now=t))
            self.assertTrue(self.breaker.can_attempt(u, now=t))

        # Recovery of unit-01: success=True resets attempts
        u1 = "unit-01.service"
        self.breaker.record_attempt(u1, success=True, now=t)
        st = self.breaker.get_status(u1)
        self.assertEqual(st["recent_attempts"], 0)
        self.assertFalse(st["quarantined"])

    def test_circuit_breaker_window_pruning(self):
        """Verify that failures outside the 900s window are pruned."""
        unit = "expiring.service"
        t0 = 1000.0

        # 2 failures at t0 and t0+100
        self.breaker.record_attempt(unit, success=False, now=t0)
        self.breaker.record_attempt(unit, success=False, now=t0 + 100)
        self.assertEqual(len(self.breaker.attempts[unit]), 2)

        # Advance past 900s window (t0 + 950s)
        # The first failure (t0) is older than 950 - 900 = 50s, so it should be pruned
        t_future = t0 + 950.0
        self.assertTrue(self.breaker.can_attempt(unit, now=t_future))
        self.breaker._prune(unit, now=t_future)
        self.assertEqual(len(self.breaker.attempts[unit]), 1)  # only t0+100 remains

        # Advance past 1100s -> all should be pruned
        self.breaker._prune(unit, now=t0 + 1100.0)
        self.assertNotIn(unit, self.breaker.attempts)

    def test_immutability_enforcement_exhaustive_paths(self):
        """Stress: Exhaustive attack vectors attempting to bypass /usr protection."""
        bad_paths = [
            "/usr",
            "/usr/",
            "/usr/bin/foo",
            "/usr/lib/systemd/system/mios.service",
            "/usr/share/mios/profile.toml",
            "/usr/libexec/mios/ai/self_heal.py",
            "usr/local/bin/custom",
            "\\usr\\bin\\node",
            "C:\\usr\\bin\\binary",
            "D:/usr/share/doc/mios",
            "usr",
        ]
        for p in bad_paths:
            self.assertFalse(self.enforcer.is_path_safe(p), f"Path should be FORBIDDEN: {p}")
            with self.assertRaises(self_heal.PathViolationError, msg=f"Should raise PathViolationError for {p}"):
                self.enforcer.assert_path_safe(p)

        safe_paths = [
            "/etc/mios/profile.toml",
            "/etc/systemd/system/override.conf",
            "/var/lib/mios/pgvector/data",
            "/var/log/mios/self-heal.log",
            "/tmp/temp_patch.toml",
            "/run/mios/runtime.sock",
            os.path.join(self.temp_dir, "etc", "test.conf"),
        ]
        for p in safe_paths:
            self.assertTrue(self.enforcer.is_path_safe(p), f"Path should be SAFE: {p}")

    def test_remediation_aborts_on_usr_modification(self):
        """Stress: Attempting to remediate a target pointing to /usr must abort with PathViolationError."""
        diagnosis = {
            "unit_name": "malicious.service",
            "exit_code": 1,
            "failure_type": "CONFIG_SYNTAX_ERROR",
            "root_cause": "Tampering attempt",
            "target_files": ["/usr/share/mios/profile.toml"],
            "recommended_action": "patch_config",
            "remediation_patch": {
                "file": "/usr/share/mios/profile.toml",
                "content": "hacked = true\n",
            },
        }
        with self.assertRaises(self_heal.PathViolationError):
            self.healer.apply_remediation(diagnosis)

    def test_diagnose_massive_and_corrupted_journal_logs(self):
        """Stress: Huge logs, binary/control characters, mixed error messages."""
        # 1. Empty logs
        evt_empty = self_heal.FailureEvent(unit_name="empty.service", exit_code=1, error_logs=[])
        diag_empty = self.healer.diagnose_failure(evt_empty)
        self.assertEqual(diag_empty["failure_type"], "PROCESS_NONZERO_EXIT")

        # 2. Huge log line (50,000 characters)
        huge_line = "A" * 50000 + " /etc/mios/config.toml syntax error"
        evt_huge = self_heal.FailureEvent(unit_name="huge.service", exit_code=1, error_logs=[huge_line])
        diag_huge = self.healer.diagnose_failure(evt_huge)
        self.assertEqual(diag_huge["failure_type"], "CONFIG_SYNTAX_ERROR")
        self.assertEqual(diag_huge["target_files"], ["/etc/mios/config.toml"])

        # 3. Unprintable / control characters
        control_chars = "\x00\x01\x02\x03\x04\x1b[31mFATAL: /var/lib/mios/missing_dir directory does not exist\x1b[0m"
        evt_ctrl = self_heal.FailureEvent(unit_name="ctrl.service", exit_code=1, error_logs=[control_chars])
        diag_ctrl = self.healer.diagnose_failure(evt_ctrl)
        self.assertEqual(diag_ctrl["failure_type"], "MISSING_VAR_DIRECTORY")

    def test_safe_config_editor_atomicity_and_parent_creation(self):
        """Verify atomic replacement creates nested directory and backs up existing file."""
        nested_file = os.path.join(self.temp_dir, "etc", "deep", "nested", "service.conf")
        self.editor.patch_file(nested_file, "setting = 1\n", create_backup=True)
        self.assertTrue(os.path.exists(nested_file))

        # Patch again with backup
        self.editor.patch_file(nested_file, "setting = 2\n", create_backup=True)
        with open(nested_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "setting = 2\n")

        # Check backup file exists
        parent_dir = os.path.dirname(nested_file)
        bak_files = [f for f in os.listdir(parent_dir) if "service.conf.bak" in f]
        self.assertEqual(len(bak_files), 1)

class TestSyntheticQAAdversarial(unittest.TestCase):
    """Adversarial stress testing for T-383 Synthetic Training Q&A Data Pipeline."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mios_adv_synqa_")
        self.parser = synthetic_qa.MarkdownHierarchicalParser()
        self.redactor = synthetic_qa.SecretRedactor()
        self.synthesizer = synthetic_qa.QASynthesizer()
        self.pipeline = synthetic_qa.SyntheticQAPipeline(
            parser=self.parser,
            redactor=self.redactor,
            synthesizer=self.synthesizer,
        )

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_secret_redactor_nested_keys_and_formats(self):
        """Stress: Various nested assignment syntaxes in JSON, YAML, TOML, and Env."""
        cases = [
            ('password = "SecretPassword123!"', 'password: "<REDACTED_SECRET>"'),
            ('passwd = \'admin_pass_999\'', 'passwd: "<REDACTED_SECRET>"'),
            ('secret_key = "abc123secret"', 'secret_key: "<REDACTED_SECRET>"'),
            ('client_secret = "xyz987secret"', 'client_secret: "<REDACTED_SECRET>"'),
            ('  password: SuperSecretYAML', '  password: "<REDACTED_SECRET>"'),
            ('  secret_key: "TopSecret"', '  secret_key: "<REDACTED_SECRET>"'),
            ('PASSWORD: MyPassword', 'PASSWORD: "<REDACTED_SECRET>"'),
            ('Secret_Key: "Key123"', 'Secret_Key: "<REDACTED_SECRET>"'),
        ]
        for inp, expected_substring in cases:
            redacted = self.redactor.redact(inp)
            self.assertIn(expected_substring, redacted, f"Failed on input: {inp}")

    def test_secret_redactor_multiline_private_keys(self):
        """Stress: Multi-line RSA, EC, and OPENSSH private keys."""
        rsa_key = """-----BEGIN RSA PRIVATE KEY----- MIIEowIBAAKCAQEA0Z3v9x4p... ...MULTILINE DATA... -----END RSA PRIVATE KEY-----"""

        ec_key = """-----BEGIN EC PRIVATE KEY----- MHcCAQEEIIz4... -----END EC PRIVATE KEY-----"""

        ssh_key = """-----BEGIN OPENSSH PRIVATE KEY----- b3BlbnNzaC1rZXktdjEAAAAA... -----END OPENSSH PRIVATE KEY-----"""

        for key in [rsa_key, ec_key, ssh_key]:
            wrapped = f"Config header\n{key}\nConfig footer"
            redacted = self.redactor.redact(wrapped)
            self.assertNotIn("MULTILINE DATA", redacted)
            self.assertNotIn("b3BlbnNzaC", redacted)
            self.assertIn("<REDACTED_PRIVATE_KEY>", redacted)

    def test_secret_redactor_tokens_and_ssh_keys(self):
        """Stress: API tokens, GitHub PATs, Bearer headers, and public keys."""
        text = (
            "API key: sk-abcdef1234567890abcdef1234567890\n"
            "PAT: ghp_123456789012345678901234567890123456\n"
            "Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.ZRrHA1JJ\n"
            "Key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGo4 user@host\n"
            "Key2: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC user@host\n"
        )
        redacted = self.redactor.redact(text)
        self.assertIn("<REDACTED_API_KEY>", redacted)
        self.assertIn("<REDACTED_GITHUB_TOKEN>", redacted)
        self.assertIn("<REDACTED_BEARER_TOKEN>", redacted)
        self.assertIn("<REDACTED_SSH_KEY>", redacted)
        self.assertNotIn("sk-abcdef1234567890abcdef1234567890", redacted)
        self.assertNotIn("ghp_123456789012345678901234567890123456", redacted)

    def test_secret_redactor_false_positive_preservation(self):
        """Ensure standard architectural text and parameter names are NOT corrupted."""
        benign_prose = (
            "The system prompt defines the authentication architecture.\n"
            "All passwords must meet complexity requirements defined in the security manual.\n"
            "The secret key derivation function uses HKDF-SHA256.\n"
            "Token bucket rate limiting is applied at the gateway.\n"
        )
        redacted = self.redactor.redact(benign_prose)
        self.assertIn("complexity requirements", redacted)
        self.assertIn("HKDF-SHA256", redacted)
        self.assertIn("Token bucket", redacted)

    def test_parser_deeply_nested_headers_and_level_jumping(self):
        """Stress: 6 header levels and abrupt jumps (e.g. # to ####)."""
        md_text = """# Level 1 Title

This is the top level overview chapter of the system architecture.

## Level 2 Component

Description of the component with enough words to satisfy word count threshold.

### Level 3 Subsystem

Detailed subsystem description containing architecture rules and operational details.

###### Level 6 Deep Leaf

Extremely nested operational parameter specifications with full details.

## Level 2 Sibling

A sibling section at level 2 popping all intermediate headers off stack."""
        chunks = self.parser.parse_text(md_text, doc_path="doc/deep.md")
        self.assertGreaterEqual(len(chunks), 4)

        # Check leaf chunk hierarchy
        leaf = next((c for c in chunks if "Level 6 Deep Leaf" in c.section_title), None)
        self.assertIsNotNone(leaf)
        self.assertIn("Level 1 Title", leaf.hierarchy)
        self.assertIn("Level 2 Component", leaf.hierarchy)
        self.assertIn("Level 3 Subsystem", leaf.hierarchy)

        # Check sibling chunk hierarchy
        sibling = next((c for c in chunks if "Level 2 Sibling" in c.section_title), None)
        self.assertIsNotNone(sibling)
        self.assertIn("Level 1 Title", sibling.hierarchy)
        self.assertNotIn("Level 3 Subsystem", sibling.hierarchy)
        self.assertNotIn("Level 6 Deep Leaf", sibling.hierarchy)

    def test_parser_headers_inside_code_blocks(self):
        """Stress: Markdown headers inside code fences must NOT be parsed as headers."""
        md_text = """# Outer Header

Here is an example python script containing comments with pound signs:

```python
# This is a python comment, not a markdown header
# Another comment
def hello():
    return True
```

This section concludes the explanation with sufficient descriptive words."""
        chunks = self.parser.parse_text(md_text, doc_path="doc/code_block.md")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].section_title, "Outer Header")
        self.assertEqual(len(chunks[0].code_blocks), 1)
        self.assertIn("# This is a python comment", chunks[0].code_blocks[0]["code"])

    def test_parser_unclosed_code_fence_and_malformed_tables(self):
        """Stress: Unclosed code fences and malformed tables must not crash."""
        md_text = """# Unclosed Fence Test

Here is text before unclosed fence.

```sh
echo "unclosed code fence"

| col1 | col2 |
| --- | --- |
| val1 | val2 |

More descriptive text to satisfy the minimum word count threshold for this chunk."""
        chunks = self.parser.parse_text(md_text, doc_path="doc/unclosed.md")
        self.assertEqual(len(chunks), 1)

    def test_parser_unicode_and_special_characters(self):
        """Stress: CJK, emojis, mathematical symbols, special markdown characters."""
        md_text = """# 🚀 MiOS 架构规范 (Architecture)

MiOS 是一个不可变的 bootc/OCI Fedora 工作站与本地 AI 操作系统 🌟。

## 🔐 安全与加密 (Security & Crypto)

采用 Ed25519 签名与 ChaCha20-Poly1305 AEAD 加密算法，保证跨节点通信安全。
数学公式: $\\mathcal{H}(k, m) = \\text{HMAC-SHA256}(k, m)$。"""
        chunks = self.parser.parse_text(md_text, doc_path="doc/unicode.md")
        self.assertGreaterEqual(len(chunks), 2)
        sec_chunk = chunks[1]
        self.assertIn("安全与加密", sec_chunk.section_title)
        self.assertIn("ChaCha20-Poly1305", sec_chunk.content)

    def test_qa_synthesis_and_jsonl_export_schema_compliance(self):
        """Stress: End-to-end multi-chunk generation, redaction, and strict JSONL verification."""
        test_file = os.path.join(self.temp_dir, "input.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                "# Secret Storage Subsystem\n\n"
                "The secret storage subsystem manages sensitive configurations.\n\n"
                "## Credential Provisioning\n\n"
                "Credentials are provided via configuration files:\n\n"
                "```toml\n"
                "[auth]\n"
                "password = 'UnredactedSecretPassword123!'\n"
                "api_key = 'sk-123456789012345678901234567890'\n"
                "```\n\n"
                "This ensures the service can authenticate securely against local endpoints.\n"
            )

        chunks = self.pipeline.harvest_docs([self.temp_dir])
        records = self.pipeline.generate_dataset(chunks, redact=True)
        self.assertGreaterEqual(len(records), 1)

        # Verify no secret leaked into synthesized records
        for rec in records:
            for msg in rec["messages"]:
                self.assertNotIn("UnredactedSecretPassword123!", msg["content"])
                self.assertNotIn("sk-123456789012345678901234567890", msg["content"])

        # Export and verify line-by-line JSON validity
        out_jsonl = os.path.join(self.temp_dir, "dataset.jsonl")
        self.pipeline.export_jsonl(records, out_jsonl)

        with open(out_jsonl, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), len(records))
        for line in lines:
            parsed = json.loads(line.strip())
            self.assertIn("messages", parsed)
            self.assertIn("metadata", parsed)
            # Verify system prompt identity
            sys_msg = parsed["messages"][0]
            self.assertEqual(sys_msg["role"], "system")
            self.assertIn("MiOS-Opencode", sys_msg["content"])

def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestSelfHealAdversarial),
        loader.loadTestsFromTestCase(TestSyntheticQAAdversarial),
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
