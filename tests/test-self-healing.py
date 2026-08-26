#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-382 Autonomous Self-Healing Code Remediation Agent.
# AI-related: usr/libexec/mios/ai/self_heal.py, usr/lib/systemd/system/mios-self-heal.service
"""
Automated unit tests for systemd failure parsing, journald log diagnosis,
circuit breaker rate limiting, /usr immutability protection, and RCA logging.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SELF_HEAL_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "self_heal.py")

spec = importlib.util.spec_from_file_location("self_heal", _SELF_HEAL_PATH)
if spec and spec.loader:
    self_heal = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = self_heal
    spec.loader.exec_module(self_heal)
else:
    raise ImportError(f"Could not load self_heal module from {_SELF_HEAL_PATH}")


class TestSelfHealing(unittest.TestCase):
    """Validates self-healing agent diagnostics, circuit breaker, and immutability invariants."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mios_test_selfheal_")
        self.log_file = os.path.join(self.temp_dir, "self-heal.log")
        self.state_file = os.path.join(self.temp_dir, "circuit.json")
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
        # Clean up temp files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_failure_event_serialization(self):
        event = self_heal.FailureEvent(
            unit_name="mios-test.service",
            exit_code=2,
            error_logs=["Error: invalid token on line 4", "Fatal config parse fail"],
        )
        d = event.to_dict()
        self.assertEqual(d["unit_name"], "mios-test.service")
        self.assertEqual(d["exit_code"], 2)
        self.assertEqual(len(d["error_logs"]), 2)

        restored = self_heal.FailureEvent.from_dict(d)
        self.assertEqual(restored.unit_name, event.unit_name)
        self.assertEqual(restored.error_logs, event.error_logs)

    def test_circuit_breaker_rate_limiting_and_quarantine(self):
        unit = "mios-failing.service"
        now = 1000.0

        # Attempts 1, 2 should be allowed
        self.assertTrue(self.breaker.can_attempt(unit, now=now))
        self.breaker.record_attempt(unit, success=False, now=now)

        self.assertTrue(self.breaker.can_attempt(unit, now=now + 10))
        self.breaker.record_attempt(unit, success=False, now=now + 10)

        # Attempt 3 allowed, but recording 3rd failure trips breaker
        self.assertTrue(self.breaker.can_attempt(unit, now=now + 20))
        tripped = not self.breaker.record_attempt(unit, success=False, now=now + 20)
        self.assertTrue(tripped)

        # Subsequent check must show quarantined
        self.assertFalse(self.breaker.can_attempt(unit, now=now + 30))
        self.assertTrue(self.breaker.is_quarantined(unit, now=now + 30))

        # Reset should unquarantine
        self.breaker.reset(unit)
        self.assertTrue(self.breaker.can_attempt(unit, now=now + 40))
        self.assertFalse(self.breaker.is_quarantined(unit, now=now + 40))

    def test_immutability_protection_usr_forbidden(self):
        # Law 1 (USR-OVER-ETC): /usr is strictly immutable
        self.assertFalse(self.enforcer.is_path_safe("/usr/bin/mios-llm"))
        self.assertFalse(self.enforcer.is_path_safe("/usr/share/mios/profile.toml"))
        self.assertFalse(self.enforcer.is_path_safe("usr/lib/systemd/system/foo.service"))

        # Overrides in /etc and runtime state in /var are allowed
        self.assertTrue(self.enforcer.is_path_safe("/etc/mios/profile.toml"))
        self.assertTrue(self.enforcer.is_path_safe("/etc/systemd/system/foo.service"))
        self.assertTrue(self.enforcer.is_path_safe("/var/lib/mios/state.json"))
        self.assertTrue(self.enforcer.is_path_safe("/tmp/scratch.txt"))

        with self.assertRaises(self_heal.PathViolationError):
            self.enforcer.assert_path_safe("/usr/libexec/mios/daemon")

    def test_safe_config_patch_and_backup(self):
        test_file = os.path.join(self.temp_dir, "etc", "test_config.toml")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("port = 8080\n")

        # Patch file
        self.editor.patch_file(test_file, "port = 9090\n", create_backup=True)

        with open(test_file, "r", encoding="utf-8") as f:
            new_content = f.read()
        self.assertEqual(new_content, "port = 9090\n")

        # Verify backup was created
        backups = [f for f in os.listdir(os.path.dirname(test_file)) if "test_config.toml.bak" in f]
        self.assertGreaterEqual(len(backups), 1)

    def test_diagnose_missing_var_directory(self):
        event = self_heal.FailureEvent(
            unit_name="mios-pgvector.service",
            exit_code=1,
            error_logs=[
                "FATAL: data directory does not exist: /var/lib/mios/pgvector/data",
                "Process terminated with exit status 1",
            ],
        )
        diagnosis = self.healer.diagnose_failure(event)
        self.assertEqual(diagnosis["failure_type"], "MISSING_VAR_DIRECTORY")
        self.assertEqual(diagnosis["recommended_action"], "create_var_dir")
        self.assertIn("/var/lib/mios/pgvector/data", diagnosis["target_files"])

    def test_diagnose_config_syntax_error(self):
        event = self_heal.FailureEvent(
            unit_name="mios-gateway.service",
            exit_code=1,
            error_logs=[
                "Failed to parse /etc/mios/gateway.toml: syntax error on line 12",
                "Exiting on initialization error",
            ],
        )
        diagnosis = self.healer.diagnose_failure(event)
        self.assertEqual(diagnosis["failure_type"], "CONFIG_SYNTAX_ERROR")
        self.assertEqual(diagnosis["recommended_action"], "patch_config")
        self.assertIn("/etc/mios/gateway.toml", diagnosis["target_files"])

    def test_diagnose_port_conflict(self):
        event = self_heal.FailureEvent(
            unit_name="mios-hermes.service",
            exit_code=1,
            error_logs=[
                "Error: Address already in use (:8642)",
                "Failed to bind socket",
            ],
        )
        diagnosis = self.healer.diagnose_failure(event)
        self.assertEqual(diagnosis["failure_type"], "PORT_CONFLICT")
        self.assertEqual(diagnosis["recommended_action"], "restart_with_backoff")

    def test_diagnose_and_reject_usr_tampering(self):
        event = self_heal.FailureEvent(
            unit_name="mios-rogue.service",
            exit_code=1,
            error_logs=[
                "Attempted write to /usr/bin/custom_binary: Read-only file system",
                "Failed to update binary",
            ],
        )
        diagnosis = self.healer.diagnose_failure(event)
        self.assertEqual(diagnosis["failure_type"], "IMMUTABLE_PATH_TARGET")
        self.assertEqual(diagnosis["recommended_action"], "quarantine")

    def test_full_remediation_cycle_and_rca_logging(self):
        target_dir = os.path.join(self.temp_dir, "var", "lib", "mios", "test_store")
        fake_unit = "mios-test-store.service"

        event = self_heal.FailureEvent(
            unit_name=fake_unit,
            exit_code=1,
            error_logs=[f"No such file or directory: {target_dir}"],
        )

        diagnosis = self.healer.diagnose_failure(event)
        res = self.healer.apply_remediation(diagnosis)

        self.assertTrue(res["success"])
        self.assertTrue(os.path.exists(target_dir))

        # Verify RCA log was written
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 1)
        last_rca = json.loads(lines[-1])
        self.assertEqual(last_rca["unit_name"], fake_unit)
        self.assertEqual(last_rca["failure_type"], "MISSING_VAR_DIRECTORY")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSelfHealing)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
