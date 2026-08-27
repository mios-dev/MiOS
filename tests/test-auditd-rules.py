#!/usr/bin/env python3
# AI-hint: Unit and integration tests for Auditd rule generation, syntax validation, and event parsing.
# AI-related: usr/libexec/mios/sec/auditd_rules.py, usr/share/doc/mios/manual/sec.md
"""Unit and integration test suite for AuditdRulesManager and CLI."""

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
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "auditd_rules.py")

spec = importlib.util.spec_from_file_location("auditd_rules", _TARGET_PATH)
if spec and spec.loader:
    auditd_rules = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = auditd_rules
    spec.loader.exec_module(auditd_rules)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestAuditdRules(unittest.TestCase):
    """Test suite for Auditd rule rendering, syntax validation, deployment, and event logs."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-auditd-")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_rules_default_watches(self):
        manager = auditd_rules.AuditdRulesManager(mock=True)
        rules = manager.generate_rules()
        self.assertIn("-D", rules)
        self.assertIn("-b 8192", rules)
        self.assertTrue(any("-w /etc/mios/ -p wa -k mios_config_change" in r for r in rules))
        self.assertTrue(any("-w /usr/share/mios/ -p wa -k mios_config_change" in r for r in rules))

    def test_validate_rules_syntax_valid(self):
        manager = auditd_rules.AuditdRulesManager(mock=True)
        valid_rules = [
            "# Comment",
            "-D",
            "-b 8192",
            "-w /etc/mios/ -p wa -k mios_config_change",
            "-w /usr/share/mios/ -p rwx -k mios_audit",
        ]
        valid, errors = manager.validate_rules_syntax(valid_rules)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_rules_syntax_invalid_flags(self):
        manager = auditd_rules.AuditdRulesManager(mock=True)
        invalid_rules = [
            "-w relative/path -p wa -k test",  # Non-absolute path
            "-w /etc/mios/ -p invalid_perms -k test",  # Invalid permissions
            "-z unknown_flag",  # Unrecognized flag
        ]
        valid, errors = manager.validate_rules_syntax(invalid_rules)
        self.assertFalse(valid)
        self.assertGreaterEqual(len(errors), 3)

    def test_deploy_rules_file_mock(self):
        manager = auditd_rules.AuditdRulesManager(mock=True)
        rules = manager.generate_rules()
        dest_file = os.path.join(self.temp_dir.name, "90-mios-config.rules")
        deployed = manager.deploy_rules_file(rules, destination=dest_file)
        self.assertTrue(deployed)
        self.assertTrue(os.path.exists(dest_file))

    def test_parse_audit_events_matching_key(self):
        manager = auditd_rules.AuditdRulesManager(mock=True)
        sample_log = (
            'type=SYSCALL msg=audit(1724670000.123:456): arch=c000003e syscall=2 success=yes '
            'exe="/usr/bin/touch" key="mios_config_change" comm="touch"\n'
            'type=PATH msg=audit(1724670000.123:456): item=0 name="/etc/mios/profile.toml" '
            'key="mios_config_change"\n'
            'type=SYSCALL msg=audit(1724670005.123:457): arch=c000003e syscall=2 success=yes '
            'exe="/usr/bin/ls" key="other_key" comm="ls"\n'
        )
        events = manager.parse_audit_events(sample_log, key_tag="mios_config_change")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["key"], "mios_config_change")
        self.assertEqual(events[0]["exe"], "/usr/bin/touch")

    def test_cli_execution_generate_and_validate(self):
        test_args = [
            "auditd_rules.py",
            "--validate",
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = auditd_rules.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_deploy(self):
        dest_file = os.path.join(self.temp_dir.name, "audit_test.rules")
        test_args = [
            "auditd_rules.py",
            "--deploy",
            "--rule-file", dest_file,
            "--mock",
            "--json",
        ]
        with patch.object(sys, "argv", test_args):
            exit_code = auditd_rules.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuditdRules)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
