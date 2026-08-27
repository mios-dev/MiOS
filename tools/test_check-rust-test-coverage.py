#!/usr/bin/env python3
# AI-hint: Unit tests for tools/check-rust-test-coverage.py.
# AI-related: tools/check-rust-test-coverage.py

import os
import unittest
from importlib.machinery import SourceFileLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
mod = SourceFileLoader(
    "check_rust_test_coverage", os.path.join(_HERE, "check-rust-test-coverage.py")).load_module()

class TestCheckRustTestCoverage(unittest.TestCase):
    def test_import_and_main_callable(self):
        self.assertTrue(hasattr(mod, "main"))
        self.assertTrue(callable(mod.main))

if __name__ == "__main__":
    unittest.main()
