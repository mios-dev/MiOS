#!/usr/bin/env python3
# AI-hint: Sibling test for tools/read-ssot-key.py; proves an absent key exits non-zero instead of printing a default.
# AI-related: tools/read-ssot-key.py, automation/98-drift-checks.sh
"""The point of this reader is that it CANNOT supply a value it did not read.

check_repo_partition_label_ssot used to end in `|| echo "MiOS-Repo"`, so when the
SSOT table was renamed away the shell fallback produced the very label the gate
claimed to verify, and the gate passed on exactly the change it existed to catch.
These cases hold the reader to the opposite contract.
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _load():
    spec = importlib.util.spec_from_file_location(
        "read_ssot_key", os.path.join(_HERE, "read-ssot-key.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


class TestReadSsotKey(unittest.TestCase):
    def setUp(self):
        os.environ["MIOS_DRIFT_ROOT"] = _ROOT

    def test_a_present_scalar_is_printed_and_exits_zero(self):
        self.assertEqual(0, MOD.main(["field.repo_partition.label"]))

    def test_an_absent_key_exits_non_zero(self):
        """The whole contract: no value read, no value printed."""
        self.assertNotEqual(0, MOD.main(["cat.no_such_table.label"]))

    def test_an_absent_top_level_table_exits_non_zero(self):
        self.assertNotEqual(0, MOD.main(["mios_absent_table.key"]))

    def test_a_table_is_refused_rather_than_stringified(self):
        """A caller expecting a scalar must not receive a dict's repr."""
        self.assertNotEqual(0, MOD.main(["cat.repo_partition"]))

    def test_no_argument_is_a_usage_error(self):
        self.assertEqual(2, MOD.main([]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
