#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Secure In-Memory Secret Enclave (T-627, T-628).
# AI-related: usr/libexec/mios/sec/secret_mem.py, tests/test-secret-mem.py
"""Automated unit test suite for MiOS Secure In-Memory Secret Enclave."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from secret_mem import SecretBuffer, SecretEnclave


class TestSecretMem(unittest.TestCase):
    def test_context_manager_lifecycle(self):
        """Test that SecretBuffer holds secret within context and wipes on exit."""
        secret_text = "sk_live_super_secret_token_123456789"
        buf_ref = None

        with SecretEnclave.hold(secret_text) as buf:
            buf_ref = buf
            self.assertFalse(buf.is_wiped)
            self.assertEqual(buf.get_bytes().decode("utf-8"), secret_text)

        # After exiting context, buffer must be wiped
        self.assertTrue(buf_ref.is_wiped)
        with self.assertRaises(ValueError):
            buf_ref.get_bytes()

    def test_direct_memory_zeroization(self):
        """Test that underlying memory bytes are strictly overwritten with 0x00."""
        secret_bytes = b"deterministic_zeroization_test_bytes"
        buf = SecretBuffer(secret_bytes)
        self.assertEqual(buf.get_bytes(), secret_bytes)

        # Trigger manual wipe
        buf.wipe()
        self.assertTrue(buf.is_wiped)

        # Inspect internal C buffer directly
        raw_bytes = bytes(buf._c_buf)
        self.assertEqual(raw_bytes, b"\x00" * len(secret_bytes))

    def test_repr_and_str_redaction(self):
        """Test that secret plaintext never leaks into __str__ or __repr__."""
        sensitive_key = "PRIVATE_KEY_DO_NOT_LEAK_IN_LOGS"
        buf = SecretBuffer(sensitive_key)

        str_rep = str(buf)
        repr_rep = repr(buf)

        self.assertNotIn(sensitive_key, str_rep)
        self.assertNotIn(sensitive_key, repr_rep)
        self.assertIn("REDACTED", str_rep)
        buf.wipe()

    def test_core_dump_leak_verification(self):
        """Test simulation of core dump memory search asserting 0 plaintext occurrences."""
        secret_token = "enclave_isolated_api_bearer_9999"
        buf = SecretBuffer(secret_token)

        # Simulate process memory containing buffer contents
        active_memory = b"process_header_data..." + buf.get_bytes() + b"...process_footer"
        self.assertFalse(SecretEnclave.verify_no_core_leak(secret_token, active_memory))

        # Wipe buffer
        buf.wipe()
        wiped_memory = b"process_header_data..." + bytes(buf._c_buf) + b"...process_footer"
        self.assertTrue(SecretEnclave.verify_no_core_leak(secret_token, wiped_memory))

    def test_enclave_status_flags(self):
        """Test reporting of enclave capabilities and kernel security flags."""
        status = SecretEnclave.get_enclave_status()
        self.assertTrue(status["enclave_ready"])
        self.assertIn("madv_dontdump_flag", status)
        self.assertIn("madv_wipeonfork_flag", status)


if __name__ == "__main__":
    unittest.main()
